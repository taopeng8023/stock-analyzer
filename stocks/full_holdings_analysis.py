#!/usr/bin/env python3
"""
完整持仓分析 - 包括债券082491
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime

print("="*70)
print("完整持仓分析 (含债券)")
print("="*70)
print(datetime.now())

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")

# 完整持仓
holdings = [
    {'name': '中闽能源', 'code': '600163', 'shares': 1300, 'cost': 7.414, 'type': 'stock'},
    {'name': '蔚蓝生物', 'code': '603739', 'shares': 1100, 'cost': 16.603, 'type': 'stock'},
    {'name': '002511', 'code': '002511', 'shares': 2900, 'cost': 8.812, 'type': 'stock'},
    {'name': '082491债券', 'code': '082491', 'shares': 700, 'cost': 15.057, 'type': 'bond'},
]

total_value = 0
total_profit = 0

for h in holdings:
    print("\n" + "-"*70)
    print(f"【{h['name']}】({h['code']})")
    print("-"*70)
    
    if h['type'] == 'bond':
        # 债券分析
        print("\n📦 债券持仓:")
        print(f"  持有数量: {h['shares']}张")
        print(f"  成本价: ¥{h['cost']:.3f}")
        print(f"  总投入: ¥{h['cost'] * h['shares']:.0f}")
        
        # 债券特点
        print(f"\n💡 债券特性:")
        print(f"  • 08开头代码 = 上海债券市场")
        print(f"  • 通常为国债、地方债或企业债")
        print(f"  • 收益来源: 固定利息 + 价格波动")
        print(f"  • 建议: 持有到期获取利息收益")
        
        # 市值（按成本价）
        value = h['cost'] * h['shares']
        total_value += value
        
        print(f"\n📊 当前市值:")
        print(f"  预估市值: ¥{value:.0f}")
        print(f"  说明: 债券价格波动小，按成本估算")
        
        print(f"\n✅ 操作建议:")
        print(f"  • 持有到期")
        print(f"  • 关注债券到期日和利息")
        print(f"  • 债券用于稳定收益，降低风险")
        
        continue
    
    # 股票分析
    fp = HISTORY_DIR / f"{h['code']}.json"
    
    if not fp.exists():
        print("❌ 数据文件不存在")
        continue
    
    with open(fp) as f:
        raw = json.load(f)
    
    items = raw['items']
    
    # 解析最新数据
    data = []
    for item in items:
        if len(item) >= 11:
            data.append({
                'close': float(item[5]),
                'vol': float(item[9]),
                'high': float(item[3]),
                'low': float(item[4]),
                'date': str(item[1])
            })
    
    latest = data[-1]
    current_price = latest['close']
    
    # 计算盈亏
    cost = h['cost']
    profit_pct = (current_price - cost) / cost * 100
    profit = (current_price - cost) * h['shares']
    value = current_price * h['shares']
    
    total_value += value
    total_profit += profit
    
    print(f"\n💰 持仓信息:")
    print(f"  持股: {h['shares']}股")
    print(f"  成本: ¥{cost:.2f}")
    print(f"  现价: ¥{current_price:.2f}")
    print(f"  市值: ¥{value:.0f}")
    
    status = '✅正常'
    if profit_pct <= -15:
        status = '🔴止损'
    elif profit_pct <= -10:
        status = '⚠️警戒'
    elif profit_pct >= 10:
        status = '🟢止盈'
    
    print(f"  盈亏: {profit_pct:.2f}% (¥{profit:.0f}) {status}")
    
    # 技术指标
    closes = [d['close'] for d in data]
    volumes = [d['vol'] for d in data]
    
    # 均线
    ma5 = np.mean(closes[-5:])
    ma10 = np.mean(closes[-10:])
    ma20 = np.mean(closes[-20:])
    
    print(f"\n📊 技术分析:")
    print(f"  MA5: ¥{ma5:.2f} {'✅站上' if current_price > ma5 else '🔴跌破'}")
    print(f"  MA10: ¥{ma10:.2f} {'✅站上' if current_price > ma10 else '🔴跌破'}")
    print(f"  MA20: ¥{ma20:.2f} {'✅站上' if current_price > ma20 else '🔴跌破'}")
    
    # RSI
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains = sum(d for d in deltas[-14:] if d > 0)
    losses = sum(-d for d in deltas[-14:] if d < 0)
    rsi = 100 - 100/(1 + gains/losses) if losses > 0 else 50
    
    rsi_status = '🔴超卖' if rsi < 30 else ('🟠超买' if rsi > 70 else '✅正常')
    print(f"  RSI: {rsi:.1f} {rsi_status}")
    
    # 布林带
    std20 = np.std(closes[-20:])
    boll_pos = (current_price - ma20) / (2*std20)
    print(f"  布林位置: {boll_pos:.2f}")
    
    # 涨跌
    ret5 = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) > 5 else 0
    ret10 = (closes[-1] - closes[-11]) / closes[-11] * 100 if len(closes) > 10 else 0
    
    print(f"\n📈 近期走势:")
    print(f"  5日: {ret5:.2f}%")
    print(f"  10日: {ret10:.2f}%")
    
    # 成交量
    vol5_avg = np.mean(volumes[-5:])
    vol_ratio = volumes[-1] / vol5_avg if vol5_avg > 0 else 1
    
    print(f"\n📉 成交量:")
    print(f"  量比: {vol_ratio:.2f} {'🟢放量' if vol_ratio > 1.5 else '✅正常'}")
    
    # 综合评分
    score = 0
    
    if current_price > ma5:
        score += 10
    else:
        score -= 10
    
    if current_price > ma20:
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
    
    print(f"\n🎯 综合评分: {score}")
    
    if score >= 20:
        print(f"  建议: 🟡 持有观察")
    elif score >= -30:
        print(f"  建议: 🟠 减仓")
    else:
        print(f"  建议: 🔴 止损卖出")

print("\n" + "="*70)
print("持仓总览")
print("="*70)
print(f"\n总市值: ¥{total_value:.0f}")
print(f"总盈亏: ¥{total_profit:.0f}")
print(f"\n持仓分布:")
print(f"  股票市值: ¥{total_value - 15.057*700:.0f} ({(total_value - 15.057*700)/total_value*100:.1f}%)")
print(f"  债券市值: ¥{15.057*700:.0f} ({15.057*700/total_value*100:.1f}%)")

print("\n✅ 完成:", datetime.now())