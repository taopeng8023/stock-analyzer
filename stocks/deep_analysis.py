#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票深度技术分析系统

对冠军股 (603301) 进行详细技术分析:
- 多维度技术指标
- 支撑/阻力位分析
- 波浪理论分析
- 买卖点建议
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest_with_cache import load_cached_data, calculate_ma


# ==================== 高级技术指标 ====================

def calculate_bollinger_bands(data: List[Dict], period: int = 20, std_dev: float = 2.0) -> Dict:
    """计算布林带"""
    closes = [d['close'] for d in data]
    
    upper, middle, lower = [], [], []
    
    for i in range(len(closes)):
        if i < period - 1:
            upper.append(None)
            middle.append(None)
            lower.append(None)
            continue
        
        window = closes[i-period+1:i+1]
        ma = sum(window) / period
        std = np.std(window)
        
        middle.append(ma)
        upper.append(ma + std_dev * std)
        lower.append(ma - std_dev * std)
    
    return {'upper': upper, 'middle': middle, 'lower': lower}


def calculate_atr(data: List[Dict], period: int = 14) -> List[float]:
    """计算平均真实波幅 (ATR)"""
    atr_values = []
    
    for i in range(len(data)):
        if i < period:
            atr_values.append(None)
            continue
        
        tr_values = []
        for j in range(i-period+1, i+1):
            high = data[j]['high']
            low = data[j]['low']
            prev_close = data[j-1]['close'] if j > 0 else data[j]['close']
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            tr_values.append(max(tr1, tr2, tr3))
        
        atr = sum(tr_values) / period
        atr_values.append(atr)
    
    return atr_values


def calculate_obv(data: List[Dict]) -> List[float]:
    """计算能量潮 (OBV)"""
    obv_values = [0]
    
    for i in range(1, len(data)):
        if data[i]['close'] > data[i-1]['close']:
            obv = obv_values[-1] + data[i]['volume']
        elif data[i]['close'] < data[i-1]['close']:
            obv = obv_values[-1] - data[i]['volume']
        else:
            obv = obv_values[-1]
        
        obv_values.append(obv)
    
    return obv_values


def calculate_support_resistance(data: List[Dict], lookback: int = 30) -> Dict:
    """计算支撑位和阻力位"""
    highs = [d['high'] for d in data[-lookback:]]
    lows = [d['low'] for d in data[-lookback:]]
    
    # 近期高低点
    recent_high = max(highs)
    recent_low = min(lows)
    
    # 计算斐波那契回撤位
    high_idx = highs.index(recent_high)
    low_idx = lows.index(recent_low)
    
    if recent_high > recent_low:
        diff = recent_high - recent_low
        fib_levels = {
            '0%': recent_low,
            '23.6%': recent_low + diff * 0.236,
            '38.2%': recent_low + diff * 0.382,
            '50%': recent_low + diff * 0.5,
            '61.8%': recent_low + diff * 0.618,
            '78.6%': recent_low + diff * 0.786,
            '100%': recent_high
        }
    else:
        fib_levels = {}
    
    return {
        'resistance': recent_high,
        'support': recent_low,
        'fib_levels': fib_levels
    }


def analyze_wave_pattern(data: List[Dict]) -> Dict:
    """简化波浪理论分析"""
    closes = [d['close'] for d in data[-100:]]
    
    # 寻找局部高低点
    peaks = []
    troughs = []
    
    for i in range(2, len(closes)-2):
        if closes[i] > closes[i-1] and closes[i] > closes[i+1] and \
           closes[i] > closes[i-2] and closes[i] > closes[i+2]:
            peaks.append((i, closes[i]))
        
        if closes[i] < closes[i-1] and closes[i] < closes[i+1] and \
           closes[i] < closes[i-2] and closes[i] < closes[i+2]:
            troughs.append((i, closes[i]))
    
    # 判断当前波浪位置
    current_price = closes[-1]
    
    if peaks and troughs:
        last_peak = peaks[-1]
        last_trough = troughs[-1]
        
        if current_price > last_peak[1]:
            wave = '可能处于第 5 浪或 C 浪'
            trend = '上升'
        elif current_price < last_trough[1]:
            wave = '可能处于第 3 浪或 A 浪'
            trend = '下降'
        elif current_price > (last_peak[1] + last_trough[1]) / 2:
            wave = '可能处于第 4 浪或 B 浪'
            trend = '调整'
        else:
            wave = '可能处于第 2 浪或 A 浪'
            trend = '调整'
    else:
        wave = '数据不足'
        trend = '不明'
    
    return {
        'current_wave': wave,
        'trend': trend,
        'peaks_count': len(peaks),
        'troughs_count': len(troughs)
    }


# ==================== 综合技术分析 ====================

def technical_analysis(data: List[Dict], code: str) -> Dict:
    """
    综合技术分析
    
    Returns:
        分析报告字典
    """
    analysis = {
        'code': code,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'price': data[-1]['close'],
        'indicators': {},
        'signals': [],
        'recommendation': {}
    }
    
    # === 趋势指标 ===
    closes = [d['close'] for d in data]
    
    # 均线系统
    ma5 = calculate_ma(closes, 5)[-1]
    ma10 = calculate_ma(closes, 10)[-1]
    ma20 = calculate_ma(closes, 20)[-1]
    ma60 = calculate_ma(closes, 60)[-1] if len(closes) >= 60 else None
    
    analysis['indicators']['moving_averages'] = {
        'MA5': round(ma5, 2),
        'MA10': round(ma10, 2),
        'MA20': round(ma20, 2),
        'MA60': round(ma60, 2) if ma60 else None
    }
    
    # 均线排列判断
    if ma5 > ma10 > ma20 > ma60:
        analysis['signals'].append('✅ 多头排列 - 强势上涨')
        trend_score = 10
    elif ma5 < ma10 < ma20 < ma60:
        analysis['signals'].append('❌ 空头排列 - 弱势下跌')
        trend_score = -10
    elif ma5 > ma20 and ma10 > ma20:
        analysis['signals'].append('⚠️ 短期偏强')
        trend_score = 5
    else:
        analysis['signals'].append('⚠️ 震荡整理')
        trend_score = 0
    
    # === 动量指标 ===
    # RSI
    rsi = calculate_rsi(closes)[-1]
    analysis['indicators']['RSI'] = round(rsi, 2)
    
    if rsi > 70:
        analysis['signals'].append('⚠️ RSI 超买 (>70)')
    elif rsi < 30:
        analysis['signals'].append('✅ RSI 超卖 (<30)')
    else:
        analysis['signals'].append(f'➖ RSI 中性 ({rsi:.1f})')
    
    # MACD
    macd = calculate_macd(closes)
    dif = macd['dif'][-1]
    dea = macd['dea'][-1]
    macd_bar = macd['macd'][-1]
    
    analysis['indicators']['MACD'] = {
        'DIF': round(dif, 4),
        'DEA': round(dea, 4),
        'MACD': round(macd_bar, 4)
    }
    
    if dif > dea and macd_bar > 0:
        analysis['signals'].append('✅ MACD 金叉 - 买入信号')
        momentum_score = 5
    elif dif < dea and macd_bar < 0:
        analysis['signals'].append('❌ MACD 死叉 - 卖出信号')
        momentum_score = -5
    else:
        analysis['signals'].append('➖ MACD 震荡')
        momentum_score = 0
    
    # === 波动指标 ===
    # 布林带
    bb = calculate_bollinger_bands(data)
    current_price = data[-1]['close']
    upper = bb['upper'][-1]
    middle = bb['middle'][-1]
    lower = bb['lower'][-1]
    
    analysis['indicators']['Bollinger'] = {
        'Upper': round(upper, 2),
        'Middle': round(middle, 2),
        'Lower': round(lower, 2)
    }
    
    if current_price > upper:
        analysis['signals'].append('⚠️ 股价突破上轨 - 可能超买')
    elif current_price < lower:
        analysis['signals'].append('✅ 股价跌破下轨 - 可能超卖')
    else:
        analysis['signals'].append('➖ 股价在布林带内')
    
    # ATR
    atr = calculate_atr(data)[-1]
    analysis['indicators']['ATR'] = round(atr, 4)
    
    # === 成交量指标 ===
    # OBV
    obv = calculate_obv(data)
    obv_recent = sum(obv[-10:]) / 10
    obv_prev = sum(obv[-20:-10]) / 10
    
    if obv_recent > obv_prev * 1.1:
        analysis['signals'].append('✅ OBV 上升 - 资金流入')
    elif obv_recent < obv_prev * 0.9:
        analysis['signals'].append('❌ OBV 下降 - 资金流出')
    else:
        analysis['signals'].append('➖ OBV 平稳')
    
    # === 支撑阻力 ===
    sr = calculate_support_resistance(data)
    analysis['indicators']['Support_Resistance'] = {
        'Resistance': round(sr['resistance'], 2),
        'Support': round(sr['support'], 2),
        'Fib_Levels': {k: round(v, 2) for k, v in sr['fib_levels'].items()}
    }
    
    # === 波浪分析 ===
    wave = analyze_wave_pattern(data)
    analysis['indicators']['Wave_Analysis'] = wave
    
    # === 综合建议 ===
    total_score = trend_score + momentum_score
    
    # 计算仓位建议
    if total_score >= 10:
        position = '80-100%'
        action = '强烈买入'
    elif total_score >= 5:
        position = '60-80%'
        action = '买入'
    elif total_score >= 0:
        position = '30-50%'
        action = '持有'
    elif total_score >= -5:
        position = '10-30%'
        action = '减仓'
    else:
        position = '0%'
        action = '卖出/观望'
    
    analysis['recommendation'] = {
        'action': action,
        'position': position,
        'score': total_score,
        'stop_loss': round(current_price * 0.94, 2),  # 6% 止损
        'take_profit_1': round(current_price * 1.08, 2),  # 8% 止盈
        'take_profit_2': round(current_price * 1.15, 2)  # 15% 止盈
    }
    
    return analysis


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """计算 RSI"""
    rsi_values = []
    
    for i in range(len(prices)):
        if i < period:
            rsi_values.append(None)
            continue
        
        gains, losses = [], []
        for j in range(i-period+1, i+1):
            change = prices[j] - prices[j-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi_values.append(rsi)
    
    return rsi_values


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    """计算 MACD"""
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    dif = []
    for i in range(len(prices)):
        if ema_fast[i] is None or ema_slow[i] is None:
            dif.append(None)
        else:
            dif.append(ema_fast[i] - ema_slow[i])
    
    dif_valid = [d for d in dif if d is not None]
    dea_raw = calculate_ema(dif_valid, signal) if dif_valid else []
    
    dea = []
    dea_idx = 0
    for i in range(len(prices)):
        if dif[i] is None:
            dea.append(None)
        elif dea_idx < len(dea_raw):
            dea.append(dea_raw[dea_idx])
            dea_idx += 1
        else:
            dea.append(None)
    
    macd_bar = []
    for i in range(len(prices)):
        if dif[i] is None or dea[i] is None:
            macd_bar.append(None)
        else:
            macd_bar.append(2 * (dif[i] - dea[i]))
    
    return {'dif': dif, 'dea': dea, 'macd': macd_bar}


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """计算 EMA"""
    if len(prices) < period:
        return [None] * len(prices)
    
    multiplier = 2 / (period + 1)
    sma = sum(prices[:period]) / period
    result = [sma]
    
    for i in range(1, len(prices)):
        ema = (prices[i] - result[-1]) * multiplier + result[-1]
        result.append(ema)
    
    return [None] * (period - 1) + result


# ==================== 报告生成 ====================

def print_analysis_report(analysis: Dict):
    """打印分析报告"""
    print("\n" + "="*80)
    print(f"📊 {analysis['code']} 深度技术分析报告".center(80))
    print("="*80)
    
    print(f"\n📅 分析日期：{analysis['date']}")
    print(f"💰 当前价格：¥{analysis['price']:.2f}")
    
    # 趋势指标
    print("\n" + "-"*80)
    print("📈 趋势指标")
    print("-"*80)
    ma = analysis['indicators']['moving_averages']
    print(f"  MA5:  ¥{ma['MA5']:.2f}")
    print(f"  MA10: ¥{ma['MA10']:.2f}")
    print(f"  MA20: ¥{ma['MA20']:.2f}")
    print(f"  MA60: ¥{ma['MA60']:.2f}" if ma['MA60'] else "  MA60: 数据不足")
    
    # 动量指标
    print("\n" + "-"*80)
    print("⚡ 动量指标")
    print("-"*80)
    print(f"  RSI:  {analysis['indicators']['RSI']:.2f}")
    macd = analysis['indicators']['MACD']
    print(f"  MACD: DIF={macd['DIF']:.4f}, DEA={macd['DEA']:.4f}, MACD={macd['MACD']:.4f}")
    
    # 波动指标
    print("\n" + "-"*80)
    print("📊 波动指标")
    print("-"*80)
    bb = analysis['indicators']['Bollinger']
    print(f"  布林带：上轨¥{bb['Upper']:.2f}, 中轨¥{bb['Middle']:.2f}, 下轨¥{bb['Lower']:.2f}")
    print(f"  ATR:    {analysis['indicators']['ATR']:.4f}")
    
    # 支撑阻力
    print("\n" + "-"*80)
    print("🎯 支撑与阻力")
    print("-"*80)
    sr = analysis['indicators']['Support_Resistance']
    print(f"  阻力位：¥{sr['Resistance']:.2f}")
    print(f"  支撑位：¥{sr['Support']:.2f}")
    print("  斐波那契回撤位:")
    for level, price in sr['Fib_Levels'].items():
        print(f"    {level}: ¥{price:.2f}")
    
    # 波浪分析
    print("\n" + "-"*80)
    print("🌊 波浪理论分析")
    print("-"*80)
    wave = analysis['indicators']['Wave_Analysis']
    print(f"  当前波浪：{wave['current_wave']}")
    print(f"  趋势：{wave['trend']}")
    
    # 交易信号
    print("\n" + "-"*80)
    print("📡 交易信号")
    print("-"*80)
    for signal in analysis['signals']:
        print(f"  {signal}")
    
    # 综合建议
    print("\n" + "="*80)
    print("💡 综合建议")
    print("="*80)
    rec = analysis['recommendation']
    print(f"  操作建议：{rec['action']}")
    print(f"  建议仓位：{rec['position']}")
    print(f"  综合得分：{rec['score']}")
    print(f"  止损位：  ¥{rec['stop_loss']:.2f} (-6%)")
    print(f"  止盈 1：   ¥{rec['take_profit_1']:.2f} (+8%)")
    print(f"  止盈 2：   ¥{rec['take_profit_2']:.2f} (+15%)")
    print("="*80 + "\n")


def save_analysis(analysis: Dict, output_dir: str = None):
    """保存分析报告"""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), 'analysis_reports')
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.join(output_dir, f"analysis_{analysis['code']}_{timestamp}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"📁 报告已保存：{filepath}")


# ==================== 主程序 ====================

def main():
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description='股票深度技术分析')
    parser.add_argument('--code', type=str, default='603301', help='股票代码 (默认 603301)')
    parser.add_argument('--days', type=int, default=250, help='分析天数 (默认 250)')
    parser.add_argument('--save', action='store_true', help='保存报告到文件')
    
    args = parser.parse_args()
    
    print("="*80)
    print("🚀 股票深度技术分析系统".center(80))
    print("="*80)
    print(f"作者：凯文")
    print("="*80 + "\n")
    
    # 加载数据
    data = load_cached_data(args.code)
    
    if not data or len(data) < args.days:
        print(f"❌ 数据不足，需要至少 {args.days} 条，实际 {len(data) if data else 0} 条")
        return
    
    # 截取数据
    data = data[-args.days:]
    
    # 技术分析
    analysis = technical_analysis(data, args.code)
    
    # 打印报告
    print_analysis_report(analysis)
    
    # 保存报告
    if args.save:
        save_analysis(analysis)


if __name__ == '__main__':
    main()
