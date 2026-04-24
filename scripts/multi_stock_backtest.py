#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多股票批量回测系统
对比不同股票上的策略表现
"""

import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/scripts')

import json
import os
from datetime import datetime
from typing import Dict, List
import numpy as np

# 导入回测 v2.0 模块
from stock_backtest_v2 import (
    generate_historical_data,
    calculate_indicators,
    calculate_score_v2,
    BacktestEngineV2,
    trading_strategy_v2
)

# ==================== 批量回测 ====================

def run_multi_backtest(stocks: List[Dict], days: int = 250) -> Dict:
    """
    批量回测多只股票
    stocks: [{'code': '600549', 'name': '厦门钨业'}, ...]
    """
    print("=" * 90)
    print(" " * 28 + "多股票批量回测系统")
    print("=" * 90)
    
    results = []
    
    for i, stock in enumerate(stocks, 1):
        print(f"\n{'='*90}")
        print(f"📊 回测 {i}/{len(stocks)}: {stock['name']} ({stock['code']})")
        print(f"{'='*90}")
        
        result = run_single_backtest(
            stock['code'], 
            stock['name'], 
            days
        )
        results.append(result)
    
    # 生成对比报告
    print_comparison_report(results)
    
    return {'stocks': results, 'summary': generate_summary(results)}

def run_single_backtest(code: str, name: str, days: int = 250) -> Dict:
    """单只股票回测"""
    
    # 生成历史数据
    data = generate_historical_data(code, name, days)
    
    # 初始化回测引擎
    engine = BacktestEngineV2(initial_capital=100000)
    
    # 回测参数
    take_profit = 0.15
    stop_loss = 0.06
    trailing_stop_start = 0.08
    trailing_stop_pct = 0.05
    
    hold_days = 0
    buy_price = 0
    prev_score = 50
    peak_return = 0
    
    # 逐日回测
    for i in range(60, len(data)):
        day_data = data[:i+1]
        current = day_data[-1]
        
        # 计算技术指标
        indicators = calculate_indicators(day_data)
        
        # 计算综合评分
        score, score_details = calculate_score_v2(day_data, indicators)
        
        # 当前收益率
        current_return = (current['close'] - buy_price) / buy_price if buy_price > 0 else 0
        peak_return = max(peak_return, current_return)
        
        # 获取交易信号
        signal = trading_strategy_v2(score, indicators, prev_score, hold_days, current_return)
        
        # 执行交易
        if signal == 'buy' and engine.position == 0:
            shares = engine.get_position_size(current['close'], score)
            if shares > 0:
                engine.buy(current['date'], current['close'], shares, f"评分={score:.1f}")
                buy_price = current['close']
                hold_days = 0
                peak_return = 0
        
        elif signal == 'sell' and engine.position > 0:
            reason = f"评分={score:.1f}"
            if current_return > take_profit:
                reason += " 止盈"
            elif current_return < -stop_loss:
                reason += " 止损"
            elif peak_return > trailing_stop_start and current_return < peak_return - trailing_stop_pct:
                reason += " 追踪止损"
            
            engine.sell(current['date'], current['close'], reason=reason)
            hold_days = 0
            buy_price = 0
            peak_return = 0
        
        elif engine.position > 0:
            hold_days += 1
            
            # 检查止盈止损
            if hold_days > 0 and buy_price > 0:
                if current_return > take_profit:
                    engine.sell(current['date'], current['close'], reason="止盈")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
                elif current_return < -stop_loss:
                    engine.sell(current['date'], current['close'], reason="止损")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
                elif peak_return > trailing_stop_start and current_return < peak_return - trailing_stop_pct:
                    engine.sell(current['date'], current['close'], reason="追踪止损")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
        
        prev_score = score
    
    # 强制平仓
    if engine.position > 0:
        engine.sell(data[-1]['date'], data[-1]['close'], reason="回测结束")
    
    # 计算结果
    total_trades = len([t for t in engine.trades if t['type'] == '卖出'])
    profitable_trades = len([t for t in engine.trades if t['type'] == '卖出' and t.get('profit', 0) > 0])
    win_rate = profitable_trades / total_trades * 100 if total_trades > 0 else 0
    
    total_profit = sum([t.get('profit', 0) for t in engine.trades if t['type'] == '卖出'])
    avg_profit = total_profit / total_trades if total_trades > 0 else 0
    
    final_value = engine.initial_capital + total_profit
    total_return = (final_value - engine.initial_capital) / engine.initial_capital * 100
    
    return {
        'code': code,
        'name': name,
        'period': days,
        'initial_capital': engine.initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'max_drawdown': engine.max_drawdown,
        'trades': engine.trades,
        'annual_return': total_return * 250 / days,
    }

def print_comparison_report(results: List[Dict]):
    """打印对比报告"""
    print("\n" + "=" * 90)
    print(" " * 32 + "回测对比报告")
    print("=" * 90)
    
    # 表格头部
    print(f"\n{'股票':<12} {'收益率':<10} {'胜率':<8} {'交易次数':<10} {'最大回撤':<10} {'年化收益':<10}")
    print("-" * 90)
    
    # 排序（按收益率）
    sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
    
    # 打印每只股票
    for r in sorted_results:
        flag = "🥇" if r == sorted_results[0] else ("🥈" if r == sorted_results[1] else ("🥉" if r == sorted_results[2] else "  "))
        print(f"{flag} {r['code']:<8} {r['total_return']:>8.2f}% {r['win_rate']:>7.1f}% {r['total_trades']:>10} {r['max_drawdown']:>9.2f}% {r['annual_return']:>9.2f}%")
    
    # 统计汇总
    avg_return = np.mean([r['total_return'] for r in results])
    avg_winrate = np.mean([r['win_rate'] for r in results])
    avg_drawdown = np.mean([r['max_drawdown'] for r in results])
    total_trades = sum([r['total_trades'] for r in results])
    
    print("-" * 90)
    print(f"{'平均':<12} {avg_return:>8.2f}% {avg_winrate:>7.1f}% {total_trades:>10} {avg_drawdown:>9.2f}% {np.mean([r['annual_return'] for r in results]):>9.2f}%")

def generate_summary(results: List[Dict]) -> Dict:
    """生成汇总统计"""
    returns = [r['total_return'] for r in results]
    drawdowns = [r['max_drawdown'] for r in results]
    winrates = [r['win_rate'] for r in results]
    
    return {
        'avg_return': np.mean(returns),
        'best_return': max(returns),
        'worst_return': min(returns),
        'avg_drawdown': np.mean(drawdowns),
        'min_drawdown': min(drawdowns),
        'avg_winrate': np.mean(winrates),
        'total_trades': sum([r['total_trades'] for r in results]),
        'profitable_count': len([r for r in results if r['total_return'] > 0]),
        'loss_count': len([r for r in results if r['total_return'] <= 0]),
    }

# ==================== 主函数 ====================

def main():
    """主函数"""
    # 回测股票池
    stocks = [
        {'code': '600549', 'name': '厦门钨业'},
        {'code': '000592', 'name': '平潭发展'},
        {'code': '600186', 'name': '莲花健康'},
    ]
    
    # 运行批量回测
    results = run_multi_backtest(stocks, days=250)
    
    # 保存结果
    output_dir = '/home/admin/.openclaw/workspace/data/backtest'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/multi_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 回测报告已保存：{output_file}")
    
    # 汇总分析
    summary = results['summary']
    print("\n" + "=" * 90)
    print(" " * 35 + "汇总分析")
    print("=" * 90)
    print(f"\n📊 回测股票数：{len(stocks)} 只")
    print(f"📈 盈利股票：{summary['profitable_count']} 只 ({summary['profitable_count']/len(stocks)*100:.0f}%)")
    print(f"📉 亏损股票：{summary['loss_count']} 只 ({summary['loss_count']/len(stocks)*100:.0f}%)")
    print(f"💰 平均收益：{summary['avg_return']:.2f}%")
    print(f"🏆 最佳收益：{summary['best_return']:.2f}%")
    print(f"⚠️ 最差收益：{summary['worst_return']:.2f}%")
    print(f"📉 平均回撤：{summary['avg_drawdown']:.2f}%")
    print(f"🎯 平均胜率：{summary['avg_winrate']:.1f}%")
    print(f"📊 总交易次数：{summary['total_trades']} 次")

if __name__ == "__main__":
    main()
