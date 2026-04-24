#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOP10 股票深度技术分析

基于今日（2026-03-30）数据
"""

import json
from pathlib import Path
from datetime import datetime
import numpy as np

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
OUTPUT_DIR = Path('/home/admin/.openclaw/workspace/stocks/analysis_reports')
OUTPUT_DIR.mkdir(exist_ok=True)

# 今日日期
TODAY = '20260330'

# TOP10 股票列表（从选股报告中获取）
TOP10_STOCKS = [
    '301132', '601339', '601990', '002977', '603987',
    '300578', '301079', '600861', '300778', '603350'
]


def load_stock_data(symbol):
    """加载股票数据"""
    filepath = DATA_DIR / f'{symbol}.json'
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def calc_ma(data, period):
    """计算移动平均线"""
    if len(data) < period:
        return None
    closes = [d['收盘'] for d in data[-period:]]
    return sum(closes) / period


def calc_macd(data):
    """计算 MACD"""
    closes = [d['收盘'] for d in data]
    
    if len(closes) < 26:
        return None, None, None
    
    # EMA12
    ema12 = []
    for i, close in enumerate(closes):
        if i == 0:
            ema12.append(close)
        else:
            ema12.append(close * 2/13 + ema12[-1] * 11/13)
    
    # EMA26
    ema26 = []
    for i, close in enumerate(closes):
        if i == 0:
            ema26.append(close)
        else:
            ema26.append(close * 2/27 + ema26[-1] * 25/27)
    
    # DIF
    dif = [ema12[i] - ema26[i] for i in range(len(closes))]
    
    # DEA
    dea = []
    for i, d in enumerate(dif):
        if i == 0:
            dea.append(d)
        else:
            dea.append(d * 2/10 + dea[-1] * 8/10)
    
    # MACD 柱
    macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(closes))]
    
    return dif[-1], dea[-1], macd_bar[-1]


def calc_rsi(data, period=14):
    """计算 RSI"""
    closes = [d['收盘'] for d in data]
    
    if len(closes) < period + 1:
        return None
    
    gains = []
    losses = []
    for i in range(len(closes)-period, len(closes)):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


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
        return None
    
    patterns = []
    
    # 锤头线
    if lower > body * 2 and upper < body * 0.5:
        patterns.append('锤头线')
    
    # 射击之星
    if upper > body * 2 and lower < body * 0.5:
        patterns.append('射击之星')
    
    # 大阳线
    if body > total_range * 0.7 and c > o:
        patterns.append('大阳线')
    
    # 大阴线
    if body > total_range * 0.7 and c < o:
        patterns.append('大阴线')
    
    # 十字星
    if body < total_range * 0.1:
        patterns.append('十字星')
    
    # 看涨吞没
    if i > 0:
        prev_o = data[i-1]['开盘']
        prev_c = data[i-1]['收盘']
        
        if prev_c < prev_o and c > o and o < prev_c and c > prev_o:
            patterns.append('看涨吞没')
        
        if prev_c > prev_o and c < o and o < prev_o and c > prev_c:
            patterns.append('看跌吞没')
    
    return patterns if patterns else ['普通 K 线']


def analyze_stock(symbol):
    """深度分析单只股票"""
    data = load_stock_data(symbol)
    
    if not data or len(data) < 60:
        return None
    
    # 最新数据
    latest = data[-1]
    
    # 检查是否是今日数据
    if latest['日期'] != TODAY:
        return None
    
    # 基本信息
    analysis = {
        'symbol': symbol,
        'date': latest['日期'],
        'price': latest['收盘'],
        'change_pct': latest['涨跌幅'],
        'volume': latest['成交量'],
        'amount': latest['成交额'],
        'high': latest['最高'],
        'low': latest['最低'],
        'open': latest['开盘'],
    }
    
    # 均线系统
    ma5 = calc_ma(data, 5)
    ma10 = calc_ma(data, 10)
    ma20 = calc_ma(data, 20)
    ma60 = calc_ma(data, 60)
    
    analysis['ma5'] = round(ma5, 2) if ma5 else None
    analysis['ma10'] = round(ma10, 2) if ma10 else None
    analysis['ma20'] = round(ma20, 2) if ma20 else None
    analysis['ma60'] = round(ma60, 2) if ma60 else None
    
    # 均线排列
    if ma5 and ma10 and ma20 and ma60:
        if ma5 > ma10 > ma20 > ma60:
            analysis['ma_pattern'] = '多头排列'
        elif ma5 < ma10 < ma20 < ma60:
            analysis['ma_pattern'] = '空头排列'
        else:
            analysis['ma_pattern'] = '混乱排列'
    else:
        analysis['ma_pattern'] = '数据不足'
    
    # MACD
    dif, dea, macd_bar = calc_macd(data)
    analysis['macd_dif'] = round(dif, 3) if dif else None
    analysis['macd_dea'] = round(dea, 3) if dea else None
    analysis['macd_bar'] = round(macd_bar, 3) if macd_bar else None
    
    if dif and dea:
        if dif > dea and macd_bar > 0:
            analysis['macd_signal'] = '金叉多头'
        elif dif < dea and macd_bar < 0:
            analysis['macd_signal'] = '死叉空头'
        elif dif > dea:
            analysis['macd_signal'] = '金叉转弱'
        else:
            analysis['macd_signal'] = '死叉转弱'
    else:
        analysis['macd_signal'] = '数据不足'
    
    # RSI
    rsi = calc_rsi(data)
    analysis['rsi'] = round(rsi, 2) if rsi else None
    
    if rsi:
        if rsi > 70:
            analysis['rsi_status'] = '超买'
        elif rsi < 30:
            analysis['rsi_status'] = '超卖'
        else:
            analysis['rsi_status'] = '中性'
    else:
        analysis['rsi_status'] = '数据不足'
    
    # 分型
    top_fractals, bottom_fractals = detect_fractal(data)
    
    # 检查近期分型
    recent_days = min(10, len(data))
    recent_top = [i for i in top_fractals if i >= len(data) - recent_days]
    recent_bottom = [i for i in bottom_fractals if i >= len(data) - recent_days]
    
    analysis['recent_top_fractals'] = len(recent_top)
    analysis['recent_bottom_fractals'] = len(recent_bottom)
    
    # 蜡烛图形态
    patterns = detect_candlestick_pattern(data, len(data) - 1)
    analysis['candlestick_pattern'] = ', '.join(patterns)
    
    # 成交量分析
    if len(data) >= 5:
        avg_vol_5 = sum([data[-i]['成交量'] for i in range(1, 6)]) / 5
        avg_vol_20 = sum([data[-i]['成交量'] for i in range(1, 21)]) / 20
        analysis['vol_ratio_5'] = round(latest['成交量'] / avg_vol_5, 2) if avg_vol_5 > 0 else 1
        analysis['vol_ratio_20'] = round(latest['成交量'] / avg_vol_20, 2) if avg_vol_20 > 0 else 1
    else:
        analysis['vol_ratio_5'] = 1
        analysis['vol_ratio_20'] = 1
    
    # 价格位置
    if len(data) >= 60:
        high_60 = max([d['最高'] for d in data[-60:]])
        low_60 = min([d['最低'] for d in data[-60:]])
        if high_60 > low_60:
            analysis['price_position'] = round((latest['收盘'] - low_60) / (high_60 - low_60) * 100, 2)
        else:
            analysis['price_position'] = 50
    else:
        analysis['price_position'] = 50
    
    # 综合评分
    score = 0
    reasons = []
    
    # 均线评分
    if analysis['ma_pattern'] == '多头排列':
        score += 30
        reasons.append('均线多头')
    elif ma5 and ma20 and ma5 > ma20:
        score += 15
        reasons.append('MA5>MA20')
    
    # MACD 评分
    if analysis['macd_signal'] == '金叉多头':
        score += 25
        reasons.append('MACD 金叉')
    elif dif and dif > 0:
        score += 10
        reasons.append('DIF>0')
    
    # RSI 评分
    if analysis['rsi_status'] == '超卖':
        score += 20
        reasons.append('RSI 超卖')
    elif rsi and 40 < rsi < 60:
        score += 10
        reasons.append('RSI 中性')
    
    # 分型评分
    if recent_bottom:
        score += 15
        reasons.append('底分型')
    
    # 成交量评分
    if analysis['vol_ratio_5'] > 1.5:
        score += 10
        reasons.append('放量')
    
    # 形态评分
    if '看涨吞没' in patterns or '锤头线' in patterns:
        score += 20
        reasons.append('看涨形态')
    elif '大阳线' in patterns:
        score += 10
        reasons.append('阳线')
    
    analysis['score'] = min(100, score)
    analysis['reasons'] = reasons
    
    # 买卖建议
    if score >= 70:
        analysis['recommendation'] = '强烈买入'
    elif score >= 50:
        analysis['recommendation'] = '买入'
    elif score >= 30:
        analysis['recommendation'] = '观望'
    else:
        analysis['recommendation'] = '卖出'
    
    return analysis


def print_analysis(analyses):
    """打印分析结果"""
    print("=" * 120)
    print("TOP10 股票深度技术分析")
    print(f"分析日期：{TODAY}")
    print("=" * 120)
    
    for i, a in enumerate(analyses, 1):
        print(f"\n{'='*120}")
        print(f"📈 NO.{i} {a['symbol']} | {a['date']} | 价格：¥{a['price']:.2f} | 涨幅：{a['change_pct']:.2f}%")
        print(f"{'='*120}")
        
        # 基本信息
        print(f"\n【基本信息】")
        print(f"  开盘：¥{a['open']:.2f}  最高：¥{a['high']:.2f}  最低：¥{a['low']:.2f}  收盘：¥{a['price']:.2f}")
        print(f"  成交量：{a['volume']/10000:.1f}万手  成交额：{a['amount']/100000000:.2f}亿元")
        
        # 均线系统
        print(f"\n【均线系统】")
        ma_info = []
        if a['ma5']: ma_info.append(f"MA5:¥{a['ma5']:.2f}")
        if a['ma10']: ma_info.append(f"MA10:¥{a['ma10']:.2f}")
        if a['ma20']: ma_info.append(f"MA20:¥{a['ma20']:.2f}")
        if a['ma60']: ma_info.append(f"MA60:¥{a['ma60']:.2f}")
        print(f"  {'  '.join(ma_info)}")
        print(f"  排列：{a['ma_pattern']}")
        
        # MACD
        print(f"\n【MACD 指标】")
        if a['macd_dif']:
            print(f"  DIF:{a['macd_dif']:.3f}  DEA:{a['macd_dea']:.3f}  MACD 柱:{a['macd_bar']:.3f}")
            print(f"  信号：{a['macd_signal']}")
        
        # RSI
        print(f"\n【RSI 指标】")
        if a['rsi']:
            print(f"  RSI:{a['rsi']:.2f}  状态：{a['rsi_status']}")
        
        # 蜡烛图
        print(f"\n【蜡烛图形态】")
        print(f"  {a['candlestick_pattern']}")
        
        # 分型
        print(f"\n【缠论分型】")
        print(f"  近 10 日顶分型：{a['recent_top_fractals']}次  底分型：{a['recent_bottom_fractals']}次")
        
        # 成交量
        print(f"\n【成交量分析】")
        print(f"  5 日均量比：{a['vol_ratio_5']:.2f}  20 日均量比：{a['vol_ratio_20']:.2f}")
        
        # 价格位置
        print(f"\n【价格位置】")
        print(f"  60 日相对位置：{a['price_position']:.2f}%")
        
        # 综合评分
        print(f"\n【综合评分】⭐⭐⭐⭐⭐")
        print(f"  得分：{a['score']}/100")
        if a['reasons']:
            print(f"  加分项：{', '.join(a['reasons'])}")
        print(f"  建议：{a['recommendation']}")
    
    print(f"\n{'='*120}")
    print("📊 综合排名")
    print(f"{'='*120}")
    print(f"{'排名':<6} {'代码':<10} {'价格':<10} {'涨幅%':<10} {'得分':<10} {'建议':<15}")
    print("-" * 120)
    
    sorted_analyses = sorted(analyses, key=lambda x: x['score'], reverse=True)
    for i, a in enumerate(sorted_analyses, 1):
        print(f"{i:<6} {a['symbol']:<10} {a['price']:<10.2f} {a['change_pct']:<10.2f} {a['score']:<10} {a['recommendation']:<15}")
    
    print("=" * 120)


def main():
    print(f"\n分析 TOP10 股票...")
    print(f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    analyses = []
    for symbol in TOP10_STOCKS:
        print(f"分析 {symbol}...", end=" ")
        result = analyze_stock(symbol)
        if result:
            analyses.append(result)
            print("✅")
        else:
            print("❌ 无数据")
    
    print()
    
    if not analyses:
        print("❌ 没有股票数据可供分析")
        return
    
    # 打印分析
    print_analysis(analyses)
    
    # 保存报告
    report = {
        'time': datetime.now().isoformat(),
        'date': TODAY,
        'stocks': TOP10_STOCKS,
        'analyses': analyses
    }
    
    report_file = OUTPUT_DIR / f'top10_analysis_{TODAY}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 报告已保存：{report_file}")


if __name__ == '__main__':
    main()
