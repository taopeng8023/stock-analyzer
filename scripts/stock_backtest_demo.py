#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票回测系统 - 本地数据版
当无法获取真实 API 数据时，使用此版本进行演示
【重要】实际使用时请替换为真实数据
"""

import json
import os
from datetime import datetime, timedelta
import numpy as np

def generate_demo_data(code: str, name: str, days: int = 250) -> list:
    """
    生成演示数据（基于真实股票的大致价格范围）
    【注意】这是演示数据，实际使用请替换为真实 API 数据
    """
    # 基于真实股票的历史价格范围
    price_ranges = {
        '600549': (15.0, 25.0),   # 厦门钨业
        '000592': (2.0, 5.0),      # 平潭发展
        '600186': (5.0, 12.0),     # 莲花健康
    }
    
    min_price, max_price = price_ranges.get(code, (10.0, 20.0))
    base_price = (min_price + max_price) / 2
    
    np.random.seed(hash(code) % 2**32)
    data = []
    current_price = base_price
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d')
        
        # 生成合理的股价波动
        change = np.random.randn() * 0.02  # 2% 日波动
        trend = np.sin(i / 30) * 0.01  # 周期性趋势
        
        close = current_price * (1 + change + trend)
        close = max(min_price * 0.8, min(max_price * 1.2, close))  # 限制价格范围
        
        high = close * (1 + abs(np.random.randn() * 0.015))
        low = close * (1 - abs(np.random.randn() * 0.015))
        open_price = low + (high - low) * np.random.rand()
        volume = int(np.random.randint(50000, 500000) * (base_price / 10))
        
        data.append({
            'date': date,
            'open': round(open_price, 2),
            'close': round(close, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'volume': volume,
            'amount': round(volume * open_price, 2),
            'amplitude': round((high - low) / close * 100, 2),
            'change_pct': round((close - current_price) / current_price * 100, 2),
            'change': round(close - current_price, 2),
            'turnover': round(np.random.rand() * 3, 2)
        })
        
        current_price = close
    
    print(f"✅ 生成 {code} {name} 演示数据 {len(data)} 条")
    print(f"   价格范围：{min(d['close'] for d in data):.2f} - {max(d['close'] for d in data):.2f}元")
    print(f"   数据范围：{data[0]['date']} 至 {data[-1]['date']}")
    
    return data

def run_backtest_demo(code: str, name: str, days: int = 250):
    """运行演示回测"""
    print("=" * 90)
    print(" " * 25 + "股票策略回测系统 - 演示版")
    print("=" * 90)
    print(f"\n📊 回测标的：{name} ({code})")
    print(f"📅 回测周期：{days} 交易日")
    print(f"💰 初始资金：100,000 元")
    print(f"⚠️  【演示】使用模拟数据，实际使用请接入真实 API")
    print("-" * 90)
    
    # 生成演示数据
    data = generate_demo_data(code, name, days)
    
    # 导入回测引擎
    import sys
    sys.path.insert(0, '/home/admin/.openclaw/workspace/scripts')
    from stock_backtest_real_api import (
        calculate_indicators,
        calculate_score,
        trading_strategy,
        BacktestEngine
    )
    
    # 初始化回测引擎
    engine = BacktestEngine(initial_capital=100000)
    
    # 回测参数
    take_profit = 0.15
    stop_loss = 0.06
    
    hold_days = 0
    buy_price = 0
    prev_score = 50
    peak_return = 0
    
    print(f"\n📊 开始回测...")
    print("-" * 90)
    
    trade_count = 0
    for i in range(60, len(data)):
        day_data = data[:i+1]
        current = day_data[-1]
        
        indicators = calculate_indicators(day_data)
        score, score_details = calculate_score(day_data, indicators, None)
        
        current_return = (current['close'] - buy_price) / buy_price if buy_price > 0 else 0
        peak_return = max(peak_return, current_return)
        
        signal = trading_strategy(score, indicators, prev_score, hold_days, current_return, peak_return)
        
        if signal == 'buy' and engine.position == 0:
            shares = engine.get_position_size(current['close'], score)
            if shares > 0:
                engine.buy(current['date'], current['close'], shares, f"评分={score:.1f}")
                buy_price = current['close']
                hold_days = 0
                peak_return = 0
                trade_count += 1
                print(f"📈 [{current['date']}] 买入 {shares}股 @ {current['close']:.2f}元 (评分={score:.1f})")
        
        elif signal == 'sell' and engine.position > 0:
            reason = f"评分={score:.1f}"
            if current_return > take_profit:
                reason += " 止盈"
            elif current_return < -stop_loss:
                reason += " 止损"
            
            engine.sell(current['date'], current['close'], reason=reason)
            profit_pct = (current['close'] - buy_price) / buy_price * 100
            print(f"📉 [{current['date']}] 卖出 @ {current['close']:.2f}元 收益率={profit_pct:.1f}%")
            hold_days = 0
            buy_price = 0
            peak_return = 0
        
        elif engine.position > 0:
            hold_days += 1
            
            if hold_days > 0 and buy_price > 0:
                if current_return > take_profit:
                    engine.sell(current['date'], current['close'], reason="止盈")
                    print(f"📉 [{current['date']}] 止盈卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}%")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
                elif current_return < -stop_loss:
                    engine.sell(current['date'], current['close'], reason="止损")
                    print(f"📉 [{current['date']}] 止损卖出 @ {current['close']:.2f}元 收益率={current_return*100:.1f}%")
                    hold_days = 0
                    buy_price = 0
                    peak_return = 0
        
        prev_score = score
    
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
    
    # 输出报告
    print("\n" + "=" * 90)
    print(" " * 38 + "回测报告")
    print("=" * 90)
    
    print(f"\n📊 交易统计")
    print(f"  总交易次数：{total_trades} 次")
    print(f"  盈利次数：{profitable_trades} 次")
    print(f"  亏损次数：{total_trades - profitable_trades} 次")
    print(f"  胜率：{win_rate:.1f}%")
    
    print(f"\n💰 收益统计")
    print(f"  初始资金：{engine.initial_capital:,.0f} 元")
    print(f"  最终资金：{final_value:,.0f} 元")
    print(f"  总收益：{total_profit:,.0f} 元")
    print(f"  总收益率：{total_return:.2f}%")
    
    print(f"\n📉 风险统计")
    print(f"  最大回撤：{engine.max_drawdown:.2f}%")
    
    print(f"\n📈 年化收益率：{total_return * 250 / days:.2f}%")
    
    # 保存结果
    result = {
        'code': code,
        'name': name,
        'version': 'demo',
        'data_source': 'simulated',
        'period': days,
        'initial_capital': engine.initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'max_drawdown': engine.max_drawdown,
        'trades': engine.trades,
        'timestamp': datetime.now().isoformat(),
    }
    
    output_dir = '/home/admin/.openclaw/workspace/data/backtest'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/backtest_demo_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 回测报告已保存：{output_file}")
    print("⚠️ 【演示】本回测使用模拟数据，实际使用请接入真实 API")
    
    return result

if __name__ == "__main__":
    # 回测指定股票
    stocks = [
        {'code': '600549', 'name': '厦门钨业'},
        {'code': '000592', 'name': '平潭发展'},
        {'code': '600186', 'name': '莲花健康'},
    ]
    
    results = []
    for stock in stocks:
        result = run_backtest_demo(stock['code'], stock['name'], days=250)
        if result:
            results.append(result)
    
    # 汇总
    if results:
        print("\n" + "=" * 90)
        print(" " * 35 + "回测汇总")
        print("=" * 90)
        print(f"\n{'股票':<12} {'收益率':<10} {'胜率':<8} {'交易次数':<10} {'最大回撤':<10} {'年化':<10}")
        print("-" * 90)
        for r in sorted(results, key=lambda x: x['total_return'], reverse=True):
            print(f"{r['code']:<8} {r['total_return']:>8.2f}% {r['win_rate']:>7.1f}% {r['total_trades']:>10} {r['max_drawdown']:>9.2f}% {r.get('annual_return', r['total_return']):>9.2f}%")
