#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缠论 + 蜡烛图 每日选股系统

功能:
1. 扫描全量 A 股数据
2. 识别缠论底分型 + 看涨蜡烛图信号
3. 生成选股列表（按信号强度排序）
4. 输出报告并推送

用法:
    python3 daily_stock_selector.py --date 20260330
    python3 daily_stock_selector.py --auto  # 自动识别最新日期
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
OUTPUT_DIR = Path('/home/admin/.openclaw/workspace/stocks/daily_selection')
OUTPUT_DIR.mkdir(exist_ok=True)

# 配置
CONFIG = {
    'min_signal_strength': 0.6,  # 最小信号强度
    'top_n': 30,  # 输出前 N 只股票
    'fractal_window': 5,  # 分型窗口
    'min_volume_ratio': 1.0,  # 最小成交量比率
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
    """
    检测分型
    
    Returns:
        top_fractals: 顶分型位置列表
        bottom_fractals: 底分型位置列表
    """
    top_fractals = []
    bottom_fractals = []
    
    for i in range(window, len(data) - window):
        highs = [data[i+j]['最高'] for j in range(-window, window+1)]
        lows = [data[i+j]['最低'] for j in range(-window, window+1)]
        
        # 顶分型：中间高两边低
        if data[i]['最高'] == max(highs):
            # 确认是局部最高点
            left_highs = [data[i+j]['最高'] for j in range(-window, 0)]
            right_highs = [data[i+j]['最高'] for j in range(1, window+1)]
            if data[i]['最高'] > max(left_highs) and data[i]['最高'] >= max(right_highs):
                top_fractals.append(i)
        
        # 底分型：中间低两边高
        if data[i]['最低'] == min(lows):
            left_lows = [data[i+j]['最低'] for j in range(-window, 0)]
            right_lows = [data[i+j]['最低'] for j in range(1, window+1)]
            if data[i]['最低'] < min(left_lows) and data[i]['最低'] <= min(right_lows):
                bottom_fractals.append(i)
    
    return top_fractals, bottom_fractals


def detect_candlestick_pattern(data, i):
    """
    检测蜡烛图形态
    
    Returns:
        pattern: 形态名称
        strength: 信号强度 (0-1)
        type: 'bull' 或 'bear'
    """
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
    
    # 锤头线 (看涨)
    if lower > body * 2 and upper < body * 0.5 and lower > total_range * 0.3:
        strength = min(1.0, lower / total_range)
        return '锤头线', strength, 'bull'
    
    # 射击之星 (看跌)
    if upper > body * 2 and lower < body * 0.5 and upper > total_range * 0.3:
        strength = min(1.0, upper / total_range)
        return '射击之星', strength, 'bear'
    
    # 大阳线 (看涨)
    if body > total_range * 0.7 and c > o:
        strength = min(1.0, body / total_range)
        return '大阳线', strength, 'bull'
    
    # 大阴线 (看跌)
    if body > total_range * 0.7 and c < o:
        strength = min(1.0, body / total_range)
        return '大阴线', strength, 'bear'
    
    # 看涨吞没 (双 K 线)
    if i > 0:
        prev_o = data[i-1]['开盘']
        prev_c = data[i-1]['收盘']
        prev_body = abs(prev_c - prev_o)
        
        # 看涨吞没
        if prev_c < prev_o and c > o and o < prev_c and c > prev_o:
            strength = min(1.0, body / (prev_body + 0.01))
            return '看涨吞没', strength, 'bull'
        
        # 看跌吞没
        if prev_c > prev_o and c < o and o < prev_o and c > prev_c:
            strength = min(1.0, body / (prev_body + 0.01))
            return '看跌吞没', strength, 'bear'
    
    return None, 0, None


def calc_signal_strength(data, i, pattern, pattern_strength):
    """
    计算综合信号强度
    
    考虑因素:
    1. 蜡烛图形态强度
    2. 成交量变化
    3. 价格位置
    4. 近期趋势
    """
    strength = pattern_strength
    
    # 成交量因素
    if i >= 5:
        avg_vol = sum([data[i-j]['成交量'] for j in range(1, 6)]) / 5
        if data[i]['成交量'] > avg_vol * 1.5:
            strength *= 1.2  # 放量加分
        elif data[i]['成交量'] < avg_vol * 0.5:
            strength *= 0.8  # 缩量减分
    
    # 价格位置因素（接近近期低点加分）
    if i >= 20:
        recent_low = min([data[i-j]['最低'] for j in range(20)])
        if abs(data[i]['最低'] - recent_low) / recent_low < 0.05:
            strength *= 1.3  # 接近低点加分
    
    # 趋势因素（下跌后反弹加分）
    if i >= 10:
        if data[i]['收盘'] > data[i-5]['收盘'] * 1.02:
            strength *= 1.1  # 近期上涨加分
    
    return min(1.0, strength)


def scan_buy_signals(data, symbol):
    """
    扫描买入信号
    
    买入条件:
    1. 出现底分型
    2. 同时出现看涨蜡烛图形态
    3. 信号强度 > 阈值
    """
    signals = []
    
    top_fractals, bottom_fractals = detect_fractal(data, CONFIG['fractal_window'])
    
    # 只检查最近 20 个交易日
    recent_days = min(20, len(data))
    start_idx = len(data) - recent_days
    
    for i in range(start_idx, len(data)):
        # 检查是否是底分型
        if i not in bottom_fractals:
            continue
        
        # 检查蜡烛图形态
        pattern, pattern_strength, pattern_type = detect_candlestick_pattern(data, i)
        
        # 只看看涨信号
        if pattern_type != 'bull':
            continue
        
        # 计算综合信号强度
        signal_strength = calc_signal_strength(data, i, pattern, pattern_strength)
        
        # 过滤低强度信号
        if signal_strength < CONFIG['min_signal_strength']:
            continue
        
        # 检查成交量
        if i >= 5:
            avg_vol = sum([data[i-j]['成交量'] for j in range(1, 6)]) / 5
            vol_ratio = data[i]['成交量'] / avg_vol
            if vol_ratio < CONFIG['min_volume_ratio']:
                continue
        
        # 记录信号
        signals.append({
            'symbol': symbol,
            'date': data[i]['日期'],
            'price': data[i]['收盘'],
            'pattern': pattern,
            'signal_strength': signal_strength,
            'volume_ratio': data[i]['成交量'] / avg_vol if i >= 5 else 1.0,
            'change_pct': data[i]['涨跌幅'],
            'fractal_type': '底分型'
        })
    
    return signals


def scan_all_stocks(date=None):
    """扫描所有股票"""
    print("=" * 80)
    print("缠论 + 蜡烛图 每日选股")
    print("=" * 80)
    
    if date:
        print(f"选股日期：{date}")
    else:
        print("选股日期：自动识别最新交易日")
    print()
    
    stocks = get_stock_list()
    print(f"扫描股票数：{len(stocks)} 只")
    print()
    
    all_signals = []
    scanned = 0
    with_signals = 0
    
    for i, symbol in enumerate(stocks):
        data = load_stock_data(symbol)
        if not data or len(data) < 50:
            continue
        
        signals = scan_buy_signals(data, symbol)
        
        if signals:
            all_signals.extend(signals)
            with_signals += 1
        
        scanned += 1
        
        # 进度
        if (i + 1) % 500 == 0:
            print(f"进度：{i+1}/{len(stocks)} (已扫描:{scanned} 有信号:{with_signals})")
    
    # 按信号强度排序
    all_signals.sort(key=lambda x: x['signal_strength'], reverse=True)
    
    print()
    print(f"扫描完成：{scanned} 只股票")
    print(f"发现信号：{len(all_signals)} 个")
    print(f"有信号股票：{with_signals} 只")
    
    return all_signals


def generate_report(signals, date=None):
    """生成选股报告"""
    if not signals:
        print("\n⚠️  未发现符合条件的信号")
        return None
    
    # 去重（每只股票只保留最强信号）
    unique_signals = {}
    for s in signals:
        symbol = s['symbol']
        if symbol not in unique_signals or s['signal_strength'] > unique_signals[symbol]['signal_strength']:
            unique_signals[symbol] = s
    
    signals = list(unique_signals.values())
    signals.sort(key=lambda x: x['signal_strength'], reverse=True)
    
    # 取前 N 只
    top_signals = signals[:CONFIG['top_n']]
    
    # 生成报告
    report = {
        'date': date or datetime.now().strftime('%Y%m%d'),
        'time': datetime.now().isoformat(),
        'total_scanned': len(set(s['symbol'] for s in signals)),
        'total_signals': len(signals),
        'top_signals': top_signals,
        'config': CONFIG
    }
    
    # 打印报告
    print("\n" + "=" * 100)
    print(f"📊 缠论 + 蜡烛图 选股报告 ({report['date']})")
    print("=" * 100)
    print(f"\n{'排名':<6} {'代码':<10} {'名称':<15} {'价格':<10} {'形态':<12} {'强度':<8} {'量比':<8} {'涨幅%':<10}")
    print("-" * 100)
    
    # 获取股票名称（简化版，实际可从文件读取）
    for i, s in enumerate(top_signals, 1):
        print(f"{i:<6} {s['symbol']:<10} {'--':<15} {s['price']:<10.2f} {s['pattern']:<12} {s['signal_strength']:<8.2f} {s['volume_ratio']:<8.2f} {s['change_pct']:<10.2f}")
    
    print("=" * 100)
    
    # 保存报告
    report_file = OUTPUT_DIR / f'selection_{report["date"]}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 保存文本格式
    text_file = OUTPUT_DIR / f'selection_{report["date"]}.txt'
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(f"缠论 + 蜡烛图 选股报告 ({report['date']})\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"{'排名':<6} {'代码':<10} {'形态':<12} {'强度':<8} {'量比':<8} {'涨幅%':<10}\n")
        f.write("-" * 80 + "\n")
        for i, s in enumerate(top_signals, 1):
            f.write(f"{i:<6} {s['symbol']:<10} {s['pattern']:<12} {s['signal_strength']:<8.2f} {s['volume_ratio']:<8.2f} {s['change_pct']:<10.2f}\n")
    
    print(f"\n💾 报告已保存:")
    print(f"   JSON: {report_file}")
    print(f"   TXT:  {text_file}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description='缠论 + 蜡烛图 每日选股')
    parser.add_argument('--date', type=str, help='选股日期 (YYYYMMDD)')
    parser.add_argument('--auto', action='store_true', help='自动识别最新日期')
    parser.add_argument('--top', type=int, default=30, help='输出前 N 只股票')
    parser.add_argument('--min-strength', type=float, default=0.6, help='最小信号强度')
    
    args = parser.parse_args()
    
    # 设置参数
    CONFIG['top_n'] = args.top
    CONFIG['min_signal_strength'] = args.min_strength
    
    # 确定日期
    date = None
    if args.date:
        date = args.date
    elif args.auto:
        # 找最新的数据日期
        stocks = get_stock_list()[:10]
        latest_dates = []
        for s in stocks:
            data = load_stock_data(s)
            if data:
                latest_dates.append(data[-1]['日期'])
        if latest_dates:
            date = max(latest_dates)
            print(f"自动识别最新日期：{date}")
    
    # 扫描选股
    signals = scan_all_stocks(date)
    
    # 生成报告
    report = generate_report(signals, date)
    
    return report


if __name__ == '__main__':
    main()
