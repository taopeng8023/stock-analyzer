#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量回测系统 - 使用采集的缓存数据

功能:
- 批量回测多只股票
- 生成对比报告
- 筛选最优策略标的

用法:
    python3 batch_backtest.py --codes 600549,000001,000002 --days 200
    python3 batch_backtest.py --top 10 --days 200  # 回测表现最好的 10 只
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np

# 导入回测引擎
from backtest_with_cache import (
    load_cached_data, 
    BacktestEngine, 
    print_report, 
    save_report
)


def batch_backtest(codes: List[str], days: int = 200, capital: float = 100000) -> List[Dict]:
    """
    批量回测多只股票
    
    Args:
        codes: 股票代码列表
        days: 回测天数
        capital: 初始资金
    
    Returns:
        回测结果列表
    """
    results = []
    
    print("\n" + "="*80)
    print(f"🚀 批量回测系统 - 共 {len(codes)} 只股票".center(80))
    print("="*80 + "\n")
    
    for i, code in enumerate(codes, 1):
        print(f"\n[{i}/{len(codes)}] 回测 {code}...")
        print("-"*60)
        
        # 加载数据
        data = load_cached_data(code)
        
        if not data or len(data) < days:
            print(f"⚠️ 跳过 {code}: 数据不足 ({len(data) if data else 0}/{days}条)")
            continue
        
        # 截取数据
        data = data[-days:]
        
        # 运行回测
        engine = BacktestEngine(initial_capital=capital)
        result = engine.run(data)
        
        results.append(result)
        
        # 简要输出
        print(f"  收益率：{result['total_return']:+.2f}%")
        print(f"  年化：{result['annualized_return']:+.2f}%")
        print(f"  胜率：{result['win_rate']:.1f}%")
        print(f"  夏普：{result['sharpe_ratio']:.2f}")
    
    return results


def print_comparison_report(results: List[Dict]):
    """打印对比报告"""
    if not results:
        print("❌ 无回测结果")
        return
    
    print("\n" + "="*80)
    print("📊 批量回测对比报告".center(80))
    print("="*80)
    
    # 按收益率排序
    sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
    
    # 打印表头
    print(f"\n{'排名':<6} {'代码':<10} {'收益率':>12} {'年化':>12} {'胜率':>10} {'夏普':>10} {'最大回撤':>12} {'交易次数':>10}")
    print("-"*80)
    
    # 打印结果
    medals = ['🥇', '🥈', '🥉']
    
    for i, result in enumerate(sorted_results):
        medal = medals[i] if i < 3 else f'{i+1}.'
        
        print(f"{medal:<6} {result['code']:<10} {result['total_return']:>+11.2f}% {result['annualized_return']:>+11.2f}% {result['win_rate']:>9.1f}% {result['sharpe_ratio']:>10.2f} {result['max_drawdown']:>11.2f}% {result['total_trades']:>10}")
    
    print("-"*80)
    
    # 统计信息
    avg_return = np.mean([r['total_return'] for r in results])
    avg_win_rate = np.mean([r['win_rate'] for r in results])
    avg_sharpe = np.mean([r['sharpe_ratio'] for r in results])
    
    print(f"\n📈 平均统计:")
    print(f"  平均收益率：{avg_return:+.2f}%")
    print(f"  平均胜率：{avg_win_rate:.1f}%")
    print(f"  平均夏普比率：{avg_sharpe:.2f}")
    
    # 最佳/最差
    best = sorted_results[0]
    worst = sorted_results[-1]
    
    print(f"\n🏆 最佳表现：{best['code']} ({best['total_return']:+.2f}%)")
    print(f"📉 最差表现：{worst['code']} ({worst['total_return']:+.2f}%)")
    
    print("="*80 + "\n")


def get_all_cached_stocks(cache_dir: str = None) -> List[str]:
    """获取所有缓存的股票代码"""
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', datetime.now().strftime('%Y%m'))
    
    if not os.path.exists(cache_dir):
        # 尝试上个月
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', last_month.strftime('%Y%m'))
    
    if not os.path.exists(cache_dir):
        print(f"❌ 缓存目录不存在：{cache_dir}")
        return []
    
    # 获取所有 JSON 文件
    files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
    codes = [f.replace('.json', '') for f in files]
    
    print(f"✅ 找到 {len(codes)} 只股票的缓存数据")
    
    return codes


def select_top_stocks(codes: List[str], top_n: int = 10, days: int = 200) -> List[str]:
    """
    快速筛选表现最好的股票 (简化版回测)
    
    Args:
        codes: 股票代码列表
        top_n: 返回前 N 只
        days: 回测天数
    
    Returns:
        精选的股票代码列表
    """
    print(f"\n🔍 从 {len(codes)} 只股票中筛选前 {top_n} 只...\n")
    
    scores = []
    
    for code in codes:
        data = load_cached_data(code)
        
        if not data or len(data) < days:
            continue
        
        data = data[-days:]
        
        # 简化回测 (只计算总收益，不模拟交易)
        start_price = data[0]['close']
        end_price = data[-1]['close']
        total_return = (end_price - start_price) / start_price * 100
        
        # 波动性
        returns = [(data[i]['close'] - data[i-1]['close']) / data[i-1]['close'] for i in range(1, len(data))]
        volatility = np.std(returns) * 100 if returns else 0
        
        # 夏普比率估算
        avg_return = np.mean(returns) * 100 if returns else 0
        sharpe = (avg_return * 252) / (volatility * np.sqrt(252)) if volatility > 0 else 0
        
        scores.append({
            'code': code,
            'return': total_return,
            'volatility': volatility,
            'sharpe': sharpe
        })
        
        if len(scores) % 500 == 0:
            print(f"  已处理 {len(scores)} 只...")
    
    # 按夏普比率排序
    sorted_scores = sorted(scores, key=lambda x: x['sharpe'], reverse=True)
    
    top_codes = [s['code'] for s in sorted_scores[:top_n]]
    
    print(f"\n✅ 筛选完成，前 {top_n} 只股票:")
    for i, code in enumerate(top_codes, 1):
        s = next(x for x in sorted_scores if x['code'] == code)
        print(f"  {i}. {code} (夏普：{s['sharpe']:.2f}, 收益：{s['return']:+.2f}%)")
    
    return top_codes


def main():
    parser = argparse.ArgumentParser(description='批量回测系统')
    parser.add_argument('--codes', type=str, help='股票代码列表，逗号分隔 (如：600549,000001,000002)')
    parser.add_argument('--top', type=int, help='回测表现最好的 N 只股票')
    parser.add_argument('--days', type=int, default=200, help='回测天数 (默认 200)')
    parser.add_argument('--capital', type=float, default=100000, help='初始资金 (默认 100000)')
    parser.add_argument('--save', action='store_true', help='保存报告到文件')
    
    args = parser.parse_args()
    
    # 获取股票代码
    if args.codes:
        codes = [c.strip() for c in args.codes.split(',')]
    elif args.top:
        # 获取所有缓存股票并筛选
        all_codes = get_all_cached_stocks()
        codes = select_top_stocks(all_codes, top_n=args.top, days=args.days)
    else:
        # 默认回测示例股票
        codes = ['600549', '000001', '000002', '601318', '000858']
        print(f"ℹ️  未指定股票，使用默认示例：{', '.join(codes)}")
    
    # 批量回测
    results = batch_backtest(codes, days=args.days, capital=args.capital)
    
    # 打印对比报告
    print_comparison_report(results)
    
    # 保存报告
    if args.save and results:
        output_dir = os.path.join(os.path.dirname(__file__), 'backtest_results')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_backtest_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # 简化结果
        simplified_results = []
        for r in results:
            sr = r.copy()
            sr['equity_curve'] = r['equity_curve'][::10]
            sr['daily_returns'] = r['daily_returns'][::10]
            sr['trades'] = r['trades'][:20]  # 只保留前 20 笔交易
            simplified_results.append(sr)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'total_stocks': len(results),
                'days': args.days,
                'capital': args.capital,
                'results': simplified_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"📁 批量报告已保存：{filepath}")


if __name__ == '__main__':
    from datetime import timedelta
    main()
