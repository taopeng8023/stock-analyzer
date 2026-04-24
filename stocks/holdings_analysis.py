#!/usr/bin/env python3
"""
持仓股分析 - 技术指标 + 资金流
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime

print("="*70)
print("持仓股深度分析")
print("="*70)
print(datetime.now())

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
DATA_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data")

# 持仓信息
holdings = [
    {'name': '中闽能源', 'code': '600163', 'shares': 1300, 'cost': 7.414},
    {'name': '蔚蓝生物', 'code': '603739', 'shares': 1100, 'cost': 16.603},
    {'name': '002511', 'code': '002511', 'shares': 2900, 'cost': 8.812},
]

# 加载资金流数据
zjlx_file = DATA_DIR / "zjlx_ranking_20260415.json"
zjlx_data = {}
if zjlx_file.exists():
    with open(zjlx_file) as f:
        raw = json.load(f)
    items = raw if isinstance(raw, list) else raw.get('data', [])
    for item in items:
        code = item.get('代码', item.get('code', ''))
        zjlx_data[code] = item

def calc_rsi(closes, period=14):
    """计算RSI"""
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains = sum(d for d in deltas[-period:] if d > 0)
    losses = sum(-d for d in deltas[-period:] if d < 0)
    return 100 - 100/(1 + gains/losses) if losses > 0 else 50

def calc_macd(closes):
    """计算MACD"""
    ema12 = closes[-1]
    ema26 = closes[-1]
    
    # 简化计算
    for i, c in enumerate(closes[-26:]):
        if i < 12:
            ema12 = c * 0.154 + ema12 * 0.846
        ema26 = c * 0.074 + ema26 * 0.926
    
    dif = ema12 - ema26
    dea = dif * 0.2 + dea * 0.8 if 'dea' in dir() else dif
    macd = 2 * (dif - dea)
    
    return dif, dea, macd

for h in holdings:
    print("\n" + "="*70)
    print(f"{h['name']} ({h['code']})")
    print("="*70)
    
    fp = HISTORY_DIR / f"{h['code']}.json"
    
    if not fp.exists():
        print("数据文件不存在")
        continue
    
    with open(fp) as f:
        raw = json.load(f)
    
    items = raw['items']
    fields = raw['fields']
    
    # 解析数据
    data = []
    for item in items:
        d = dict(zip(fields, item))
        c = float(d.get('close', 0))
        if c > 0:
            data.append({
                'close': c,
                'vol': float(d.get('vol', 0)),
                'high': float(d.get('high', c)),
                'low': float(d.get('low', c)),
                'date': str(d.get('trade_date', ''))
            })
    
    if len(data) < 30:
        print("数据不足")
        continue
    
    # 最新数据
    latest = data[-1]
    closes = [d['close'] for d in data]
    volumes = [d['vol'] for d in data]
    
    current_price = latest['close']
    cost = h['cost']
    profit_pct = (current_price - cost) / cost * 100
    profit = (current_price - cost) * h['shares']
    
    print(f"\n💰 持仓信息:")
    print(f"  持股数量: {h['shares']}股")
    print(f"  成本价: ¥{cost:.2f}")
    print(f"  当前价: ¥{current_price:.2f}")
    print(f"  盈亏: {profit_pct:.2f}% (¥{profit:.0f})")
    
    # 技术指标
    print(f"\n📊 技术分析:")
    
    # 均线
    ma5 = np.mean(closes[-5:])
    ma10 = np.mean(closes[-10:])
    ma20 = np.mean(closes[-20:])
    
    print(f"  MA5: ¥{ma5:.2f} {'✅站上' if current_price > ma5 else '🔴跌破'}")
    print(f"  MA10: ¥{ma10:.2f} {'✅站上' if current_price > ma10 else '🔴跌破'}")
    print(f"  MA20: ¥{ma20:.2f} {'✅站上' if current_price > ma20 else '🔴跌破'}")
    
    # RSI
    rsi = calc_rsi(closes)
    rsi_status = '🔴超卖' if rsi < 30 else ('🟠超买' if rsi > 70 else '✅正常')
    print(f"  RSI(14): {rsi:.1f} {rsi_status}")
    
    # MACD
    try:
        dif, dea, macd = calc_macd(closes)
        macd_status = '🟢金叉' if dif > dea else '🔴死叉'
        print(f"  MACD: DIF={dif:.2f} DEA={dea:.2f} {macd_status}")
    except:
        print(f"  MACD: 计算中...")
    
    # 布林带
    std20 = np.std(closes[-20:])
    upper = ma20 + 2*std20
    lower = ma20 - 2*std20
    boll_pos = (current_price - ma20) / (2*std20)
    
    print(f"  布林带: 上轨¥{upper:.2f} 下轨¥{lower:.2f}")
    print(f"  当前位置: {boll_pos:.2f} {'🔴超买区' if boll_pos > 1 else ('🟢超卖区' if boll_pos < -1 else '✅正常')}")
    
    # 近期走势
    print(f"\n📈 近期走势:")
    
    # 5日涨跌
    ret5 = (closes[-1] - closes[-6]) / closes[-6] * 100
    ret10 = (closes[-1] - closes[-11]) / closes[-11] * 100
    ret20 = (closes[-1] - closes[-21]) / closes[-21] * 100
    
    print(f"  5日涨跌: {ret5:.2f}%")
    print(f"  10日涨跌: {ret10:.2f}%")
    print(f"  20日涨跌: {ret20:.2f}%")
    
    # 成交量
    vol5_avg = np.mean(volumes[-5:])
    vol20_avg = np.mean(volumes[-20:])
    vol_ratio = volumes[-1] / vol5_avg if vol5_avg > 0 else 1
    
    print(f"\n📉 成交量:")
    print(f"  今日成交量: {volumes[-1]:.0f}")
    print(f"  5日平均: {vol5_avg:.0f}")
    print(f"  量比: {vol_ratio:.2f} {'🟢放量' if vol_ratio > 1.5 else ('🔴缩量' if vol_ratio < 0.5 else '✅正常')}")
    
    # 资金流
    print(f"\n💵 资金流向:")
    
    if h['code'] in zjlx_data:
        zjlx = zjlx_data[h['code']]
        flow = zjlx.get('主力净流入', 0)
        rank = zjlx.get('排行', 0)
        pct = zjlx.get('主力占比', 0)
        
        if isinstance(flow, str):
            flow = float(flow.replace('亿', '').replace('万', ''))
        
        flow_status = '🟢流入' if flow > 0 else '🔴流出'
        print(f"  主力净流入: {flow:.2f}亿 {flow_status}")
        print(f"  主力占比: {pct:.2f}%")
        print(f"  排行: #{rank}")
    else:
        print(f"  未在资金流TOP50")
    
    # 综合评分
    print(f"\n🎯 综合评分:")
    
    score = 0
    reasons = []
    
    # 技术面评分
    if current_price > ma5:
        score += 10
        reasons.append("站上MA5(+10)")
    else:
        score -= 10
        reasons.append("跌破MA5(-10)")
    
    if current_price > ma20:
        score += 15
        reasons.append("站上MA20(+15)")
    else:
        score -= 15
        reasons.append("跌破MA20(-15)")
    
    if rsi < 30:
        score += 20
        reasons.append("RSI超卖(+20)")
    elif rsi > 70:
        score -= 10
        reasons.append("RSI超买(-10)")
    else:
        score += 5
        reasons.append("RSI正常(+5)")
    
    if boll_pos < -1:
        score += 15
        reasons.append("布林下轨(+15)")
    elif boll_pos > 1:
        score -= 10
        reasons.append("布林上轨(-10)")
    
    # 资金流评分
    if h['code'] in zjlx_data:
        zjlx = zjlx_data[h['code']]
        flow = zjlx.get('主力净流入', 0)
        if isinstance(flow, str):
            flow = float(flow.replace('亿', '').replace('万', ''))
        
        if flow > 1:
            score += 20
            reasons.append("主力大幅流入(+20)")
        elif flow > 0:
            score += 10
            reasons.append("主力流入(+10)")
        elif flow < -1:
            score -= 20
            reasons.append("主力大幅流出(-20)")
        else:
            score -= 10
            reasons.append("主力流出(-10)")
    
    # 盈亏评分
    if profit_pct <= -15:
        score -= 30
        reasons.append("触发止损线(-30)")
    elif profit_pct <= -10:
        score -= 20
        reasons.append("接近止损线(-20)")
    elif profit_pct >= 10:
        score += 15
        reasons.append("盈利可观(+15)")
    
    print(f"  总分: {score}")
    print(f"  评分项:")
    for r in reasons:
        print(f"    • {r}")
    
    # 操作建议
    print(f"\n💡 操作建议:")
    
    if score >= 40:
        print(f"  ✅ 坚定持有/可加仓 (得分{score}≥40)")
    elif score >= 20:
        print(f"  🟡 持有观察 (得分20~40)")
    elif score >= 0:
        print(f"  ⚠️ 谨慎持有 (得分0~20)")
    elif score >= -30:
        print(f"  🟠 建议减仓 (得分-30~0)")
    else:
        print(f"  🔴 立即止损 (得分{score}≤-30)")

print("\n" + "="*70)
print("持仓总览")
print("="*70)

total_value = sum([h['shares'] * (HISTORY_DIR / f"{h['code']}.json").exists() and 
                   json.loads(open(HISTORY_DIR / f"{h['code']}.json").read())['items'][-1][5] 
                   for h in holdings if (HISTORY_DIR / f"{h['code']}.json").exists()])

print("\n完成:", datetime.now())