#!/usr/bin/env python3
import json
import numpy as np
from pathlib import Path

HISTORY_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026')
fp = HISTORY_DIR / '002491.json'

print("="*70)
print("002491 股票分析")
print("="*70)

if fp.exists():
    with open(fp) as f:
        raw = json.load(f)
    
    items = raw['items']
    
    latest = items[-1]
    latest_date = str(latest[1])
    latest_close = float(latest[5])
    
    print(f"最新日期: {latest_date}")
    print(f"最新收盘: ¥{latest_close:.2f}")
    
    # 持仓信息
    shares = 700
    cost = 15.057
    
    current_value = latest_close * shares
    profit_pct = (latest_close - cost) / cost * 100
    profit = current_value - cost * shares
    
    print(f"\n持仓信息:")
    print(f"  持股: {shares}股")
    print(f"  成本: ¥{cost:.2f}")
    print(f"  现价: ¥{latest_close:.2f}")
    print(f"  市值: ¥{current_value:.0f}")
    
    status = "正常"
    if profit_pct <= -15:
        status = "止损"
    elif profit_pct <= -10:
        status = "警戒"
    elif profit_pct >= 10:
        status = "止盈"
    
    print(f"  盈亏: {profit_pct:.2f}% (¥{profit:.0f}) [{status}]")
    
    # 解析历史数据
    data = []
    for item in items:
        if len(item) >= 11:
            data.append({
                'close': float(item[5]),
                'vol': float(item[9]),
                'high': float(item[3]),
                'low': float(item[4])
            })
    
    closes = [d['close'] for d in data]
    volumes = [d['vol'] for d in data]
    
    # 均线
    ma5 = np.mean(closes[-5:])
    ma10 = np.mean(closes[-10:])
    ma20 = np.mean(closes[-20:])
    
    print(f"\n技术分析:")
    ma5_status = "站上" if latest_close > ma5 else "跌破"
    ma10_status = "站上" if latest_close > ma10 else "跌破"
    ma20_status = "站上" if latest_close > ma20 else "跌破"
    
    print(f"  MA5: ¥{ma5:.2f} [{ma5_status}]")
    print(f"  MA10: ¥{ma10:.2f} [{ma10_status}]")
    print(f"  MA20: ¥{ma20:.2f} [{ma20_status}]")
    
    # RSI
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains = sum(d for d in deltas[-14:] if d > 0)
    losses = sum(-d for d in deltas[-14:] if d < 0)
    rsi = 100 - 100/(1 + gains/losses) if losses > 0 else 50
    
    rsi_status = "超卖" if rsi < 30 else ("超买" if rsi > 70 else "正常")
    print(f"  RSI: {rsi:.1f} [{rsi_status}]")
    
    # 布林带
    std20 = np.std(closes[-20:])
    boll_pos = (latest_close - ma20) / (2*std20)
    print(f"  布林位置: {boll_pos:.2f}")
    
    # 涨跌
    ret5 = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) > 5 else 0
    ret10 = (closes[-1] - closes[-11]) / closes[-11] * 100 if len(closes) > 10 else 0
    
    print(f"\n近期走势:")
    print(f"  5日: {ret5:.2f}%")
    print(f"  10日: {ret10:.2f}%")
    
    # 成交量
    vol5_avg = np.mean(volumes[-5:])
    vol_ratio = volumes[-1] / vol5_avg if vol5_avg > 0 else 1
    
    vol_status = "放量" if vol_ratio > 1.5 else "正常"
    print(f"\n成交量:")
    print(f"  量比: {vol_ratio:.2f} [{vol_status}]")
    
    # 综合评分
    score = 0
    
    if latest_close > ma5:
        score += 10
    else:
        score -= 10
    
    if latest_close > ma20:
        score += 15
    else:
        score -= 15
    
    if rsi < 30:
        score += 20
    elif rsi > 70:
        score -= 10
    else:
        score += 5
    
    if profit_pct <= -15:
        score -= 30
    
    print(f"\n综合评分: {score}")
    
    if score >= 20:
        print(f"  建议: 持有观察")
    elif score >= -30:
        print(f"  建议: 减仓")
    else:
        print(f"  建议: 止损卖出")

else:
    print("数据文件不存在")