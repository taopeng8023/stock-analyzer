#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略回测总执行脚本
按优先级执行所有策略回测并生成最终对比报告
"""

import subprocess
import pandas as pd
from datetime import datetime
from pathlib import Path

RESULTS_DIR = Path('backtest_results')

def run_backtest(script_name, description):
    """执行回测脚本"""
    print(f"\n{'='*80}")
    print(f"执行：{description}")
    print(f"{'='*80}")
    
    result = subprocess.run(
        ['python3.11', script_name],
        capture_output=True,
        text=True,
        timeout=600
    )
    
    if result.returncode == 0:
        print(f"✅ {description} 完成")
        return True
    else:
        print(f"❌ {description} 失败：{result.stderr}")
        return False


def generate_final_report():
    """生成最终对比报告"""
    print("\n" + "="*80)
    print("生成最终对比报告...")
    print("="*80)
    
    # 收集所有回测结果
    all_results = []
    
    # 1. 交叉信号 Top5 全市场结果
    top5_file = list(RESULTS_DIR.glob('top5_full_market_summary_*.csv'))
    if top5_file:
        df = pd.read_csv(top5_file[0])
        for _, row in df.iterrows():
            all_results.append({
                '策略': f"交叉信号-{row['均线组合']}+{row['成交量信号']}",
                '平均收益': row['实际收益'] * 100,
                '盈利比例': row['盈利比例'],
                '平均胜率': row['平均胜率'],
                '平均回撤': row['平均回撤'] * 100,
                '交易次数': row['平均交易次数']
            })
    
    # 2. 三均线策略结果
    triple_files = list(RESULTS_DIR.glob('triple_ma_full_market_*.csv'))
    if triple_files:
        df = pd.read_csv(triple_files[0])
        for _, row in df.iterrows():
            all_results.append({
                '策略': f"三均线-{row['combo']}",
                '平均收益': row['avg_return'] * 100,
                '盈利比例': row['profit_ratio'],
                '平均胜率': row['win_rate'],
                '平均回撤': row['max_drawdown'] * 100,
                '交易次数': row['avg_trades']
            })
    
    # 3. 止盈止损优化结果
    exit_files = list(RESULTS_DIR.glob('exit_optimization_*.csv'))
    if exit_files:
        df = pd.read_csv(exit_files[0])
        for _, row in df.iterrows():
            all_results.append({
                '策略': f"止盈止损-{row['exit_combo']}",
                '平均收益': row['avg_return'] * 100,
                '盈利比例': row['profit_ratio'],
                '平均胜率': row['win_rate'],
                '平均回撤': None,
                '交易次数': None
            })
    
    # 4. 均线+MACD结果
    ma_macd_files = list(RESULTS_DIR.glob('ma_macd_full_market_*.csv'))
    if ma_macd_files:
        df = pd.read_csv(ma_macd_files[0])
        for _, row in df.iterrows():
            all_results.append({
                '策略': f"均线+MACD-{row['combo']}",
                '平均收益': row['avg_return'] * 100,
                '盈利比例': row['profit_ratio'],
                '平均胜率': row['win_rate'],
                '平均回撤': None,
                '交易次数': None
            })
    
    # 生成 DataFrame 并排序
    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values('平均收益', ascending=False)
    
    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = RESULTS_DIR / f'FINAL_STRATEGY_COMPARISON_{timestamp}.csv'
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    # 生成 Markdown 报告
    generate_markdown_report(results_df, timestamp)
    
    print(f"\n最终报告已保存：{output_file}")
    return results_df


def generate_markdown_report(df, timestamp):
    """生成 Markdown 报告"""
    report = f"""# 全策略回测最终对比报告

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**数据源**: Tushare 缓存数据 (全市场 3620 只股票)  
**测试策略**: 交叉信号/三均线/止盈止损/均线+MACD

---

## 🏆 Top 20 最佳策略 (按平均收益排序)

| 排名 | 策略 | 平均收益 | 盈利比例 | 胜率 | 回撤 | 交易次数 |
|------|------|---------|---------|------|------|---------|
"""
    
    for i, (_, row) in enumerate(df.head(20).iterrows(), 1):
        report += f"| {i} | {row['策略']} | **{row['平均收益']:.2f}%** | {row['盈利比例']:.1f}% | {row['平均胜率']:.1f}% | {row['平均回撤'] if pd.notna(row['平均回撤']) else '-'} | {row['交易次数'] if pd.notna(row['交易次数']) else '-'} |\n"
    
    report += f"""
---

## 📊 各类策略最佳表现

### 交叉信号策略 Top 3

"""
    
    cross_df = df[df['策略'].str.contains('交叉信号')]
    for i, (_, row) in enumerate(cross_df.head(3).iterrows(), 1):
        report += f"{i}. **{row['策略']}**: +{row['平均收益']:.2f}% (盈利{row['盈利比例']:.1f}%)\n"
    
    report += f"""
### 三均线策略 Top 3

"""
    
    triple_df = df[df['策略'].str.contains('三均线')]
    for i, (_, row) in enumerate(triple_df.head(3).iterrows(), 1):
        report += f"{i}. **{row['策略']}**: +{row['平均收益']:.2f}% (盈利{row['盈利比例']:.1f}%)\n"
    
    report += f"""
### 止盈止损策略 Top 3

"""
    
    exit_df = df[df['策略'].str.contains('止盈止损')]
    for i, (_, row) in enumerate(exit_df.head(3).iterrows(), 1):
        report += f"{i}. **{row['策略']}**: +{row['平均收益']:.2f}% (盈利{row['盈利比例']:.1f}%)\n"
    
    report += f"""
### 均线+MACD 策略 Top 3

"""
    
    ma_macd_df = df[df['策略'].str.contains('均线+MACD')]
    for i, (_, row) in enumerate(ma_macd_df.head(3).iterrows(), 1):
        report += f"{i}. **{row['策略']}**: +{row['平均收益']:.2f}% (盈利{row['盈利比例']:.1f}%)\n"
    
    # 找出最佳策略
    best = df.iloc[0]
    report += f"""
---

## 🥇 最终推荐：最佳策略

**策略**: {best['策略']}  
**平均收益**: **+{best['平均收益']:.2f}%**  
**盈利比例**: **{best['盈利比例']:.1f}%**  
**平均胜率**: {best['平均胜率']:.1f}%  
**平均回撤**: {best['平均回撤'] if pd.notna(best['平均回撤']) else 'N/A'}%  
**交易频率**: {best['交易次数'] if pd.notna(best['交易次数']) else 'N/A'} 次/年

---

## 💡 核心结论

1. **最佳收益策略**: {best['策略']} (+{best['平均收益']:.2f}%)
2. **最高盈利面**: {df.loc[df['盈利比例'].idxmax(), '策略']} ({df['盈利比例'].max():.1f}%)
3. **最稳健策略**: 低回撤 + 高盈利的平衡

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    report_file = RESULTS_DIR / f'FINAL_STRATEGY_REPORT_{timestamp}.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Markdown 报告：{report_file}")


if __name__ == '__main__':
    scripts = [
        ('backtest_triple_ma_full.py', '1. 三均线策略全市场回测'),
        ('backtest_exit_optimize.py', '2. 止盈止损参数优化回测'),
        ('backtest_ma_macd.py', '3. 均线+MACD 组合策略回测'),
    ]
    
    completed = 0
    for script, desc in scripts:
        if run_backtest(script, desc):
            completed += 1
    
    print(f"\n{'='*80}")
    print(f"完成：{completed}/{len(scripts)} 个策略回测")
    print(f"{'='*80}")
    
    # 生成最终报告
    generate_final_report()
