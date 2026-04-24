#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用今日（2026-03-30）Tushare 数据进行选股分析

基于缠论 + 蜡烛图策略
"""

import json
from pathlib import Path
from datetime import datetime
import numpy as np

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
OUTPUT_DIR = Path('/home/admin/.openclaw/workspace/stocks/daily_selection')
OUTPUT_DIR.mkdir(exist_ok=True)

# 今日日期
TODAY = '20260330'

# 配置
CONFIG = {
    'min_signal_strength': 0.6,
    'top_n': 30,
    'fractal_window': 5,
}


def load_stock_data(symbol):
    """加载股票数据"""
    filepath = DATA_DIR / f'{symbol}.json'
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def get_stock_list():
    """获取所有股票代码"""
    stocks = []
    for f in DATA_DIR.glob('*.json'):
        stocks.append(f.stem)
    return stocks


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
    
    # 锤头线
    if lower > body * 2 and upper < body * 0.5 and lower > total_range * 0.3:
        strength = min(1.0, lower / total_range)
        return '锤头线', strength, 'bull'
    
    # 射击之星
    if upper > body * 2 and lower < body * 0.5 and upper > total_range * 0.3:
        strength = min(1.0, upper / total_range)
        return '射击之星', strength, 'bear'
    
    # 大阳线
    if body > total_range * 0.7 and c > o:
        strength = min(1.0, body / total_range)
        return '大阳线', strength, 'bull'
    
    # 大阴线
    if body > total_range * 0.7 and c < o:
        strength = min(1.0, body / total_range)
        return '大阴线', strength, 'bear'
    
    # 看涨吞没
    if i > 0:
        prev_o = data[i-1]['开盘']
        prev_c = data[i-1]['收盘']
        prev_body = abs(prev_c - prev_o)
        
        if prev_c < prev_o and c > o and o < prev_c and c > prev_o:
            strength = min(1.0, body / (prev_body + 0.01))
            return '看涨吞没', strength, 'bull'
        
        if prev_c > prev_o and c < o and o < prev_o and c > prev_c:
            strength = min(1.0, body / (prev_body + 0.01))
            return '看跌吞没', strength, 'bear'
    
    return None, 0, None


def calc_signal_strength(data, i, pattern_strength):
    """计算综合信号强度"""
    strength = pattern_strength
    
    # 成交量因素
    if i >= 5:
        avg_vol = sum([data[i-j]['成交量'] for j in range(1, 6)]) / 5
        if data[i]['成交量'] > avg_vol * 1.5:
            strength *= 1.2
        elif data[i]['成交量'] < avg_vol * 0.5:
            strength *= 0.8
    
    # 价格位置因素
    if i >= 20:
        recent_low = min([data[i-j]['最低'] for j in range(20)])
        if abs(data[i]['最低'] - recent_low) / recent_low < 0.05:
            strength *= 1.3
    
    # 趋势因素
    if i >= 10:
        if data[i]['收盘'] > data[i-5]['收盘'] * 1.02:
            strength *= 1.1
    
    return min(1.0, strength)


def analyze_today_signal(data, symbol):
    """分析今日信号"""
    if not data or len(data) < 50:
        return None
    
    # 检查最新数据是否是今日
    latest = data[-1]
    if latest['日期'] != TODAY:
        return None
    
    # 检测分型
    top_fractals, bottom_fractals = detect_fractal(data, CONFIG['fractal_window'])
    
    # 检查今日（最后一个交易日）的信号
    i = len(data) - 1
    
    # 检查是否是底分型
    is_bottom_fractal = i in bottom_fractals
    
    # 检查蜡烛图形态
    pattern, pattern_strength, pattern_type = detect_candlestick_pattern(data, i)
    
    # 只看看涨信号
    if pattern_type != 'bull':
        return None
    
    # 计算信号强度
    signal_strength = calc_signal_strength(data, i, pattern_strength)
    
    # 过滤低强度信号
    if signal_strength < CONFIG['min_signal_strength']:
        return None
    
    # 计算技术指标
    closes = [d['收盘'] for d in data]
    
    # MA5, MA20
    ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else None
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    
    # 成交量比率
    if len(data) >= 5:
        avg_vol = sum([data[-j]['成交量'] for j in range(1, 6)]) / 5
        vol_ratio = data[-1]['成交量'] / avg_vol if avg_vol > 0 else 1
    else:
        vol_ratio = 1
    
    return {
        'symbol': symbol,
        'date': latest['日期'],
        'price': latest['收盘'],
        'change_pct': latest['涨跌幅'],
        'pattern': pattern,
        'signal_strength': signal_strength,
        'volume_ratio': vol_ratio,
        'is_bottom_fractal': is_bottom_fractal,
        'ma5': round(ma5, 2) if ma5 else None,
        'ma20': round(ma20, 2) if ma20 else None,
        'trend': '上涨' if (ma5 and ma20 and ma5 > ma20 * 1.02) else ('下跌' if (ma5 and ma20 and ma5 < ma20 * 0.98) else '震荡')
    }


def main():
    print("=" * 100)
    print(f"缠论 + 蜡烛图 今日选股分析 ({TODAY})")
    print("=" * 100)
    print()
    
    # 获取股票列表
    stocks = get_stock_list()
    print(f"扫描股票数：{len(stocks)} 只")
    print()
    
    # 分析所有股票
    all_signals = []
    scanned = 0
    with_today_data = 0
    
    for i, symbol in enumerate(stocks):
        data = load_stock_data(symbol)
        
        if not data:
            continue
        
        # 检查是否有今日数据
        if data[-1]['日期'] == TODAY:
            with_today_data += 1
            
            # 分析信号
            signal = analyze_today_signal(data, symbol)
            if signal:
                all_signals.append(signal)
        
        scanned += 1
        
        # 进度
        if (i + 1) % 1000 == 0:
            print(f"进度：{i+1}/{len(stocks)} (已扫描:{scanned} 今日数据:{with_today_data} 有信号:{len(all_signals)})")
    
    # 按信号强度排序
    all_signals.sort(key=lambda x: x['signal_strength'], reverse=True)
    
    print()
    print(f"扫描完成：{scanned} 只股票")
    print(f"有今日数据：{with_today_data} 只")
    print(f"发现信号：{len(all_signals)} 个")
    print()
    
    # 生成报告
    if not all_signals:
        print("⚠️  未发现符合条件的信号")
        return
    
    # 取前 N 只
    top_signals = all_signals[:CONFIG['top_n']]
    
    # 打印报告
    print("=" * 100)
    print(f"📊 缠论 + 蜡烛图 选股报告 ({TODAY})")
    print("=" * 100)
    print()
    print(f"{'排名':<6} {'代码':<10} {'价格':<10} {'形态':<12} {'强度':<8} {'量比':<8} {'涨幅%':<10} {'趋势':<10} {'分型':<8}")
    print("-" * 100)
    
    for i, s in enumerate(top_signals, 1):
        fractal_icon = '✅' if s['is_bottom_fractal'] else '❌'
        print(f"{i:<6} {s['symbol']:<10} {s['price']:<10.2f} {s['pattern']:<12} {s['signal_strength']:<8.2f} {s['volume_ratio']:<8.2f} {s['change_pct']:<10.2f} {s['trend']:<10} {fractal_icon:<8}")
    
    print("=" * 100)
    
    # 保存报告
    report = {
        'date': TODAY,
        'time': datetime.now().isoformat(),
        'total_scanned': scanned,
        'with_today_data': with_today_data,
        'total_signals': len(all_signals),
        'top_signals': top_signals,
        'config': CONFIG
    }
    
    report_file = OUTPUT_DIR / f'selection_{TODAY}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 保存文本格式
    text_file = OUTPUT_DIR / f'selection_{TODAY}.txt'
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(f"缠论 + 蜡烛图 选股报告 ({TODAY})\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"{'排名':<6} {'代码':<10} {'形态':<12} {'强度':<8} {'量比':<8} {'涨幅%':<10}\n")
        f.write("-" * 80 + "\n")
        for i, s in enumerate(top_signals, 1):
            f.write(f"{i:<6} {s['symbol']:<10} {s['pattern']:<12} {s['signal_strength']:<8.2f} {s['volume_ratio']:<8.2f} {s['change_pct']:<10.2f}\n")
    
    print(f"\n💾 报告已保存:")
    print(f"   JSON: {report_file}")
    print(f"   TXT:  {text_file}")
    
    # 统计
    print("\n📊 信号统计:")
    patterns = {}
    for s in all_signals:
        p = s['pattern']
        patterns[p] = patterns.get(p, 0) + 1
    
    for p, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"   {p}: {count} 只")
    
    print()
    print("=" * 100)


if __name__ == '__main__':
    main()
