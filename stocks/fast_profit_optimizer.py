#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速盈利策略优化器
精简版本 - 只测试最关键的参数组合

核心测试：
- 跌幅阈值：8% / 10% / 12%
- RSI买入阈值：35 / 40 / 45
- 止盈：10% / 15%
- 止损：10% / 12%

目标：快速找到胜率>55%，收益>1%的参数
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
import sys

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
    
    ma20 = calc_ma(data, 20)
    rsi = calc_rsi(data)
    k, d, j = calc_kdj(data)
    drop_from_ma = (data['close'] - ma20) / ma20
    
    drop_pct = params['drop_pct']
    rsi_buy = params['rsi_buy']
    rsi_sell = 70  # 固定
    kdj_sell = 85  # 固定
    profit_pct = params['profit_pct']
    trail_pct = params['trail_pct']
    stop_loss = params['stop_loss']
    max_hold = 15  # 固定
    
    position = 0
    cost_price = 0
    highest = 0
    buy_idx = 0
    trades = []
    
    for i in range(25, len(data)):
        close = float(data['close'].iloc[i])
        
        if position > 0:
            highest = max(highest, close)
            hold_days = i - buy_idx
            loss = (close - cost_price) / cost_price
            
            # 止损
            if loss <= -stop_loss:
                trades.append({'type': 'sell', 'profit_pct': loss, 'reason': 'stop_loss'})
                position = 0
                continue
            
            # 移动止盈
            if loss >= profit_pct:
                drawdown = (highest - close) / highest
                if drawdown >= trail_pct:
                    trades.append({'type': 'sell', 'profit_pct': loss, 'reason': 'trailing'})
                    position = 0
                    continue
            
            # RSI/KDJ超买卖出
            if rsi.iloc[i] > rsi_sell or j.iloc[i] > kdj_sell:
                trades.append({'type': 'sell', 'profit_pct': loss, 'reason': 'indicator'})
                position = 0
                continue
            
            # 最大持仓
            if hold_days >= max_hold:
                trades.append({'type': 'sell', 'profit_pct': loss, 'reason': 'max_hold'})
                position = 0
                continue
        
        # 买入
        if position == 0:
            drop = drop_from_ma.iloc[i]
            rsi_val = rsi.iloc[i]
            
            if drop <= -drop_pct and rsi_val < rsi_buy and close < ma20.iloc[i]:
                trades.append({'type': 'buy', 'price': close})
                position = 1
                cost_price = close * 1.001
                highest = cost_price
                buy_idx = i
    
    # 强制平仓
    if position > 0:
        last_close = float(data['close'].iloc[-1])
        loss = (last_close - cost_price) / cost_price
        trades.append({'type': 'sell', 'profit_pct': loss, 'reason': 'force'})
    
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
        'expected_return': expected
    }


def fast_optimize():
    """快速优化"""
    print('='*80)
    print('快速盈利策略优化器')
    print('='*80, flush=True)
    
    stock_files = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    
    # 抽样测试（先测试100只）
    import random
    random.seed(42)
    sample_stocks = random.sample(stock_files, min(100, len(stock_files)))
    
    print(f'\n📊 抽样股票：{len(sample_stocks)} 只', flush=True)
    
    # 精简参数组合（只测试最关键的）
    params_list = []
    
    # 跌幅阈值
    for drop in [0.08, 0.10, 0.12]:
        # RSI买入阈值
        for rsi_buy in [35, 40, 45]:
            # 止盈止损组合
            for profit, trail, stop in [
                (0.10, 0.05, 0.10),  # 保守
                (0.10, 0.05, 0.12),  # 标准
                (0.15, 0.08, 0.12),  # 进取
            ]:
                params_list.append({
                    'drop_pct': drop,
                    'rsi_buy': rsi_buy,
                    'profit_pct': profit,
                    'trail_pct': trail,
                    'stop_loss': stop
                })
    
    # 总共 3 × 3 × 3 = 27 种组合
    print(f'📊 参数组合：{len(params_list)} 种', flush=True)
    print('\n开始测试...\n', flush=True)
    
    start_time = time.time()
    all_results = []
    
    for p_idx, params in enumerate(params_list):
        param_name = f"跌>{int(params['drop_pct']*100)}% + RSI<{params['rsi_buy']} | 止盈{int(params['profit_pct']*100)}%/止损{int(params['stop_loss']*100)}%"
        
        stock_results = []
        
        for symbol in sample_stocks:
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
            
            all_results.append({
                'params': params,
                'param_name': param_name,
                'valid_stocks': len(stock_results),
                'total_trades': total_trades,
                'avg_win_rate': avg_win_rate,
                'avg_expected': avg_expected,
                'avg_win_pct': avg_win_pct,
                'avg_loss_pct': avg_loss_pct,
                'score': avg_win_rate * 0.4 + avg_expected * 100 * 0.6
            })
        
        # 实时输出
        elapsed = time.time() - start_time
        valid = len([r for r in all_results if r['total_trades'] > 0])
        print(f"[{p_idx+1}/{len(params_list)}] {param_name[:40]} | "
              f"有效:{valid} | 耗时:{elapsed:.0f}秒", flush=True)
    
    elapsed = time.time() - start_time
    
    # 排序
    all_results.sort(key=lambda x: -x['score'])
    
    # 输出
    print("\n" + "="*80)
    print("🏆 参数组合排名")
    print("="*80, flush=True)
    
    print("\n| 排名 | 参数组合 | 覆盖股票 | 总交易 | 胜率 | 期望收益 | 盈利时赚 | 亏损时亏 |")
    print("|------|----------|---------|--------|------|---------|---------|---------|", flush=True)
    
    for i, r in enumerate(all_results, 1):
        status = "✅" if r['avg_expected'] > 0.005 and r['avg_win_rate'] > 0.55 else ""
        print(f"| {i:2d} | {r['param_name'][:38]} | {r['valid_stocks']:4d} | {r['total_trades']:4d} | "
              f"{r['avg_win_rate']*100:4.1f}% | {r['avg_expected']*100:+5.2f}% | {r['avg_win_pct']*100:+5.2f}% | "
              f"{r['avg_loss_pct']*100:+5.2f}% | {status}", flush=True)
    
    # 筛选盈利组合
    profit_combos = [r for r in all_results if r['avg_expected'] > 0.005 and r['avg_win_rate'] > 0.50]
    
    print("\n" + "="*80)
    print(f"✅ 盈利组合：{len(profit_combos)} / {len(all_results)}")
    print("="*80, flush=True)
    
    if profit_combos:
        print("\n🏆 最佳盈利策略：", flush=True)
        best = profit_combos[0]
        print(f"""
参数：
  跌幅阈值：{int(best['params']['drop_pct']*100)}%
  RSI买入：< {best['params']['rsi_buy']}
  止盈：{int(best['params']['profit_pct']*100)}%
  回撤止盈：{int(best['params']['trail_pct']*100)}%
  止损：{int(best['params']['stop_loss']*100)}%

效果：
  覆盖股票：{best['valid_stocks']} 只
  总交易：{best['total_trades']} 次
  胜率：{best['avg_win_rate']*100:.1f}%
  期望收益：{best['avg_expected']*100:+.2f}%
  盈利时赚：{best['avg_win_pct']*100:+.2f}%
  亏损时亏：{best['avg_loss_pct']*100:+.2f}%

⏱️ 耗时：{elapsed:.0f}秒
""", flush=True)
    
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
    
    results_df.to_csv(RESULTS_DIR / f'fast_profit_opt_{timestamp}.csv',
                      index=False, encoding='utf-8-sig')
    
    print(f"💾 结果已保存：fast_profit_opt_{timestamp}.csv", flush=True)
    
    return all_results


if __name__ == '__main__':
    fast_optimize()