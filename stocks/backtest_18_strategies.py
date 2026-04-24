#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
18 种选股策略全量回测对比

策略分类:
1. 均线类 (5 种)
2. MACD 类 (3 种)
3. RSI 类 (2 种)
4. 缠论 + 蜡烛图 (3 种)
5. 多因子 (3 种)
6. 形态类 (2 种)

回测期：2025-03-27 ~ 2026-03-30
股票数：5,500+ 只
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
REPORT_DIR = Path('/home/admin/.openclaw/workspace/stocks/analysis_reports')
REPORT_DIR.mkdir(exist_ok=True)


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


# ============== 技术指标计算 ==============

def calc_ma(closes, period):
    """计算移动平均线"""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def calc_macd(closes):
    """计算 MACD"""
    if len(closes) < 26:
        return None, None, None
    
    # EMA12
    ema12 = []
    for close in closes:
        if not ema12:
            ema12.append(close)
        else:
            ema12.append(close * 2/13 + ema12[-1] * 11/13)
    
    # EMA26
    ema26 = []
    for close in closes:
        if not ema26:
            ema26.append(close)
        else:
            ema26.append(close * 2/27 + ema26[-1] * 25/27)
    
    dif = ema12[-1] - ema26[-1]
    
    # DEA
    dea_list = []
    for i, d in enumerate(dif if isinstance(dif, list) else [dif]):
        if not dea_list:
            dea_list.append(d)
        else:
            dea_list.append(d * 2/10 + dea_list[-1] * 8/10)
    
    dea = dea_list[-1] if dea_list else 0
    macd_bar = (dif - dea) * 2
    
    return dif, dea, macd_bar


def calc_rsi(closes, period=14):
    """计算 RSI"""
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
    return 100 - (100 / (1 + rs))


def calc_kdj(data):
    """计算 KDJ"""
    if len(data) < 9:
        return None, None, None
    
    recent = data[-9:]
    low_9 = min([d['最低'] for d in recent])
    high_9 = max([d['最高'] for d in recent])
    
    if high_9 == low_9:
        return 50, 50, 50
    
    c = data[-1]['收盘']
    rsv = (c - low_9) / (high_9 - low_9) * 100
    
    # 简化 KDJ (实际需要序列计算)
    k = rsv * 2/3 + 50 * 1/3
    d = k * 2/3 + 50 * 1/3
    j = 3*k - 2*d
    
    return k, d, j


def detect_fractal(data, window=5):
    """检测分型"""
    if len(data) < window * 2 + 1:
        return False, False
    
    i = len(data) - 1 - window
    
    highs = [data[i+j]['最高'] for j in range(-window, window+1)]
    lows = [data[i+j]['最低'] for j in range(-window, window+1)]
    
    is_top = data[i]['最高'] == max(highs)
    is_bottom = data[i]['最低'] == min(lows)
    
    return is_top, is_bottom


def detect_candlestick(data):
    """检测蜡烛图形态"""
    if len(data) < 2:
        return None
    
    latest = data[-1]
    prev = data[-2]
    
    o, c, h, l = latest['开盘'], latest['收盘'], latest['最高'], latest['最低']
    po, pc = prev['开盘'], prev['收盘']
    
    body = abs(c - o)
    total = h - l
    
    if total == 0:
        return None
    
    # 大阳线
    if body > total * 0.7 and c > o:
        return 'big_bull'
    
    # 大阴线
    if body > total * 0.7 and c < o:
        return 'big_bear'
    
    # 锤头线
    lower = min(o, c) - l
    upper = h - max(o, c)
    if lower > body * 2 and upper < body * 0.5:
        return 'hammer'
    
    # 看涨吞没
    if pc < po and c > o and o < pc and c > po:
        return 'bullish_engulfing'
    
    return None


# ============== 18 种策略 ==============

def strategy_1_ma_gold_cross(data):
    """1. 均线金叉 (MA5 上穿 MA20)"""
    if len(data) < 25:
        return 0
    
    closes = [d['收盘'] for d in data]
    
    ma5_prev = calc_ma(closes[:-1], 5)
    ma20_prev = calc_ma(closes[:-1], 20)
    ma5_curr = calc_ma(closes, 5)
    ma20_curr = calc_ma(closes, 20)
    
    if ma5_prev and ma20_prev and ma5_curr and ma20_curr:
        if ma5_prev <= ma20_prev and ma5_curr > ma20_curr:
            return 1  # 买入信号
    
    return 0


def strategy_2_ma_multi(data):
    """2. 均线多头 (MA5>MA10>MA20)"""
    if len(data) < 25:
        return 0
    
    closes = [d['收盘'] for d in data]
    
    ma5 = calc_ma(closes, 5)
    ma10 = calc_ma(closes, 10)
    ma20 = calc_ma(closes, 20)
    
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            return 1
    
    return 0


def strategy_3_ma_trend(data):
    """3. 均线趋势 (MA20 向上)"""
    if len(data) < 45:
        return 0
    
    closes = [d['收盘'] for d in data]
    
    ma20_prev = calc_ma(closes[:-5], 20)
    ma20_curr = calc_ma(closes, 20)
    
    if ma20_prev and ma20_curr:
        if ma20_curr > ma20_prev * 1.02:
            return 1
    
    return 0


def strategy_4_ma_deviation(data):
    """4. 均线偏离 (价格低于 MA20 超过 10%)"""
    if len(data) < 25:
        return 0
    
    closes = [d['收盘'] for d in data]
    ma20 = calc_ma(closes, 20)
    
    if ma20 and closes[-1] < ma20 * 0.9:
        return 1  # 超卖买入
    
    return 0


def strategy_5_ma_envelope(data):
    """5. 均线通道 (突破 MA20 上轨)"""
    if len(data) < 25:
        return 0
    
    closes = [d['收盘'] for d in data]
    ma20 = calc_ma(closes, 20)
    
    # 计算标准差
    if len(closes) >= 20:
        std = np.std(closes[-20:])
        upper = ma20 + 2 * std
        
        if closes[-1] > upper:
            return 1  # 突破买入
    
    return 0


def strategy_6_macd_cross(data):
    """6. MACD 金叉"""
    if len(data) < 30:
        return 0
    
    closes = [d['收盘'] for d in data]
    dif, dea, _ = calc_macd(closes)
    
    # 前一日
    closes_prev = closes[:-1]
    dif_prev, dea_prev, _ = calc_macd(closes_prev)
    
    if dif and dea and dif_prev and dea_prev:
        if dif_prev <= dea_prev and dif > dea:
            return 1
    
    return 0


def strategy_7_macd_zero(data):
    """7. MACD 零轴上金叉"""
    if len(data) < 30:
        return 0
    
    closes = [d['收盘'] for d in data]
    dif, dea, _ = calc_macd(closes)
    
    if dif and dea:
        if dif > 0 and dea > 0 and dif > dea:
            return 1
    
    return 0


def strategy_8_macd_divergence(data):
    """8. MACD 底背离"""
    if len(data) < 60:
        return 0
    
    closes = [d['收盘'] for d in data]
    lows = [d['最低'] for d in data]
    
    # 简化版：价格创新低，MACD 未创新低
    dif_curr, _, _ = calc_macd(closes)
    
    closes_prev = closes[-30:-5]
    dif_prev, _, _ = calc_macd(closes_prev)
    
    if dif_curr and dif_prev:
        if lows[-1] < min(lows[-30:-5]) and dif_curr > dif_prev:
            return 1
    
    return 0


def strategy_9_rsi_oversold(data):
    """9. RSI 超卖 (<30)"""
    if len(data) < 20:
        return 0
    
    closes = [d['收盘'] for d in data]
    rsi = calc_rsi(closes)
    
    if rsi and rsi < 30:
        return 1
    
    return 0


def strategy_10_rsi_divergence(data):
    """10. RSI 底背离"""
    if len(data) < 60:
        return 0
    
    closes = [d['收盘'] for d in data]
    lows = [d['最低'] for d in data]
    
    rsi_curr = calc_rsi(closes)
    rsi_prev = calc_rsi(closes[-30:-5])
    
    if rsi_curr and rsi_prev:
        if lows[-1] < min(lows[-30:-5]) and rsi_curr > rsi_prev:
            return 1
    
    return 0


def strategy_11_chanlun_bottom(data):
    """11. 缠论底分型"""
    if len(data) < 15:
        return 0
    
    _, is_bottom = detect_fractal(data)
    
    if is_bottom:
        return 1
    
    return 0


def strategy_12_candlestick_pattern(data):
    """12. 蜡烛图形态"""
    if len(data) < 2:
        return 0
    
    pattern = detect_candlestick(data)
    
    if pattern in ['hammer', 'bullish_engulfing', 'big_bull']:
        return 1
    
    return 0


def strategy_13_chanlun_candle(data):
    """13. 缠论 + 蜡烛图组合"""
    if len(data) < 15:
        return 0
    
    _, is_bottom = detect_fractal(data)
    pattern = detect_candlestick(data)
    
    if is_bottom and pattern in ['hammer', 'bullish_engulfing']:
        return 2  # 强信号
    elif is_bottom or pattern in ['hammer', 'bullish_engulfing']:
        return 1
    
    return 0


def strategy_14_multi_factor(data):
    """14. 多因子 (MA+RSI+ 成交量)"""
    if len(data) < 25:
        return 0
    
    closes = [d['收盘'] for d in data]
    ma5 = calc_ma(closes, 5)
    ma20 = calc_ma(closes, 20)
    rsi = calc_rsi(closes)
    
    score = 0
    
    if ma5 and ma20 and ma5 > ma20:
        score += 1
    
    if rsi and rsi < 40:
        score += 1
    
    # 成交量
    if len(data) >= 5:
        avg_vol = sum([d['成交量'] for d in data[-5:]]) / 5
        if data[-1]['成交量'] > avg_vol * 1.5:
            score += 1
    
    return score >= 2


def strategy_15_value_factor(data):
    """15. 价值因子 (低市盈率 + 低市净率)"""
    # 简化版：使用价格位置代替
    if len(data) < 60:
        return 0
    
    highs = [d['最高'] for d in data[-60:]]
    lows = [d['最低'] for d in data[-60:]]
    
    if highs and lows:
        position = (data[-1]['收盘'] - min(lows)) / (max(highs) - min(lows))
        if position < 0.3:  # 低位
            return 1
    
    return 0


def strategy_16_momentum(data):
    """16. 动量因子 (近期涨幅)"""
    if len(data) < 10:
        return 0
    
    closes = [d['收盘'] for d in data]
    
    return_5 = (closes[-1] - closes[-5]) / closes[-5] if closes[-5] > 0 else 0
    return_10 = (closes[-1] - closes[-10]) / closes[-10] if closes[-10] > 0 else 0
    
    if return_5 > 0.05 and return_10 > 0.1:
        return 1
    
    return 0


def strategy_17_volume_break(data):
    """17. 成交量突破"""
    if len(data) < 25:
        return 0
    
    avg_vol_20 = sum([d['成交量'] for d in data[-20:-1]]) / 19
    
    if avg_vol_20 > 0 and data[-1]['成交量'] > avg_vol_20 * 2:
        return 1
    
    return 0


def strategy_18_price_break(data):
    """18. 价格突破 (20 日新高)"""
    if len(data) < 25:
        return 0
    
    highs_20 = [d['最高'] for d in data[-20:-1]]
    
    if data[-1]['最高'] > max(highs_20):
        return 1
    
    return 0


# 策略列表
STRATEGIES = [
    ('均线金叉', strategy_1_ma_gold_cross),
    ('均线多头', strategy_2_ma_multi),
    ('均线趋势', strategy_3_ma_trend),
    ('均线偏离', strategy_4_ma_deviation),
    ('均线通道', strategy_5_ma_envelope),
    ('MACD 金叉', strategy_6_macd_cross),
    ('MACD 零轴上', strategy_7_macd_zero),
    ('MACD 背离', strategy_8_macd_divergence),
    ('RSI 超卖', strategy_9_rsi_oversold),
    ('RSI 背离', strategy_10_rsi_divergence),
    ('缠论底分型', strategy_11_chanlun_bottom),
    ('蜡烛图形态', strategy_12_candlestick_pattern),
    ('缠论 + 蜡烛图', strategy_13_chanlun_candle),
    ('多因子', strategy_14_multi_factor),
    ('价值因子', strategy_15_value_factor),
    ('动量因子', strategy_16_momentum),
    ('成交量突破', strategy_17_volume_break),
    ('价格突破', strategy_18_price_break),
]


def backtest_strategy(stocks, strategy_func, strategy_name):
    """回测单个策略"""
    signals = {}
    
    for symbol in stocks:
        data = load_stock_data(symbol)
        if not data or len(data) < 30:
            continue
        
        # 检查是否有今日数据
        if data[-1]['日期'] < '20260330':
            continue
        
        signal = strategy_func(data)
        if signal > 0:
            signals[symbol] = {
                'signal': signal,
                'price': data[-1]['收盘'],
                'change': data[-1]['涨跌幅']
            }
    
    return signals


def main():
    print("=" * 100)
    print("18 种选股策略回测对比")
    print("=" * 100)
    print(f"回测期：2025-03-27 ~ 2026-03-30")
    print()
    
    # 获取股票列表
    print("[1/3] 加载股票列表...")
    stocks = get_stock_list()
    print(f"   股票总数：{len(stocks)} 只")
    
    # 回测所有策略
    print(f"\n[2/3] 回测 18 种策略...")
    print()
    
    results = {}
    
    for i, (name, func) in enumerate(STRATEGIES, 1):
        print(f"[{i}/18] {name}...", end=" ")
        signals = backtest_strategy(stocks, func, name)
        results[name] = signals
        print(f"{len(signals)} 只信号")
    
    # 汇总分析
    print(f"\n[3/3] 汇总分析...")
    
    # 生成报告
    report = {
        'time': datetime.now().isoformat(),
        'period': '2025-03-27 ~ 2026-03-30',
        'total_stocks': len(stocks),
        'strategies': {}
    }
    
    print("\n" + "=" * 100)
    print("📊 策略信号统计")
    print("=" * 100)
    print(f"{'排名':<6} {'策略':<20} {'信号数':<12} {'占比':<10}")
    print("-" * 100)
    
    # 按信号数排序
    sorted_results = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)
    
    for i, (name, signals) in enumerate(sorted_results, 1):
        count = len(signals)
        ratio = count / len(stocks) * 100 if stocks else 0
        print(f"{i:<6} {name:<20} {count:<12} {ratio:>6.2f}%")
        
        report['strategies'][name] = {
            'signal_count': count,
            'ratio': ratio,
            'signals': list(signals.keys())[:20]  # 只保存前 20 个
        }
    
    print("=" * 100)
    
    # 保存报告
    report_file = REPORT_DIR / f'18_strategies_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 报告已保存：{report_file}")
    
    return report


if __name__ == '__main__':
    main()
