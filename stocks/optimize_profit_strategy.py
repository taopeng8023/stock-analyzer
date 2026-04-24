#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盈利策略优化器 - 多参数组合测试
系统化寻找能够盈利的策略参数

测试维度：
1. 跌幅阈值：8% / 10% / 12%
2. RSI买入阈值：35 / 40 / 45 / 50
3. RSI卖出阈值：65 / 70 / 75
4. 止盈止损：10%止盈/5%回撤 / 15%止盈/8%回撤
5. 持仓天数：10 / 15 / 20

目标：找到胜率>55%，期望收益>1%的参数组合
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import warnings
from pathlib import Path
import time
from typing import Dict, Optional, List
import statistics

warnings.filterwarnings('ignore')

CACHE_DIR = Path(__file__).parent / 'data_tushare'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'
RESULTS_DIR.mkdir(exist_ok=True)


def load_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'fields' in data and 'items' in data:
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        else:
            return None
        
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except:
        return None


def calc_ma(data, period):
    return data['close'].rolling(window=period).mean()

def calc_rsi(data, period=14):
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_kdj(data, n=9):
    lowv = data['low'].rolling(n).min()
    highv = data['high'].rolling(n).max()
    rsv = (data['close'] - lowv) / (highv - lowv) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def backtest_strategy(data: pd.DataFrame, params: Dict) -> Optional[Dict]:
    """单只股票回测"""
    if len(data) < 100:
        return None
    
    # 计算指标
    ma20 = calc_ma(data, 20)
    rsi = calc_rsi(data)
    k, d, j = calc_kdj(data)
    
    # 计算跌幅
    drop_from_ma = (data['close'] - ma20) / ma20
    
    # 参数
    drop_pct = params['drop_pct']
    rsi_buy = params['rsi_buy']
    rsi_sell = params['rsi_sell']
    kdj_sell = params['kdj_sell']
    profit_pct = params['profit_pct']
    trail_pct = params['trail_pct']
    stop_loss = params['stop_loss']
    max_hold = params['max_hold_days']
    
    # 状态
    position = 0
    cost_price = 0
    highest = 0
    buy_idx = 0
    trades = []
    capital = 100000
    
    for i in range(25, len(data)):
        close = float(data['close'].iloc[i])
        
        # 持仓状态
        if position > 0:
            highest = max(highest, close)
            hold_days = i - buy_idx
            
            # 止损
            loss = (close - cost_price) / cost_price
            if loss <= -stop_loss:
                profit_pct_real = loss
                trades.append({
                    'type': 'sell',
                    'profit_pct': profit_pct_real,
                    'reason': 'stop_loss',
                    'hold_days': hold_days
                })
                position = 0
                continue
            
            # 盈利后移动止盈
            if loss >= profit_pct:
                drawdown = (highest - close) / highest
                if drawdown >= trail_pct:
                    trades.append({
                        'type': 'sell',
                        'profit_pct': loss,
                        'reason': 'trailing_stop',
                        'hold_days': hold_days
                    })
                    position = 0
                    continue
            
            # RSI超卖
            rsi_val = rsi.iloc[i]
            if rsi_val > rsi_sell:
                trades.append({
                    'type': 'sell',
                    'profit_pct': loss,
                    'reason': 'rsi_sell',
                    'hold_days': hold_days
                })
                position = 0
                continue
            
            # KDJ超卖
            j_val = j.iloc[i]
            if j_val > kdj_sell:
                trades.append({
                    'type': 'sell',
                    'profit_pct': loss,
                    'reason': 'kdj_sell',
                    'hold_days': hold_days
                })
                position = 0
                continue
            
            # 最大持仓
            if hold_days >= max_hold:
                trades.append({
                    'type': 'sell',
                    'profit_pct': loss,
                    'reason': 'max_hold',
                    'hold_days': hold_days
                })
                position = 0
                continue
        
        # 买入信号
        if position == 0:
            drop = drop_from_ma.iloc[i]
            rsi_val = rsi.iloc[i]
            
            # 三条件同时满足
            if drop <= -drop_pct and rsi_val < rsi_buy and close < ma20.iloc[i]:
                trades.append({
                    'type': 'buy',
                    'price': close,
                    'drop_pct': drop,
                    'rsi': rsi_val,
                    'idx': i
                })
                position = 1
                cost_price = close * 1.001
                highest = cost_price
                buy_idx = i
    
    # 强制平仓
    if position > 0 and trades:
        last_close = float(data['close'].iloc[-1])
        loss = (last_close - cost_price) / cost_price
        trades.append({
            'type': 'sell',
            'profit_pct': loss,
            'reason': 'force_close',
            'hold_days': len(data) - 1 - buy_idx
        })
    
    # 统计
    sell_trades = [t for t in trades if t['type'] == 'sell']
    if not sell_trades:
        return None
    
    win_trades = [t for t in sell_trades if t['profit_pct'] > 0]
    loss_trades = [t for t in sell_trades if t['profit_pct'] <= 0]
    
    win_rate = len(win_trades) / len(sell_trades) if sell_trades else 0
    avg_win = statistics.mean([t['profit_pct'] for t in win_trades]) if win_trades else 0
    avg_loss = statistics.mean([t['profit_pct'] for t in loss_trades]) if loss_trades else 0
    
    expected = win_rate * avg_win + (1 - win_rate) * avg_loss
    
    return {
        'trades': len(sell_trades),
        'win_rate': win_rate,
        'avg_win_pct': avg_win,
        'avg_loss_pct': avg_loss,
        'expected_return': expected,
        'win_count': len(win_trades),
        'loss_count': len(loss_trades)
    }


def generate_param_combinations() -> List[Dict]:
    """生成参数组合"""
    params_list = []
    
    # 跌幅阈值
    drop_pcts = [0.08, 0.10, 0.12]
    
    # RSI买入阈值
    rsi_buys = [35, 40, 45, 50]
    
    # RSI卖出阈值
    rsi_sells = [65, 70, 75]
    
    # KDJ卖出阈值
    kdj_sells = [80, 85, 90]
    
    # 止盈止损组合
    profit_trail_pairs = [
        (0.10, 0.05),   # 10%止盈/5%回撤
        (0.15, 0.08),   # 15%止盈/8%回撤
        (0.08, 0.04),   # 8%止盈/4%回撤（更保守）
    ]
    
    # 止损
    stop_losses = [0.10, 0.12, 0.15]
    
    # 最大持仓天数
    max_holds = [10, 15, 20]
    
    for drop in drop_pcts:
        for rsi_buy in rsi_buys:
            for rsi_sell in rsi_sells:
                for kdj_sell in kdj_sells:
                    for profit, trail in profit_trail_pairs:
                        for stop in stop_losses:
                            for max_hold in max_holds:
                                params_list.append({
                                    'drop_pct': drop,
                                    'rsi_buy': rsi_buy,
                                    'rsi_sell': rsi_sell,
                                    'kdj_sell': kdj_sell,
                                    'profit_pct': profit,
                                    'trail_pct': trail,
                                    'stop_loss': stop,
                                    'max_hold_days': max_hold
                                })
    
    return params_list


def full_market_optimize():
    """全市场参数优化"""
    print('='*80)
    print('盈利策略优化器 - 多参数组合测试')
    print('='*80)
    
    stock_files = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    print(f'\n📊 股票数量：{len(stock_files)} 只')
    
    param_combinations = generate_param_combinations()
    print(f'📊 参数组合：{len(param_combinations)} 种')
    print('\n开始测试...\n')
    
    start_time = time.time()
    all_results = []
    
    # 遍历所有参数组合
    for p_idx, params in enumerate(param_combinations):
        param_name = f"跌>{int(params['drop_pct']*100)}% + RSI<{params['rsi_buy']} | 止盈{int(params['profit_pct']*100)}%/回撤{int(params['trail_pct']*100)}%"
        
        stock_results = []
        
        for symbol in stock_files[:500]:  # 先测试500只股票
            try:
                data = load_stock_data(symbol)
                if data is None:
                    continue
                
                result = backtest_strategy(data, params)
                if result and result['trades'] > 0:
                    stock_results.append(result)
            except:
                pass
        
        if stock_results:
            avg_win_rate = statistics.mean([r['win_rate'] for r in stock_results])
            avg_expected = statistics.mean([r['expected_return'] for r in stock_results])
            avg_win_pct = statistics.mean([r['avg_win_pct'] for r in stock_results])
            avg_loss_pct = statistics.mean([r['avg_loss_pct'] for r in stock_results])
            total_trades = sum([r['trades'] for r in stock_results])
            valid_stocks = len(stock_results)
            
            # 只记录有交易机会的组合
            if total_trades >= 10:  # 至少10次交易
                all_results.append({
                    'param_idx': p_idx,
                    'params': params,
                    'param_name': param_name,
                    'valid_stocks': valid_stocks,
                    'total_trades': total_trades,
                    'avg_win_rate': avg_win_rate,
                    'avg_expected': avg_expected,
                    'avg_win_pct': avg_win_pct,
                    'avg_loss_pct': avg_loss_pct,
                    'score': avg_win_rate * 0.4 + avg_expected * 100 * 0.6  # 综合评分
                })
        
        # 进度显示
        if (p_idx + 1) % 50 == 0:
            elapsed = time.time() - start_time
            print(f"⏳ {p_idx+1}/{len(param_combinations)} ({(p_idx+1)/len(param_combinations)*100:.1f}%) | 有效组合:{len(all_results)} | 耗时:{elapsed:.0f}秒")
    
    elapsed = time.time() - start_time
    
    # 排序
    all_results.sort(key=lambda x: -x['score'])
    
    # 输出
    print("\n" + "="*80)
    print("🏆 Top 20 最佳参数组合")
    print("="*80)
    
    print("\n| 排名 | 参数组合 | 覆盖股票 | 总交易 | 胜率 | 期望收益 | 盈利时赚 | 亏损时亏 | 综合评分 |")
    print("|------|----------|---------|--------|------|---------|---------|---------|---------|")
    
    for i, r in enumerate(all_results[:20], 1):
        print(f"| {i:2d} | {r['param_name'][:35]} | {r['valid_stocks']:4d} | {r['total_trades']:4d} | "
              f"{r['avg_win_rate']*100:4.1f}% | {r['avg_expected']*100:+5.2f}% | {r['avg_win_pct']*100:+5.2f}% | "
              f"{r['avg_loss_pct']*100:+5.2f}% | {r['score']:+6.3f} |")
    
    # 筛选盈利组合
    profit_combos = [r for r in all_results if r['avg_expected'] > 0.005 and r['avg_win_rate'] > 0.50]
    
    print("\n" + "="*80)
    print(f"✅ 盈利组合数量：{len(profit_combos)} / {len(all_results)}")
    print("="*80)
    
    if profit_combos:
        print("\n| 排名 | 参数组合 | 覆盖股票 | 总交易 | 胜率 | 期望收益 | 盈利时赚 | 亏损时亏 |")
        print("|------|----------|---------|--------|------|---------|---------|---------|")
        
        for i, r in enumerate(profit_combos[:15], 1):
            print(f"| {i:2d} | {r['param_name'][:35]} | {r['valid_stocks']:4d} | {r['total_trades']:4d} | "
                  f"{r['avg_win_rate']*100:4.1f}% | {r['avg_expected']*100:+5.2f}% | {r['avg_win_pct']*100:+5.2f}% | "
                  f"{r['avg_loss_pct']*100:+5.2f}% |")
    
    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    results_df = pd.DataFrame([{
        'param_name': r['param_name'],
        'valid_stocks': r['valid_stocks'],
        'total_trades': r['total_trades'],
        'win_rate': r['avg_win_rate'],
        'expected_return': r['avg_expected'],
        'avg_win_pct': r['avg_win_pct'],
        'avg_loss_pct': r['avg_loss_pct'],
        'score': r['score'],
        **r['params']
    } for r in all_results])
    
    results_df.to_csv(RESULTS_DIR / f'profit_optimizer_{timestamp}.csv', 
                      index=False, encoding='utf-8-sig')
    
    # 保存最佳参数
    if all_results:
        best = all_results[0]
        best_params = {
            'params': best['params'],
            'summary': {
                'valid_stocks': best['valid_stocks'],
                'total_trades': best['total_trades'],
                'win_rate': best['avg_win_rate'],
                'expected_return': best['avg_expected'],
                'avg_win_pct': best['avg_win_pct'],
                'avg_loss_pct': best['avg_loss_pct']
            }
        }
        
        with open(RESULTS_DIR / f'best_profit_params_{timestamp}.json', 'w') as f:
            json.dump(best_params, f, indent=2)
        
        print(f"\n💾 结果已保存：")
        print(f"  - profit_optimizer_{timestamp}.csv")
        print(f"  - best_profit_params_{timestamp}.json")
        
        print("\n" + "="*80)
        print("🎯 最佳策略参数")
        print("="*80)
        
        print(f"""
参数详情：
  跌幅阈值：{int(best['params']['drop_pct']*100)}%
  RSI买入：< {best['params']['rsi_buy']}
  RSI卖出：> {best['params']['rsi_sell']}
  KDJ卖出：> {best['params']['kdj_sell']}
  止盈：{int(best['params']['profit_pct']*100)}%
  回撤止盈：{int(best['params']['trail_pct']*100)}%
  止损：{int(best['params']['stop_loss']*100)}%
  最大持仓：{best['params']['max_hold_days']}天

效果：
  覆盖股票：{best['valid_stocks']} 只
  总交易数：{best['total_trades']} 次
  胜率：{best['avg_win_rate']*100:.1f}%
  期望收益：{best['avg_expected']*100:+.2f}%
  盈利时赚：{best['avg_win_pct']*100:+.2f}%
  亏损时亏：{best['avg_loss_pct']*100:+.2f}%

⏱️ 总耗时：{elapsed:.0f}秒 ({elapsed/60:.1f}分钟)
""")
        
        # 判断是否达标
        if best['avg_expected'] > 0.01 and best['avg_win_rate'] > 0.55:
            print("✅ 策略达标！胜率>55%，期望收益>1%")
        elif best['avg_expected'] > 0.005:
            print("🟡 策略接近达标，可进一步优化")
        else:
            print("❌ 策略未达标，需要继续寻找")
    
    return all_results


if __name__ == '__main__':
    full_market_optimize()