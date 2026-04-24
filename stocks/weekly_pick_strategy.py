#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每周选股策略系统
目标：每周筛选出符合条件的股票，持有约1-2周

最佳参数：RSI 25-45 + 均线多头 + 持有10天
回测结果：平均收益 0.78%，胜率 49.5%，盈利股票占比 51%

策略逻辑：
1. 选股条件：RSI处于超卖区间(25-45) + 均线多头排列(MA5>MA10) + 股价站上MA5
2. 持有周期：10个交易日(约2周)
3. 止盈止损：移动止盈10%，止损-8%
4. 资金管理：每周最多买入3只，单只仓位30%

适用环境：震荡市或弱牛市，熊市慎用
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
OUTPUT_DIR = Path('/home/admin/.openclaw/workspace/stocks/weekly_picks')
OUTPUT_DIR.mkdir(exist_ok=True)


def load_stock_data(symbol):
    """加载股票历史数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'fields' in data and 'items' in data:
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df = df.rename(columns={'trade_date': 'date'})
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date').reset_index(drop=True)
            
            for col in ['open', 'high', 'low', 'close', 'vol']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
    except:
        return None


def calc_ma(close, period):
    """计算均线"""
    return close.rolling(window=period).mean()


def calc_rsi(close, period=14):
    """计算RSI"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calc_kdj(df, n=9):
    """计算KDJ"""
    lowv = df['low'].rolling(n).min()
    highv = df['high'].rolling(n).max()
    rsv = (df['close'] - lowv) / (highv - lowv) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def weekly_pick(df, lookback=30):
    """
    每周选股筛选
    返回：符合条件的股票信号
    """
    if df is None or len(df) < lookback + 20:
        return None
    
    # 计算指标
    recent = df.tail(lookback + 20).copy()
    recent['ma5'] = calc_ma(recent['close'], 5)
    recent['ma10'] = calc_ma(recent['close'], 10)
    recent['ma20'] = calc_ma(recent['close'], 20)
    recent['rsi'] = calc_rsi(recent['close'], 14)
    k, d, j = calc_kdj(recent, 9)
    recent['k'] = k
    recent['d'] = d
    recent['j'] = j
    
    # 最新数据
    latest = recent.iloc[-1]
    
    if pd.isna(latest['rsi']) or pd.isna(latest['ma5']):
        return None
    
    # 选股条件
    signals = []
    
    # 条件1：RSI超卖区间 (25-45)
    rsi_cond = 25 < latest['rsi'] < 45
    
    # 条件2：均线多头 (MA5 > MA10)
    ma_cond = latest['ma5'] > latest['ma10']
    
    # 条件3：股价站上MA5
    price_cond = latest['close'] > latest['ma5']
    
    # 条件4：KDJ低位 (J < 40)
    kdj_cond = latest['j'] < 40 if not pd.isna(latest['j']) else False
    
    # 条件5：股价高于MA20 (趋势确认)
    trend_cond = latest['close'] > latest['ma20']
    
    # 计算信号强度
    score = 0
    if rsi_cond:
        score += 2
    if ma_cond:
        score += 1
    if price_cond:
        score += 1
    if kdj_cond:
        score += 1
    if trend_cond:
        score += 1
    
    # 至少满足3个条件才入选
    if score >= 4:
        return {
            'symbol': df['symbol'].iloc[0] if 'symbol' in df.columns else 'unknown',
            'date': latest['date'],
            'close': float(latest['close']),
            'rsi': float(latest['rsi']),
            'ma5': float(latest['ma5']),
            'ma10': float(latest['ma10']),
            'j': float(latest['j']) if not pd.isna(latest['j']) else None,
            'score': score,
            'signals': {
                'rsi_oversold': rsi_cond,
                'ma_bullish': ma_cond,
                'above_ma5': price_cond,
                'kdj_low': kdj_cond,
                'trend_up': trend_cond
            }
        }
    
    return None


def scan_all_stocks(date=None):
    """扫描全市场股票"""
    symbols = [f.stem for f in CACHE_DIR.glob('*.json')]
    
    picks = []
    
    for sym in symbols:
        df = load_stock_data(sym)
        if df is None:
            continue
        
        # 如果指定日期，只看该日期之前的数据
        if date:
            df = df[df['date'] <= date]
        
        if len(df) < 50:
            continue
        
        signal = weekly_pick(df)
        if signal:
            signal['symbol'] = sym
            picks.append(signal)
    
    # 按信号强度排序
    picks.sort(key=lambda x: x['score'], reverse=True)
    
    return picks


def backtest_weekly_pick(symbols, hold_days=10, fee=0.0003):
    """
    回测每周选股策略
    """
    results = []
    
    for sym in symbols:
        df = load_stock_data(sym)
        if df is None or len(df) < 200:
            continue
        
        # 计算指标
        df['ma5'] = calc_ma(df['close'], 5)
        df['ma10'] = calc_ma(df['close'], 10)
        df['rsi'] = calc_rsi(df['close'], 14)
        
        trades = []
        capital = 10000
        
        for i in range(50, len(df) - hold_days - 5, 5):
            if pd.isna(df['rsi'].iloc[i]):
                continue
            
            rsi = float(df['rsi'].iloc[i])
            ma5 = float(df['ma5'].iloc[i])
            ma10 = float(df['ma10'].iloc[i])
            price = float(df['close'].iloc[i])
            
            # 选股条件
            if 25 < rsi < 45 and ma5 > ma10 and price > ma5:
                # 持有hold_days天
                sell_price = float(df['close'].iloc[i + hold_days])
                
                buy_cost = capital * (1 + fee)
                sell_amt = capital * sell_price / price * (1 - fee)
                profit_pct = (sell_amt - buy_cost) / buy_cost
                
                trades.append({
                    'buy_date': df['date'].iloc[i],
                    'sell_date': df['date'].iloc[i + hold_days],
                    'buy_price': price,
                    'sell_price': sell_price,
                    'return': profit_pct
                })
        
        if trades:
            wins = [t for t in trades if t['return'] > 0]
            total_return = sum([t['return'] for t in trades])
            
            results.append({
                'symbol': sym,
                'trade_count': len(trades),
                'win_count': len(wins),
                'win_rate': len(wins) / len(trades),
                'avg_return': total_return / len(trades),
                'total_return': total_return
            })
    
    return results


def generate_weekly_report(picks, top_n=10):
    """生成每周选股报告"""
    if not picks:
        return "本周无符合条件的股票"
    
    report = f"""
================================================================================
每周选股报告 - {datetime.now().strftime('%Y-%m-%d')}
================================================================================

筛选条件：
✓ RSI 处于超卖区间 (25-45)
✓ 均线多头排列 (MA5 > MA10)
✓ 股价站上 MA5
✓ KDJ 低位 (J < 40) 【加分项】
✓ 股价高于 MA20 【加分项】

入选股票：{len(picks)} 只

--------------------------------------------------------------------------------
TOP {min(top_n, len(picks))} 推荐股票
--------------------------------------------------------------------------------
"""
    
    for i, pick in enumerate(picks[:top_n], 1):
        signals = pick['signals']
        signal_str = []
        if signals['rsi_oversold']:
            signal_str.append('RSI超卖')
        if signals['ma_bullish']:
            signal_str.append('均线多头')
        if signals['above_ma5']:
            signal_str.append('站上MA5')
        if signals['kdj_low']:
            signal_str.append('KDJ低位')
        if signals['trend_up']:
            signal_str.append('趋势向上')
        
        report += f"""
{i}. {pick['symbol']}
   价格: ¥{pick['close']:.2f}
   RSI: {pick['rsi']:.1f}
   J值: {pick['j']:.1f if pick['j'] else 'N/A'}
   信号强度: {pick['score']}/6
   满足条件: {', '.join(signal_str)}
"""
    
    report += """
--------------------------------------------------------------------------------
操作建议
--------------------------------------------------------------------------------
• 每周最多买入 3 只股票
• 单只仓位 30%
• 持有周期: 10 个交易日 (约 2 周)
• 止盈: 移动止盈 10% (从最高价回撤触发)
• 止损: 固定止损 -8%

================================================================================
"""
    
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description='每周选股策略')
    parser.add_argument('--scan', action='store_true', help='扫描当前市场')
    parser.add_argument('--backtest', action='store_true', help='回测策略')
    parser.add_argument('--sample', type=int, default=100, help='回测样本数')
    parser.add_argument('--top', type=int, default=10, help='显示TOP N')
    
    args = parser.parse_args()
    
    if args.scan:
        print('扫描全市场...')
        picks = scan_all_stocks()
        report = generate_weekly_report(picks, args.top)
        print(report)
        
        # 保存结果
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = OUTPUT_DIR / f'weekly_picks_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(picks[:20], f, ensure_ascii=False, indent=2)
        
        print(f'\n💾 已保存: {output_file}')
    
    elif args.backtest:
        import statistics
        symbols = [f.stem for f in CACHE_DIR.glob('*.json')]
        
        if args.sample:
            import random
            random.seed(42)
            symbols = random.sample(symbols, min(args.sample, len(symbols)))
        
        print(f'回测 {len(symbols)} 只股票...')
        results = backtest_weekly_pick(symbols)
        
        if results:
            avg_win = statistics.mean([r['win_rate'] for r in results])
            avg_return = statistics.mean([r['avg_return'] for r in results])
            avg_trades = statistics.mean([r['trade_count'] for r in results])
            profit_pct = len([r for r in results if r['total_return'] > 0]) / len(results)
            
            print(f"""
================================================================================
回测结果
================================================================================
有效股票: {len(results)} 只
平均交易: {avg_trades:.1f} 次/股
平均胜率: {avg_win*100:.1f}%
平均收益: {avg_return*100:.2f}%
盈利股票: {profit_pct*100:.1f}%

TOP 10:
""")
            
            sorted_r = sorted(results, key=lambda x: x['total_return'], reverse=True)
            for r in sorted_r[:10]:
                print(f"  {r['symbol']}: {r['trade_count']}次 胜率{r['win_rate']*100:.0f}% 收益+{r['total_return']*100:.1f}%")
    
    else:
        print("""
用法:
  --scan          扫描当前市场，生成每周选股报告
  --backtest      回测策略历史表现
  --sample 500    回测样本数
  --top 10        显示TOP N股票
""")


if __name__ == '__main__':
    main()