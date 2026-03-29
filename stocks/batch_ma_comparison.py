#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双均线组合批量回测对比
使用 Tushare 缓存数据对全市场回测，对比不同均线组合的表现
"""

import subprocess
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import time

# 双均线组合配置
MA_COMBINATIONS = [
    {'short': 5, 'long': 20, 'name': 'MA5/MA20'},
    {'short': 10, 'long': 20, 'name': 'MA10/MA20'},
    {'short': 10, 'long': 30, 'name': 'MA10/MA30'},
    {'short': 15, 'long': 20, 'name': 'MA15/MA20'},
    {'short': 15, 'long': 30, 'name': 'MA15/MA30'},
    {'short': 20, 'long': 30, 'name': 'MA20/MA30'},
    {'short': 20, 'long': 60, 'name': 'MA20/MA60'},
    {'short': 30, 'long': 60, 'name': 'MA30/MA60'},
]

def run_backtest(short_ma, long_ma):
    """运行单次日测"""
    print(f"\n{'='*70}")
    print(f"开始回测：MA{short_ma}/MA{long_ma} 组合")
    print(f"{'='*70}")
    
    cmd = [
        'python3.11', 'backtest_v3_cache.py',
        '--all',
        '--no-filters',
        '--no-log',
        '--short-ma', str(short_ma),
        '--long-ma', str(long_ma),
        '--sample', '500'  # 抽样 500 只加快测试
    ]
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True
    )
    
    # 解析结果
    output = result.stdout + result.stderr
    
    # 提取统计数据
    stats = {
        'short_ma': short_ma,
        'long_ma': long_ma,
        'name': f'MA{short_ma}/MA{long_ma}'
    }
    
    # 解析平均收益
    if '平均收益：' in output:
        for line in output.split('\n'):
            if '平均收益：' in line:
                try:
                    value = line.split('平均收益：')[1].strip().replace('%', '')
                    stats['avg_return'] = float(value)
                except:
                    stats['avg_return'] = None
            elif '中位收益：' in line:
                try:
                    value = line.split('中位收益：')[1].strip().replace('%', '')
                    stats['median_return'] = float(value)
                except:
                    stats['median_return'] = None
            elif '盈利股票数：' in line:
                try:
                    value = line.split('盈利股票数：')[1].strip().replace('只', '').replace('(', '').split('%')[0]
                    stats['win_rate'] = float(value)
                except:
                    stats['win_rate'] = None
            elif '平均交易次数：' in line:
                try:
                    value = line.split('平均交易次数：')[1].strip().replace('次', '')
                    stats['avg_trades'] = float(value)
                except:
                    stats['avg_trades'] = None
            elif '平均胜率：' in line:
                try:
                    value = line.split('平均胜率：')[1].strip().replace('%', '')
                    stats['avg_win_rate'] = float(value)
                except:
                    stats['avg_win_rate'] = None
            elif '平均最大回撤：' in line:
                try:
                    value = line.split('平均最大回撤：')[1].strip().replace('%', '')
                    stats['max_drawdown'] = float(value)
                except:
                    stats['max_drawdown'] = None
    
    return stats


def main():
    print("="*70)
    print("双均线组合批量回测对比")
    print("="*70)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试组合数：{len(MA_COMBINATIONS)} 组")
    print(f"抽样数量：500 只股票/组合")
    print("="*70)
    
    results = []
    total_start = time.time()
    
    for i, combo in enumerate(MA_COMBINATIONS, 1):
        print(f"\n[{i}/{len(MA_COMBINATIONS)}] 测试 {combo['name']}")
        
        stats = run_backtest(combo['short'], combo['long'])
        results.append(stats)
        
        print(f"✅ {combo['name']} 完成")
        if 'avg_return' in stats:
            print(f"   平均收益：{stats.get('avg_return', 'N/A')}%")
    
    total_time = time.time() - total_start
    
    # 生成对比报告
    print("\n" + "="*70)
    print("回测对比报告")
    print("="*70)
    
    df = pd.DataFrame(results)
    
    # 排序
    df_sorted = df.sort_values('avg_return', ascending=False)
    
    print("\n📊 各均线组合表现对比 (按平均收益排序)")
    print("-"*70)
    print(f"{'组合':<15} {'平均收益':>10} {'中位收益':>10} {'胜率':>8} {'交易次数':>10} {'胜率':>8} {'最大回撤':>10}")
    print("-"*70)
    
    for _, row in df_sorted.iterrows():
        print(f"{row['name']:<15} {row.get('avg_return', 0):>9.2f}% {row.get('median_return', 0):>9.2f}% "
              f"{row.get('win_rate', 0):>7.1f}% {row.get('avg_trades', 0):>9.1f}次 "
              f"{row.get('avg_win_rate', 0):>7.1f}% {row.get('max_drawdown', 0):>9.1f}%")
    
    print("-"*70)
    
    # 最佳组合
    best = df_sorted.iloc[0]
    print(f"\n🏆 最佳组合：{best['name']}")
    print(f"   平均收益：{best.get('avg_return', 0):.2f}%")
    print(f"   中位收益：{best.get('median_return', 0):.2f}%")
    print(f"   盈利比例：{best.get('win_rate', 0):.1f}%")
    
    # 保存结果
    results_dir = Path(__file__).parent / 'backtest_results'
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = results_dir / f'ma_combinations_comparison_{timestamp}.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n💾 详细结果已保存至：{output_file}")
    print(f"\n总耗时：{total_time/60:.1f} 分钟")
    print(f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 生成 JSON 报告
    json_file = results_dir / f'ma_combinations_comparison_{timestamp}.json'
    report = {
        'timestamp': timestamp,
        'total_time_minutes': total_time / 60,
        'sample_size': 500,
        'combinations_tested': len(MA_COMBINATIONS),
        'results': results,
        'best_combination': {
            'name': best['name'],
            'avg_return': best.get('avg_return', 0),
            'median_return': best.get('median_return', 0),
            'win_rate': best.get('win_rate', 0)
        }
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📄 JSON 报告已保存至：{json_file}")


if __name__ == '__main__':
    main()
