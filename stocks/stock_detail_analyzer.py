#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个股详细分析脚本
分析 TOP3 股票：600103, 002080, 002647
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 配置
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")

def calculate_rsi(closes, period=14):
    """计算 RSI (Wilders 平滑法)"""
    if len(closes) < period + 1:
        return 50
    
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i-1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-delta)
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(closes):
    """计算 MACD"""
    if len(closes) < 26:
        return 0, 0, 0
    
    ema12 = pd.Series(closes).ewm(span=12).mean().values
    ema26 = pd.Series(closes).ewm(span=26).mean().values
    dif = ema12 - ema26
    dea = pd.Series(dif).ewm(span=9).mean().values
    macd = 2 * (dif - dea)
    
    return dif[-1], dea[-1], macd[-1]

def calculate_kdj(highs, lows, closes, n=9):
    """计算 KDJ"""
    if len(closes) < n:
        return 50, 50, 50
    
    k_values = []
    d_values = []
    
    for i in range(n-1, len(closes)):
        low_n = np.min(lows[i-n+1:i+1])
        high_n = np.max(highs[i-n+1:i+1])
        
        if high_n > low_n:
            rsv = (closes[i] - low_n) / (high_n - low_n) * 100
        else:
            rsv = 50
        
        if len(k_values) == 0:
            k = rsv
        else:
            k = (2/3) * k_values[-1] + (1/3) * rsv
        
        if len(d_values) == 0:
            d = k
        else:
            d = (2/3) * d_values[-1] + (1/3) * k
        
        k_values.append(k)
        d_values.append(d)
    
    j = 3 * k_values[-1] - 2 * d_values[-1]
    return k_values[-1], d_values[-1], j

def calculate_bollinger(closes, period=20):
    """计算布林带"""
    if len(closes) < period:
        return 0, 0, 0
    
    ma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    upper = ma + 2 * std
    lower = ma - 2 * std
    
    pos = (closes[-1] - lower) / (upper - lower) if upper > lower else 0.5
    return upper, lower, pos

def analyze_stock(code):
    """详细分析单只股票"""
    print(f"\n{'='*80}")
    print(f"📊 {code} 详细分析")
    print(f"{'='*80}")
    
    data_path = HISTORY_DIR / f"{code}.json"
    if not data_path.exists():
        print(f"❌ 数据文件不存在：{data_path}")
        return None
    
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    if not data.get('items'):
        print("❌ 无数据")
        return None
    
    df = pd.DataFrame(data['items'], columns=data['fields'])
    df = df.drop_duplicates(subset=['trade_date'], keep='last').reset_index(drop=True)
    
    # 提取数据
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    opens = df['open'].values
    volumes = df['vol'].values if 'vol' in df.columns else df['amount'].values
    trade_dates = df['trade_date'].values if 'trade_date' in df.columns else list(range(len(df)))
    
    if len(closes) < 60:
        print("❌ 数据不足")
        return None
    
    # 基本信息
    current_price = closes[-1]
    prev_close = closes[-2]
    change_pct = (current_price - prev_close) / prev_close * 100
    
    # 均线系统
    ma5 = np.mean(closes[-5:])
    ma10 = np.mean(closes[-10:])
    ma20 = np.mean(closes[-20:])
    ma60 = np.mean(closes[-60:])
    
    p_ma5 = (current_price - ma5) / ma5 * 100
    p_ma10 = (current_price - ma10) / ma10 * 100
    p_ma20 = (current_price - ma20) / ma20 * 100
    p_ma60 = (current_price - ma60) / ma60 * 100
    
    # 收益率
    ret1 = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0
    ret3 = (closes[-1] - closes[-4]) / closes[-4] * 100 if len(closes) >= 4 else 0
    ret5 = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0
    ret10 = (closes[-1] - closes[-11]) / closes[-11] * 100 if len(closes) >= 11 else 0
    ret20 = (closes[-1] - closes[-21]) / closes[-21] * 100 if len(closes) >= 21 else 0
    
    # 技术指标
    rsi = calculate_rsi(closes)
    dif, dea, macd = calculate_macd(closes)
    k, d, j = calculate_kdj(highs, lows, closes)
    boll_upper, boll_lower, boll_pos = calculate_bollinger(closes)
    
    # 成交量
    vol_ma5 = np.mean(volumes[-5:])
    vol_ma10 = np.mean(volumes[-10:])
    vol_ratio = volumes[-1] / vol_ma5 if vol_ma5 > 0 else 1
    vol_trend = "放大" if vol_ratio > 1.2 else ("萎缩" if vol_ratio < 0.8 else "平稳")
    
    # 资金流 (简化)
    money_flows = []
    for i in range(len(closes)):
        if highs[i] > lows[i]:
            price_pos = (closes[i] - lows[i]) / (highs[i] - lows[i])
        else:
            price_pos = 0.5
        flow = volumes[i] * price_pos
        money_flows.append(flow)
    
    recent_flow = np.mean(money_flows[-5:])
    avg_flow = np.mean(money_flows[-20:])
    flow_ratio = recent_flow / avg_flow if avg_flow > 0 else 1
    
    # 形态识别
    # 大阳线
    is_big_yang = (closes[-1] - opens[-1]) / opens[-1] > 0.05 if len(opens) > 0 else False
    # 连涨
    consecutive_up = sum(1 for i in range(-5, 0) if closes[i] > closes[i-1]) if len(closes) >= 5 else 0
    # 创新高
    is_new_high = current_price >= np.max(closes[-60:])
    
    # 缠论分型 (简化)
    # 顶分型
    is_top_fenxing = (highs[-2] > highs[-3] and highs[-2] > highs[-1] and 
                      highs[-2] > highs[-4] and highs[-2] > highs[-5]) if len(highs) >= 5 else False
    # 底分型
    is_bottom_fenxing = (lows[-2] < lows[-3] and lows[-2] < lows[-1] and 
                         lows[-2] < lows[-4] and lows[-2] < lows[-5]) if len(lows) >= 5 else False
    
    # 综合评分
    score = 0
    
    # 趋势评分 (0-30)
    if p_ma5 > 0 and p_ma10 > 0 and p_ma20 > 0:
        score += 30
    elif p_ma5 > 0 and p_ma10 > 0:
        score += 20
    elif p_ma5 > 0:
        score += 10
    
    # 动能评分 (0-25)
    if ret5 > 5 and ret10 > 8:
        score += 25
    elif ret5 > 3 and ret10 > 5:
        score += 15
    elif ret5 > 0:
        score += 8
    
    # 资金评分 (0-25)
    if flow_ratio > 2.0:
        score += 25
    elif flow_ratio > 1.5:
        score += 18
    elif flow_ratio > 1.2:
        score += 10
    
    # 技术评分 (0-20)
    if 50 <= rsi < 70:
        score += 10
    if macd > 0:
        score += 5
    if k > d:
        score += 5
    
    # 风险扣分
    if rsi >= 75:
        score -= 10
    if ret5 > 20:
        score -= 5  # 涨太多
    
    # 打印分析
    print(f"\n📌 基本信息")
    print(f"  代码：{code}")
    print(f"  现价：¥{current_price:.2f}")
    print(f"  今日：{change_pct:+.2f}%")
    print(f"  成交量：{volumes[-1]:,.0f} ({vol_trend} {vol_ratio:.2f}x)")
    
    print(f"\n📈 趋势分析")
    print(f"  MA5:  ¥{ma5:.2f} (股价{p_ma5:+.1f}%)")
    print(f"  MA10: ¥{ma10:.2f} (股价{p_ma10:+.1f}%)")
    print(f"  MA20: ¥{ma20:.2f} (股价{p_ma20:+.1f}%)")
    print(f"  MA60: ¥{ma60:.2f} (股价{p_ma60:+.1f}%)")
    
    ma_status = "多头排列" if p_ma5 > 0 and p_ma10 > 0 and p_ma20 > 0 else ("混乱" if p_ma5 * p_ma10 < 0 else "空头排列")
    print(f"  均线状态：{ma_status}")
    
    print(f"\n📊 收益率")
    print(f"  1 日：{ret1:+.2f}%")
    print(f"  3 日：{ret3:+.2f}%")
    print(f"  5 日：{ret5:+.2f}% ⭐")
    print(f"  10 日：{ret10:+.2f}% ⭐")
    print(f"  20 日：{ret20:+.2f}%")
    
    print(f"\n📉 技术指标")
    print(f"  RSI(14): {rsi:.1f} {'(超买⚠️)' if rsi >= 70 else ('(强势✅)' if rsi >= 50 else '(弱势)')}")
    print(f"  MACD: DIF={dif:.3f}, DEA={dea:.3f}, MACD={macd:.3f} {'(金叉✅)' if macd > 0 else '(死叉⚠️)'}")
    print(f"  KDJ: K={k:.1f}, D={d:.1f}, J={j:.1f} {'(金叉✅)' if k > d else '(死叉⚠️)'}")
    print(f"  布林带：股价在{boll_pos*100:.0f}%位置 {'(上轨压力)' if boll_pos > 0.8 else ('(中轨支撑)' if boll_pos > 0.4 else '(下轨支撑)')}")
    
    print(f"\n💰 资金流")
    print(f"  5 日平均：{recent_flow:,.0f}")
    print(f"  20 日平均：{avg_flow:,.0f}")
    print(f"  资金流比率：{flow_ratio:.2f}x {'(大幅流入✅)' if flow_ratio > 1.5 else '(小幅流入)' if flow_ratio > 1 else '(流出⚠️)'}")
    
    print(f"\n🕯️ K 线形态")
    print(f"  大阳线：{'是✅' if is_big_yang else '否'}")
    print(f"  连涨天数：{consecutive_up}天")
    print(f"  60 日新高：{'是✅' if is_new_high else '否'}")
    print(f"  顶分型：{'是⚠️' if is_top_fenxing else '否'}")
    print(f"  底分型：{'是✅' if is_bottom_fenxing else '否'}")
    
    print(f"\n🎯 综合评分：{score}/100")
    
    # 操作建议
    print(f"\n{'='*80}")
    print(f"💡 操作建议")
    print(f"{'='*80}")
    
    if score >= 80:
        rating = "⭐⭐⭐⭐⭐ 强烈买入"
        position = "30%"
        action = "立即建仓"
    elif score >= 70:
        rating = "⭐⭐⭐⭐ 买入"
        position = "20%"
        action = "逢低建仓"
    elif score >= 60:
        rating = "⭐⭐⭐ 关注"
        position = "10%"
        action = "观察等待"
    else:
        rating = "⭐⭐ 观望"
        position = "0%"
        action = "暂不操作"
    
    print(f"  评级：{rating}")
    print(f"  建议：{action}")
    print(f"  仓位：{position}")
    
    # 买卖点
    if p_ma5 > -3:
        buy_price = current_price * 0.98
        print(f"  建仓价：¥{buy_price:.2f} (回调 2%)")
    else:
        buy_price = ma5 * 1.01
        print(f"  建仓价：¥{buy_price:.2f} (站上 MA5)")
    
    stop_loss = current_price * 0.92
    take_profit1 = current_price * 1.10
    take_profit2 = current_price * 1.20
    
    print(f"  止损价：¥{stop_loss:.2f} (-8%)")
    print(f"  止盈 1：¥{take_profit1:.2f} (+10%)")
    print(f"  止盈 2：¥{take_profit2:.2f} (+20% 后回撤 5%)")
    
    # 风险提示
    risks = []
    if rsi >= 70:
        risks.append("RSI 超买，警惕回调")
    if ret5 > 15:
        risks.append("5 日涨幅过大，可能获利回吐")
    if is_top_fenxing:
        risks.append("出现顶分型，警惕反转")
    if p_ma5 < -5:
        risks.append("跌破 MA5，趋势转弱")
    if vol_ratio < 0.8:
        risks.append("成交量萎缩，动能不足")
    
    if risks:
        print(f"\n⚠️  风险提示:")
        for risk in risks:
            print(f"  • {risk}")
    else:
        print(f"\n✅ 无明显风险")
    
    print(f"{'='*80}")
    
    return {
        'code': code,
        'score': score,
        'rating': rating,
        'price': current_price,
        'rsi': rsi,
        'ret5': ret5,
        'ret10': ret10,
        'flow_ratio': flow_ratio,
        'ma_status': ma_status,
        'buy_price': buy_price,
        'stop_loss': stop_loss,
        'take_profit': take_profit1
    }

def main():
    stocks = ['600103', '002080', '002647']
    
    print("=" * 80)
    print("🔥 板块热点 + 资金流 + 主力 TOP3 详细分析")
    print("=" * 80)
    
    results = []
    for code in stocks:
        result = analyze_stock(code)
        if result:
            results.append(result)
    
    # 对比总结
    print(f"\n{'='*80}")
    print("📊 三只股票对比")
    print(f"{'='*80}")
    print(f"{'指标':<12} {'600103':<15} {'002080':<15} {'002647':<15}")
    print(f"{'-'*80}")
    
    if len(results) == 3:
        print(f"{'综合评分':<12} {results[0]['score']:<15} {results[1]['score']:<15} {results[2]['score']:<15}")
        print(f"{'评级':<12} {results[0]['rating']:<15} {results[1]['rating']:<15} {results[2]['rating']:<15}")
        print(f"{'RSI':<12} {results[0]['rsi']:<15.1f} {results[1]['rsi']:<15.1f} {results[2]['rsi']:<15.1f}")
        print(f"{'5 日收益':<12} {results[0]['ret5']:<15.1f} {results[1]['ret5']:<15.1f} {results[2]['ret5']:<15.1f}")
        print(f"{'10 日收益':<12} {results[0]['ret10']:<15.1f} {results[1]['ret10']:<15.1f} {results[2]['ret10']:<15.1f}")
        print(f"{'资金流比率':<12} {results[0]['flow_ratio']:<15.2f} {results[1]['flow_ratio']:<15.2f} {results[2]['flow_ratio']:<15.2f}")
        print(f"{'均线状态':<12} {results[0]['ma_status']:<15} {results[1]['ma_status']:<15} {results[2]['ma_status']:<15}")
    
    print(f"\n{'='*80}")
    print("🎯 最终推荐")
    print(f"{'='*80}")
    
    if results:
        best = max(results, key=lambda x: x['score'])
        print(f"  首选：{best['code']} (评分{best['score']})")
        print(f"  建仓：¥{best['buy_price']:.2f}")
        print(f"  止损：¥{best['stop_loss']:.2f}")
        print(f"  止盈：¥{best['take_profit']:.2f}")
        print(f"  仓位：30%")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()
