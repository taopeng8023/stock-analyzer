#!/usr/bin/env python3
"""
ML模型全量回测 - 使用2022-2026完整数据
评估模型实际交易效果
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import pickle
import xgboost as xgb
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')

FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'p_ma60',
    'ma5_slope', 'ma10_slope', 'ma20_slope',
    'ret1', 'ret5', 'ret10', 'ret20',
    'vol5', 'vol10', 'vol20',
    'rsi',
    'macd_dif', 'macd_dea', 'macd_hist',
    'kdj_k', 'kdj_d', 'kdj_j',
    'vol_ratio', 'vol_ratio20',
    'hl_pct', 'hc_pct', 'cl_pct',
    'boll_pos'
]

def calc_features(df):
    """计算技术指标"""
    d = df.copy()
    
    for p in [5, 10, 20, 60]:
        d[f'ma{p}'] = d['close'].rolling(p).mean()
        d[f'p_ma{p}'] = (d['close'] - d[f'ma{p}']) / d[f'ma{p}']
    
    d['ma5_slope'] = d['ma5'] / d['ma5'].shift(5) - 1
    d['ma10_slope'] = d['ma10'] / d['ma10'].shift(5) - 1
    d['ma20_slope'] = d['ma20'] / d['ma20'].shift(10) - 1
    
    for days in [1, 5, 10, 20]:
        d[f'ret{days}'] = d['close'].pct_change(days)
    
    for days in [5, 10, 20]:
        d[f'vol{days}'] = d['ret1'].rolling(days).std()
    
    delta = d['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    d['rsi'] = 100 - 100/(1 + gain/loss.replace(0, 0.001))
    
    ema12 = d['close'].ewm(span=12, adjust=False).mean()
    ema26 = d['close'].ewm(span=26, adjust=False).mean()
    d['macd_dif'] = ema12 - ema26
    d['macd_dea'] = d['macd_dif'].ewm(span=9, adjust=False).mean()
    d['macd_hist'] = (d['macd_dif'] - d['macd_dea']) * 2
    
    lowv = d['low'].rolling(9).min()
    highv = d['high'].rolling(9).max()
    rsv = (d['close'] - lowv) / (highv - lowv + 0.001) * 100
    d['kdj_k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
    d['kdj_d'] = d['kdj_k'].ewm(alpha=1/3, adjust=False).mean()
    d['kdj_j'] = 3 * d['kdj_k'] - 2 * d['kdj_d']
    
    d['vol_ma5'] = d['vol'].rolling(5).mean()
    d['vol_ma20'] = d['vol'].rolling(20).mean()
    d['vol_ratio'] = d['vol'] / d['vol_ma5']
    d['vol_ratio20'] = d['vol'] / d['vol_ma20']
    
    d['hl_pct'] = (d['high'] - d['low']) / d['close']
    d['hc_pct'] = (d['high'] - d['close']) / d['close']
    d['cl_pct'] = (d['close'] - d['low']) / d['close']
    
    d['boll_mid'] = d['close'].rolling(20).mean()
    d['boll_std'] = d['close'].rolling(20).std()
    d['boll_upper'] = d['boll_mid'] + 2 * d['boll_std']
    d['boll_lower'] = d['boll_mid'] - 2 * d['boll_std']
    d['boll_pos'] = (d['close'] - d['boll_lower']) / (d['boll_upper'] - d['boll_lower'] + 0.001)
    
    return d

def backtest_stock(symbol, model, scaler, threshold=0.75, fee=0.0006):
    """单只股票回测"""
    filepath = DATA_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data['items'], columns=data['fields'])
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        for c in ['open', 'high', 'low', 'close', 'vol']:
            df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)
        
        df = df.dropna()
        if len(df) < 100:
            return None
        
        feat = calc_features(df)
        
        # 模拟交易
        capital = 100000
        position = 0
        cost_price = 0
        buy_date_idx = 0
        highest_price = 0
        
        trades = []
        
        for i in range(60, len(feat)):
            close = float(feat.iloc[i]['close'])
            
            # 持仓状态检查
            if position > 0:
                highest_price = max(highest_price, close)
                hold_days = i - buy_date_idx
                pnl_pct = (close - cost_price) / cost_price
                
                # 止损12%
                if pnl_pct <= -0.12:
                    sell_price = close * 0.999
                    fee_amt = position * sell_price * fee
                    profit = position * sell_price - fee_amt - position * cost_price
                    trades.append({
                        'buy_date': feat.iloc[buy_date_idx]['trade_date'],
                        'sell_date': feat.iloc[i]['trade_date'],
                        'buy_price': cost_price,
                        'sell_price': sell_price,
                        'profit': profit,
                        'profit_pct': pnl_pct,
                        'hold_days': hold_days,
                        'reason': 'stop_loss'
                    })
                    position = 0
                    continue
                
                # 盈利10%后回撤5%止盈
                if pnl_pct >= 0.10:
                    drawdown = (highest_price - close) / highest_price
                    if drawdown >= 0.05:
                        sell_price = close * 0.999
                        fee_amt = position * sell_price * fee
                        profit = position * sell_price - fee_amt - position * cost_price
                        trades.append({
                            'buy_date': feat.iloc[buy_date_idx]['trade_date'],
                            'sell_date': feat.iloc[i]['trade_date'],
                            'buy_price': cost_price,
                            'sell_price': sell_price,
                            'profit': profit,
                            'profit_pct': pnl_pct,
                            'hold_days': hold_days,
                            'reason': 'trailing_stop'
                        })
                        position = 0
                        continue
                
                # RSI>70卖出
                rsi_val = feat.iloc[i]['rsi']
                if rsi_val > 70:
                    sell_price = close * 0.999
                    fee_amt = position * sell_price * fee
                    profit = position * sell_price - fee_amt - position * cost_price
                    trades.append({
                        'buy_date': feat.iloc[buy_date_idx]['trade_date'],
                        'sell_date': feat.iloc[i]['trade_date'],
                        'buy_price': cost_price,
                        'sell_price': sell_price,
                        'profit': profit,
                        'profit_pct': pnl_pct,
                        'hold_days': hold_days,
                        'reason': 'rsi_overbuy'
                    })
                    position = 0
                    continue
                
                # 最大持仓15天
                if hold_days >= 15:
                    sell_price = close * 0.999
                    fee_amt = position * sell_price * fee
                    profit = position * sell_price - fee_amt - position * cost_price
                    trades.append({
                        'buy_date': feat.iloc[buy_date_idx]['trade_date'],
                        'sell_date': feat.iloc[i]['trade_date'],
                        'buy_price': cost_price,
                        'sell_price': sell_price,
                        'profit': profit,
                        'profit_pct': pnl_pct,
                        'hold_days': hold_days,
                        'reason': 'max_hold'
                    })
                    position = 0
                    continue
            
            # 买入信号
            if position == 0:
                X = feat.iloc[i][FEATURES].values.astype(float).reshape(1, -1)
                if np.isnan(X).sum() > 0:
                    continue
                
                # 使用XGB模型预测
                dmat = xgb.DMatrix(X)
                prob = model.predict(dmat)[0]
                
                if prob > threshold:
                    # 买入
                    buy_price = close * 1.001
                    shares = int(capital * 0.95 / buy_price / 100) * 100
                    
                    if shares >= 100:
                        fee_amt = shares * buy_price * fee
                        capital -= (shares * buy_price + fee_amt)
                        position = shares
                        cost_price = buy_price
                        highest_price = buy_price
                        buy_date_idx = i
        
        # 强制平仓
        if position > 0:
            last_close = float(feat.iloc[-1]['close'])
            pnl_pct = (last_close - cost_price) / cost_price
            sell_price = last_close * 0.999
            fee_amt = position * sell_price * fee
            profit = position * sell_price - fee_amt - position * cost_price
            trades.append({
                'buy_date': feat.iloc[buy_date_idx]['trade_date'],
                'sell_date': feat.iloc[-1]['trade_date'],
                'buy_price': cost_price,
                'sell_price': sell_price,
                'profit': profit,
                'profit_pct': pnl_pct,
                'hold_days': len(feat) - 1 - buy_date_idx,
                'reason': 'force_close'
            })
        
        return trades
    
    except:
        return None

def main():
    print('='*70)
    print('ML模型全量回测 (2022-2026数据)')
    print('='*70)
    
    # 加载全量XGB模型
    import xgboost as xgb
    
    model_file = MODEL_DIR / 'ml_xgb_20260412_235045.json'
    config_file = MODEL_DIR / 'ml_config_20260412_235045.json'
    
    model = xgb.Booster()
    model.load_model(str(model_file))
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    threshold = config.get('threshold', 0.75)
    high_precision = config.get('high_precision', 0.89)
    
    # 加载V2模型的scaler（临时兼容）
    v2_file = MODEL_DIR / 'ml_selector_v2_20260412_190955.pkl'
    with open(v2_file, 'rb') as f:
        v2 = pickle.load(f)
    scaler = v2['scaler']
    
    print(f'模型: {model_file.name}')
    print(f'精确率: {high_precision*100:.1f}%')
    print(f'阈值: {threshold*100:.0f}%')
    
    # 加载股票列表
    symbols = [f.stem for f in DATA_DIR.glob('*.json')]
    print(f'\n股票总数: {len(symbols)}只')
    
    # 回测
    print('\n回测中...')
    all_trades = []
    stock_results = []
    
    for i, s in enumerate(symbols):
        trades = backtest_stock(s, model, scaler, threshold)
        
        if trades:
            all_trades.extend(trades)
            
            wins = [t for t in trades if t['profit_pct'] > 0]
            win_rate = len(wins) / len(trades) if trades else 0
            avg_pnl = np.mean([t['profit_pct'] for t in trades])
            
            stock_results.append({
                'symbol': s,
                'trades': len(trades),
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_profit': sum([t['profit'] for t in trades])
            })
        
        if (i+1) % 500 == 0:
            print(f'  {i+1}/{len(symbols)} | 交易数: {len(all_trades)}')
    
    print(f'\n扫描完成: {len(stock_results)}只股票有交易')
    
    # 汇总分析
    if all_trades:
        wins = [t for t in all_trades if t['profit_pct'] > 0]
        losses = [t for t in all_trades if t['profit_pct'] <= 0]
        
        win_rate = len(wins) / len(all_trades)
        avg_win = np.mean([t['profit_pct'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['profit_pct'] for t in losses]) if losses else 0
        
        expected_return = win_rate * avg_win + (1-win_rate) * avg_loss
        
        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # 最大收益/亏损
        max_win = max([t['profit_pct'] for t in all_trades])
        max_loss = min([t['profit_pct'] for t in all_trades])
        
        # 持仓天数
        avg_hold = np.mean([t['hold_days'] for t in all_trades])
        
        # 卖出原因统计
        sell_reasons = {}
        for t in all_trades:
            reason = t['reason']
            if reason not in sell_reasons:
                sell_reasons[reason] = {'count': 0, 'profit': 0, 'wins': 0}
            sell_reasons[reason]['count'] += 1
            sell_reasons[reason]['profit'] += t['profit_pct']
            if t['profit_pct'] > 0:
                sell_reasons[reason]['wins'] += 1
        
        print(f'\n' + '='*70)
        print('📊 全量回测结果')
        print('='*70)
        
        print(f'''
交易统计:
  总交易数: {len(all_trades)}次
  盈利次数: {len(wins)}次
  亏损次数: {len(losses)}次

核心指标:
  胜率: {win_rate*100:.2f}% ⭐
  期望收益: {expected_return*100:+.2f}% ⭐
  
  盈利时平均赚: +{avg_win*100:.2f}%
  亏损时平均亏: -{abs(avg_loss)*100:.2f}%
  
  盈亏比: {profit_loss_ratio:.2f}
  
  最大单笔收益: +{max_win*100:.1f}%
  最大单笔亏损: -{abs(max_loss)*100:.1f}%
  
  平均持仓: {avg_hold:.1f}天

股票覆盖:
  有交易股票: {len(stock_results)}只
  平均每只交易: {len(all_trades)/len(stock_results):.1f}次
''')
        
        # 卖出原因分析
        print('卖出原因分析:')
        print('| 原因 | 次数 | 盈利次数 | 平均收益 |')
        print('|------|------|---------|---------|')
        for reason, stats in sorted(sell_reasons.items(), key=lambda x: -x[1]['count']):
            avg_ret = stats['profit'] / stats['count'] * 100
            print(f'| {reason} | {stats["count"]} | {stats["wins"]} ({stats["wins"]/stats["count"]*100:.0f}%) | {avg_ret:+.2f}% |')
        
        # Top 20股票
        stock_results.sort(key=lambda x: -x['avg_pnl'])
        
        print(f'\n🏆 Top 20 表现最佳股票:')
        print('| 代码 | 交易 | 胜率 | 平均收益 |')
        print('|------|------|------|---------|')
        for r in stock_results[:20]:
            print(f'| {r["symbol"]} | {r["trades"]} | {r["win_rate"]*100:.0f}% | {r["avg_pnl"]*100:+.2f}% |')
        
        # 保存结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        trades_df = pd.DataFrame(all_trades)
        trades_df.to_csv(RESULTS_DIR / f'ml_backtest_trades_{timestamp}.csv', index=False)
        
        stocks_df = pd.DataFrame(stock_results)
        stocks_df.to_csv(RESULTS_DIR / f'ml_backtest_stocks_{timestamp}.csv', index=False)
        
        # 汇总JSON
        summary = {
            'timestamp': timestamp,
            'total_trades': len(all_trades),
            'win_trades': len(wins),
            'win_rate': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'expected_return': expected_return,
            'profit_loss_ratio': profit_loss_ratio,
            'max_win': max_win,
            'max_loss': max_loss,
            'avg_hold_days': avg_hold,
            'stock_count': len(stock_results),
            'threshold': threshold
        }
        
        with open(RESULTS_DIR / f'ml_backtest_summary_{timestamp}.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f'\n💾 结果已保存:')
        print(f'  ml_backtest_trades_{timestamp}.csv')
        print(f'  ml_backtest_stocks_{timestamp}.csv')
        print(f'  ml_backtest_summary_{timestamp}.json')
        
        # 最终评估
        print(f'\n' + '='*70)
        print('🎯 最终评估')
        print('='*70)
        
        if win_rate >= 0.60 and expected_return >= 0.02:
            print(f'''
✅ 策略优秀！
胜率 {win_rate*100:.1f}% ≥ 60%
期望收益 {expected_return*100:+.1f}% ≥ 2%

模型置信度>{threshold*100:.0f}%时可以放心买入！
''')
        elif win_rate >= 0.55 and expected_return >= 0.01:
            print(f'''
🟡 策略良好
胜率 {win_rate*100:.1f}% ≥ 55%
期望收益 {expected_return*100:+.1f}% ≥ 1%

建议：可适当提高置信度阈值
''')
        else:
            print(f'''
⚠️ 策略表现一般
胜率 {win_rate*100:.1f}%
期望收益 {expected_return*100:+.1f}%

建议：调整参数或提高阈值
''')

if __name__ == '__main__':
    main()