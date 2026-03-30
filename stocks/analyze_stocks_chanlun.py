#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缠论 + 蜡烛图 个股深度分析

对指定股票进行详细的技术分析
"""

import json
from pathlib import Path
from datetime import datetime

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')


def load_stock_data(symbol):
    """加载股票数据"""
    filepath = DATA_DIR / f'{symbol}.json'
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def detect_fractal(data, window=5):
    """检测分型"""
    top_fractals = []
    bottom_fractals = []
    
    for i in range(window, len(data) - window):
        highs = [data[i+j]['最高'] for j in range(-window, window+1)]
        lows = [data[i+j]['最低'] for j in range(-window, window+1)]
        
        if data[i]['最高'] == max(highs):
            left_highs = [data[i+j]['最高'] for j in range(-window, 0)]
            right_highs = [data[i+j]['最高'] for j in range(1, window+1)]
            if data[i]['最高'] > max(left_highs) and data[i]['最高'] >= max(right_highs):
                top_fractals.append(i)
        
        if data[i]['最低'] == min(lows):
            left_lows = [data[i+j]['最低'] for j in range(-window, 0)]
            right_lows = [data[i+j]['最低'] for j in range(1, window+1)]
            if data[i]['最低'] < min(left_lows) and data[i]['最低'] <= min(right_lows):
                bottom_fractals.append(i)
    
    return top_fractals, bottom_fractals


def detect_candlestick_pattern(data, i):
    """检测蜡烛图形态"""
    o = data[i]['开盘']
    h = data[i]['最高']
    l = data[i]['最低']
    c = data[i]['收盘']
    
    body = abs(c - o)
    total_range = h - l
    upper = h - max(o, c)
    lower = min(o, c) - l
    
    if total_range == 0:
        return None, 0, None
    
    patterns = []
    
    # 锤头线
    if lower > body * 2 and upper < body * 0.5 and lower > total_range * 0.3:
        patterns.append(('锤头线', 'bull', 0.8))
    
    # 射击之星
    if upper > body * 2 and lower < body * 0.5 and upper > total_range * 0.3:
        patterns.append(('射击之星', 'bear', 0.8))
    
    # 大阳线
    if body > total_range * 0.7 and c > o:
        patterns.append(('大阳线', 'bull', 0.7))
    
    # 大阴线
    if body > total_range * 0.7 and c < o:
        patterns.append(('大阴线', 'bear', 0.7))
    
    # 十字星
    if body < total_range * 0.1:
        patterns.append(('十字星', 'neutral', 0.5))
    
    # 看涨吞没
    if i > 0:
        prev_o = data[i-1]['开盘']
        prev_c = data[i-1]['收盘']
        prev_body = abs(prev_c - prev_o)
        
        if prev_c < prev_o and c > o and o < prev_c and c > prev_o:
            patterns.append(('看涨吞没', 'bull', 0.9))
        
        if prev_c > prev_o and c < o and o < prev_o and c > prev_c:
            patterns.append(('看跌吞没', 'bear', 0.9))
    
    return patterns if patterns else [(None, None, 0)]


def calc_ma(data, period):
    """计算移动平均线"""
    if len(data) < period:
        return None
    closes = [d['收盘'] for d in data[-period:]]
    return sum(closes) / period


def analyze_stock(symbol):
    """分析单只股票"""
    data = load_stock_data(symbol)
    
    if not data:
        return None
    
    if len(data) < 50:
        return {'error': '数据不足'}
    
    # 基本信息
    latest = data[-1]
    prev_5 = data[-5] if len(data) >= 5 else data[0]
    prev_20 = data[-20] if len(data) >= 20 else data[0]
    
    # 计算均线
    ma5 = calc_ma(data, 5)
    ma20 = calc_ma(data, 20)
    ma60 = calc_ma(data, 60) if len(data) >= 60 else None
    
    # 检测分型
    top_fractals, bottom_fractals = detect_fractal(data)
    
    # 检查最近 10 天的分型
    recent_days = min(10, len(data))
    recent_top = [i for i in top_fractals if i >= len(data) - recent_days]
    recent_bottom = [i for i in bottom_fractals if i >= len(data) - recent_days]
    
    # 检测最新蜡烛图形态
    recent_patterns = []
    for i in range(max(0, len(data)-5), len(data)):
        patterns = detect_candlestick_pattern(data, i)
        for p in patterns:
            if p[0]:
                recent_patterns.append({
                    'date': data[i]['日期'],
                    'pattern': p[0],
                    'type': p[1],
                    'strength': p[2]
                })
    
    # 判断趋势
    trend = '震荡'
    if ma5 and ma20:
        if ma5 > ma20 * 1.02:
            trend = '上涨'
        elif ma5 < ma20 * 0.98:
            trend = '下跌'
    
    # 买卖信号
    signal = '观望'
    signal_reason = []
    
    # 买入信号
    if recent_bottom and any(p['type'] == 'bull' for p in recent_patterns):
        signal = '买入'
        signal_reason.append('底分型 + 看涨形态')
    
    if ma5 and ma20 and ma5 > ma20 * 1.02:
        if signal == '观望':
            signal = '谨慎买入'
        signal_reason.append('均线多头')
    
    # 卖出信号
    if recent_top and any(p['type'] == 'bear' for p in recent_patterns):
        signal = '卖出'
        signal_reason.append('顶分型 + 看跌形态')
    
    if ma5 and ma20 and ma5 < ma20 * 0.98:
        if '卖出' not in signal:
            signal = '谨慎卖出' if signal == '观望' else signal
        signal_reason.append('均线空头')
    
    return {
        'symbol': symbol,
        'latest_date': latest['日期'],
        'price': latest['收盘'],
        'change_pct': latest['涨跌幅'],
        'volume': latest['成交量'],
        'ma5': round(ma5, 2) if ma5 else None,
        'ma20': round(ma20, 2) if ma20 else None,
        'ma60': round(ma60, 2) if ma60 else None,
        'trend': trend,
        'signal': signal,
        'signal_reason': signal_reason,
        'recent_top_fractals': len(recent_top),
        'recent_bottom_fractals': len(recent_bottom),
        'recent_patterns': recent_patterns[-5:],  # 最近 5 个形态
        'data_range': f"{data[0]['日期']} ~ {data[-1]['日期']}",
        'data_count': len(data)
    }


def print_analysis(results):
    """打印分析结果"""
    print("=" * 120)
    print("缠论 + 蜡烛图 个股深度分析")
    print("=" * 120)
    print()
    
    for r in results:
        if 'error' in r:
            print(f"❌ {r.get('symbol', 'Unknown')}: {r['error']}")
            continue
        
        print(f"📈 {r['symbol']} | {r['latest_date']} | 价格：¥{r['price']:.2f} | 涨幅：{r['change_pct']:.2f}%")
        print("-" * 120)
        
        # 均线
        ma_info = []
        if r['ma5']: ma_info.append(f"MA5:¥{r['ma5']:.2f}")
        if r['ma20']: ma_info.append(f"MA20:¥{r['ma20']:.2f}")
        if r['ma60']: ma_info.append(f"MA60:¥{r['ma60']:.2f}")
        print(f"   均线：{' | '.join(ma_info)}")
        
        # 趋势
        trend_icon = {'上涨': '📈', '下跌': '📉', '震荡': '➡️'}
        print(f"   趋势：{trend_icon.get(r['trend'], '')} {r['trend']}")
        
        # 信号
        signal_icon = {
            '买入': '✅', '谨慎买入': '⚠️',
            '卖出': '❌', '谨慎卖出': '⚠️',
            '观望': '⏸️'
        }
        print(f"   信号：{signal_icon.get(r['signal'], '')} {r['signal']}")
        if r['signal_reason']:
            print(f"   原因：{', '.join(r['signal_reason'])}")
        
        # 分型
        print(f"   分型：顶分型 {r['recent_top_fractals']} 次 | 底分型 {r['recent_bottom_fractals']} 次 (近 10 日)")
        
        # 蜡烛图形态
        if r['recent_patterns']:
            print(f"   形态：")
            for p in r['recent_patterns']:
                bull_bear = '🐂' if p['type'] == 'bull' else ('🐻' if p['type'] == 'bear' else '➖')
                print(f"      {p['date']}: {p['pattern']} {bull_bear} 强度:{p['strength']:.1f}")
        
        print()


def main():
    # 用户指定的股票列表
    symbols = [
        '002246', '600433', '600750', '600791', '600901',
        '600135', '002663', '601187', '603365', '002709',
        '603738', '600233', '600645'
    ]
    
    print(f"\n分析股票数：{len(symbols)} 只")
    print(f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    for symbol in symbols:
        print(f"分析 {symbol}...", end=" ")
        result = analyze_stock(symbol)
        if result:
            result['symbol'] = symbol
            results.append(result)
            print("✅")
        else:
            print("❌ 无数据")
    
    print()
    print_analysis(results)
    
    # 保存报告
    report = {
        'time': datetime.now().isoformat(),
        'symbols': symbols,
        'results': results
    }
    
    report_file = Path('/home/admin/.openclaw/workspace/stocks/analysis_reports') / f'stock_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"💾 报告已保存：{report_file}")
    
    # 汇总统计
    buy_count = sum(1 for r in results if '买入' in r.get('signal', ''))
    sell_count = sum(1 for r in results if '卖出' in r.get('signal', ''))
    wait_count = sum(1 for r in results if r.get('signal') == '观望')
    
    print("\n" + "=" * 120)
    print("📊 汇总统计")
    print("=" * 120)
    print(f"   买入信号：{buy_count} 只")
    print(f"   卖出信号：{sell_count} 只")
    print(f"   观望：{wait_count} 只")
    print("=" * 120)
    
    # 推荐关注
    buy_stocks = [r for r in results if r.get('signal') == '买入']
    if buy_stocks:
        print("\n🎯 推荐关注（买入信号）:")
        for r in buy_stocks:
            print(f"   - {r['symbol']} ¥{r['price']:.2f} ({r['change_pct']:.2f}%) - {', '.join(r['signal_reason'])}")


if __name__ == '__main__':
    main()
