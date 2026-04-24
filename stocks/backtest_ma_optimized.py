#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双均线策略优化版 - 针对假信号问题

优化点：
1. 成交量确认 - 过滤缩量假突破
2. 趋势方向过滤 - 只做 MA60 上方股票
3. 金叉强度过滤 - 金叉幅度>0.5%
4. 移动止盈优化 - 15%（回测最优）

对比组：
- 基础版：无过滤
- 优化版 V1：+成交量
- 优化版 V2：+成交量+趋势
- 优化版 V3：+成交量 + 趋势 + 金叉强度
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

# ============== 策略版本配置 ==============
STRATEGY_VERSIONS = {
    'base': {
        'name': '基础版 (无过滤)',
        'volume_filter': False,
        'trend_filter': False,
        'strength_filter': False,
        'volume_threshold': 1.0,
        'min_strength': 0,
    },
    'v1': {
        'name': '优化 V1 (+成交量)',
        'volume_filter': True,
        'trend_filter': False,
        'strength_filter': False,
        'volume_threshold': 1.5,
        'min_strength': 0,
    },
    'v2': {
        'name': '优化 V2 (+成交量 + 趋势)',
        'volume_filter': True,
        'trend_filter': True,
        'strength_filter': False,
        'volume_threshold': 1.5,
        'min_strength': 0,
    },
    'v3': {
        'name': '优化 V3 (完全版)',
        'volume_filter': True,
        'trend_filter': True,
        'strength_filter': True,
        'volume_threshold': 1.5,
        'min_strength': 0.5,  # 金叉强度>0.5%
    }
}

def load_data(symbol: str) -> pd.DataFrame:
    """加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data or len(data) < 100:
        return None
    
    df = pd.DataFrame(data)
    df = df.rename(columns={
        '日期': 'date', '开盘': 'open', '收盘': 'close',
        '最高': 'high', '最低': 'low', '成交量': 'volume'
    })
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    return df.sort_values('date').reset_index(drop=True)

def generate_signal(df: pd.DataFrame, idx: int, config: dict) -> tuple:
    """
    生成交易信号
    
    Returns: (buy_signal, sell_signal, info)
    """
    if idx < 30:
        return False, False, {}
    
    # 均线
    ma15 = df['ma15'].iloc[idx]
    ma20 = df['ma20'].iloc[idx]
    ma15_prev = df['ma15'].iloc[idx-1]
    ma20_prev = df['ma20'].iloc[idx-1]
    ma60 = df['ma60'].iloc[idx]
    
    if pd.isna([ma15, ma20, ma15_prev, ma20_prev, ma60]).any():
        return False, False, {}
    
    price = df['close'].iloc[idx]
    
    # 金叉信号
    golden_cross = ma15_prev <= ma20_prev and ma15 > ma20
    death_cross = ma15_prev >= ma20_prev and ma15 < ma20
    
    # 金叉强度
    cross_strength = (ma15 - ma20) / ma20 * 100 if ma20 > 0 else 0
    
    # 成交量比
    vol_ma20 = df['volume_ma20'].iloc[idx]
    vol_ratio = df['volume'].iloc[idx] / vol_ma20 if vol_ma20 > 0 else 0
    
    # 趋势方向
    above_ma60 = price > ma60
    
    info = {
        'golden_cross': golden_cross,
        'death_cross': death_cross,
        'cross_strength': cross_strength,
        'vol_ratio': vol_ratio,
        'above_ma60': above_ma60,
    }
    
    # 买入信号检查
    buy_signal = False
    if golden_cross:
        buy_signal = True
        
        # V1: 成交量过滤
        if config['volume_filter'] and vol_ratio < config['volume_threshold']:
            buy_signal = False
            info['reject_reason'] = f'成交量不足 ({vol_ratio:.2f}倍)'
        
        # V2: 趋势过滤
        if config['trend_filter'] and not above_ma60:
            buy_signal = False
            info['reject_reason'] = f'股价在 MA60 下方'
        
        # V3: 金叉强度过滤
        if config['strength_filter'] and cross_strength < config['min_strength']:
            buy_signal = False
            info['reject_reason'] = f'金叉强度不足 ({cross_strength:.2f}%)'
    
    # 卖出信号
    sell_signal = death_cross
    
    return buy_signal, sell_signal, info

def backtest(df: pd.DataFrame, config: dict) -> dict:
    """回测"""
    if len(df) < 100:
        return None
    
    # 计算指标
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    
    # 回测
    capital = 100000
    position = None
    trades = []
    highest_price = 0
    max_drawdown = 0
    peak_equity = capital
    
    # 统计过滤掉的信号
    filtered_signals = 0
    
    for idx in range(40, len(df)):
        price = df['close'].iloc[idx]
        if pd.isna(price) or price <= 0:
            continue
        
        # 计算权益
        if position:
            equity = capital + position['shares'] * price
        else:
            equity = capital
        
        # 最大回撤
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity
        if dd > max_drawdown:
            max_drawdown = dd
        
        # 持仓管理
        if position:
            highest_price = max(highest_price, price)
            
            # 移动止盈 15%
            if highest_price > position['cost'] * 1.10:
                if price <= highest_price * (1 - 0.15):
                    profit = (price - position['cost']) / position['cost'] * 100
                    capital = position['shares'] * price * 0.9997
                    trades.append({
                        'profit': profit,
                        'type': 'trailing_stop',
                        'info': position.get('info', {})
                    })
                    position = None
                    highest_price = 0
            
            # 固定止损 15%
            elif price <= position['cost'] * (1 - 0.15):
                profit = (price - position['cost']) / position['cost'] * 100
                capital = position['shares'] * price * 0.9997
                trades.append({
                    'profit': profit,
                    'type': 'stop_loss',
                    'info': position.get('info', {})
                })
                position = None
                highest_price = 0
        
        # 生成信号
        buy_signal, sell_signal, info = generate_signal(df, idx, config)
        
        # 开仓
        if buy_signal and not position:
            shares = int(capital * 0.95 / price / 100) * 100
            if shares > 0:
                position = {
                    'cost': price,
                    'shares': shares,
                    'info': info
                }
                highest_price = price
        elif info.get('golden_cross') and not buy_signal:
            filtered_signals += 1
        
        # 平仓信号
        if sell_signal and position:
            profit = (price - position['cost']) / position['cost'] * 100
            capital = position['shares'] * price * 0.9997
            trades.append({
                'profit': profit,
                'type': 'death_cross',
                'info': position.get('info', {})
            })
            position = None
            highest_price = 0
    
    # 清空
    if position:
        profit = (df['close'].iloc[-1] - position['cost']) / position['cost'] * 100
        trades.append({'profit': profit, 'type': 'end'})
    
    if not trades:
        return None
    
    # 统计
    profitable = [t for t in trades if t['profit'] > 0]
    losing = [t for t in trades if t['profit'] <= 0]
    
    # 分类统计
    trailing_wins = [t for t in profitable if t.get('type') == 'trailing_stop']
    stop_losses = [t for t in trades if t.get('type') == 'stop_loss']
    
    return {
        'total_return': (capital / 100000 - 1) * 100,
        'win_rate': len(profitable) / len(trades) * 100 if trades else 0,
        'avg_profit': np.mean([t['profit'] for t in trades]),
        'avg_win': np.mean([t['profit'] for t in profitable]) if profitable else 0,
        'avg_loss': np.mean([t['profit'] for t in losing]) if losing else 0,
        'trades': len(trades),
        'max_drawdown': max_drawdown * 100,
        'filtered_signals': filtered_signals,
        'trailing_wins': len(trailing_wins),
        'stop_losses': len(stop_losses),
    }

def backtest_all_versions():
    """回测所有版本"""
    print("=" * 80)
    print("🔬 双均线策略优化版回测")
    print(f"📅 回测时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    print(f"\n📋 优化方案:")
    print(f"   基础版：无过滤")
    print(f"   优化 V1: +成交量>1.5 倍")
    print(f"   优化 V2: +成交量 + 股价>MA60")
    print(f"   优化 V3: +成交量 + 趋势 + 金叉强度>0.5%")
    
    stock_files = list(CACHE_DIR.glob('*.json'))
    total = len(stock_files)
    
    print(f"\n🔍 回测全市场 {total} 只股票...\n")
    
    # 所有版本结果
    all_results = {ver: [] for ver in STRATEGY_VERSIONS.keys()}
    
    for i, filepath in enumerate(stock_files):
        symbol = filepath.stem
        df = load_data(symbol)
        
        if df is None:
            continue
        
        # 回测所有版本
        for ver, config in STRATEGY_VERSIONS.items():
            result = backtest(df, config)
            if result:
                result['symbol'] = symbol
                all_results[ver].append(result)
        
        if (i + 1) % 1000 == 0:
            print(f"  进度：{i+1}/{total} ({(i+1)/total*100:.1f}%)")
    
    print(f"\n✅ 回测完成\n")
    
    # 输出对比
    print_comparison(all_results)
    
    return all_results

def print_comparison(all_results: dict):
    """打印对比结果"""
    print("=" * 80)
    print("📊 策略版本对比")
    print("=" * 80)
    
    print(f"\n{'版本':<20} {'平均收益':>12} {'中位收益':>12} {'胜率':>10} {'盈利股':>10} {'回撤':>10} {'过滤':>10}")
    print("-" * 95)
    
    summary = []
    
    for ver, config in STRATEGY_VERSIONS.items():
        results = all_results[ver]
        if not results:
            continue
        
        avg_return = np.mean([r['total_return'] for r in results])
        median_return = np.median([r['total_return'] for r in results])
        avg_winrate = np.mean([r['win_rate'] for r in results])
        profitable = len([r for r in results if r['total_return'] > 0])
        profitable_ratio = profitable / len(results) * 100
        avg_maxdd = np.mean([r['max_drawdown'] for r in results])
        avg_filtered = np.mean([r['filtered_signals'] for r in results])
        
        summary.append({
            'ver': ver,
            'name': config['name'],
            'avg_return': avg_return,
            'median_return': median_return,
            'win_rate': avg_winrate,
            'profitable_ratio': profitable_ratio,
            'max_drawdown': avg_maxdd,
            'avg_filtered': avg_filtered,
            'count': len(results)
        })
        
        print(f"{config['name']:<20} {avg_return:>10.2f}% {median_return:>10.2f}% {avg_winrate:>8.1f}% {profitable_ratio:>8.1f}% {avg_maxdd:>8.2f}% {avg_filtered:>8.1f}")
    
    print("-" * 95)
    
    # 最佳版本
    print("\n" + "=" * 80)
    best = max(summary, key=lambda x: x['avg_return'])
    print(f"🏆 最佳版本：{best['name']}")
    print(f"   平均收益：{best['avg_return']:.2f}%")
    print(f"   中位收益：{best['median_return']:.2f}%")
    print(f"   胜率：{best['win_rate']:.1f}%")
    print(f"   盈利股票：{best['profitable_ratio']:.1f}%")
    print(f"   平均回撤：{best['max_drawdown']:.2f}%")
    print(f"   平均过滤信号：{best['avg_filtered']:.1f}个/股")
    
    # 与基础版对比
    base = next(s for s in summary if s['ver'] == 'base')
    print(f"\n📊 与基础版对比:")
    print(f"   收益提升：{best['avg_return'] - base['avg_return']:+.2f}%")
    print(f"   胜率提升：{best['win_rate'] - base['win_rate']:+.1f}%")
    print(f"   回撤改善：{base['max_drawdown'] - best['max_drawdown']:+.2f}%")
    
    # TOP 10
    results = all_results[best['ver']]
    results.sort(key=lambda x: x['total_return'], reverse=True)
    
    print(f"\n🏆 {best['name']} TOP 10:")
    for i, r in enumerate(results[:10], 1):
        print(f"  {i}. {r['symbol']}: {r['total_return']:+.2f}% (胜率{r['win_rate']:.1f}%, 过滤{r['filtered_signals']}个假信号)")
    
    # 结论
    print("\n" + "=" * 80)
    print("💡 结论与建议")
    print("=" * 80)
    
    if best['avg_return'] > base['avg_return'] + 5:
        print(f"\n✅ 优化版显著优于基础版！")
        print(f"   推荐使用：{best['name']}")
    elif best['avg_return'] > base['avg_return']:
        print(f"\n👍 优化版略有优势")
        print(f"   推荐使用：{best['name']}")
    else:
        print(f"\n⚠️ 优化版不如基础版")
        print(f"   建议：继续使用基础版，避免过度过滤")
    
    print("=" * 80)

if __name__ == '__main__':
    results = backtest_all_versions()
