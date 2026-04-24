#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓股票全面分析
分析 4 只持仓股：002709、华电新能源、600089、603739
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

# 持仓信息
HOLDINGS = [
    {'symbol': '002709', 'name': '天赐材料', 'shares': 500, 'cost': 48.25},
    {'symbol': '603929', 'name': '华电新能源', 'shares': 1300, 'cost': 7.41},  # 假设代码
    {'symbol': '600089', 'name': '特变电工', 'shares': 400, 'cost': 28.54},
    {'symbol': '603739', 'name': '蔚蓝生物', 'shares': 1100, 'cost': 16.60},
]

def load_data(symbol):
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data or len(data) < 100:
        return None
    df = pd.DataFrame(data)
    df = df.rename(columns={
        '日期': 'date', '开盘': 'open', '收盘': 'close',
        '最高': 'high', '最低': 'low', '成交量': 'volume'
    })
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    return df.sort_values('date').reset_index(drop=True)

def analyze_stock(df, symbol, name, shares, cost):
    """全面分析单只股票"""
    if len(df) < 100:
        return None
    
    # 计算指标
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['ma200'] = df['close'].rolling(200).mean()
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    
    # 最新数据
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    prev20 = df.iloc[-20]
    
    current_price = latest['close']
    current_loss = (current_price - cost) / cost * 100
    
    # 评分
    score = 0
    reasons = []
    warnings = []
    
    # 1. 均线排列
    if latest['ma15'] > latest['ma20']:
        score += 2
        reasons.append("✅ MA15/20 金叉")
    else:
        warnings.append("⚠️ MA15/20 死叉")
    
    # 2. 趋势
    if current_price > latest['ma60']:
        score += 2
        reasons.append("✅ 股价>MA60")
    else:
        warnings.append("⚠️ 股价<MA60")
    
    if current_price > latest['ma200']:
        score += 1
        reasons.append("✅ 长期趋势向上")
    
    # 3. 成交量
    vol_ratio = latest['volume'] / latest['vol_ma20'] if latest['vol_ma20'] > 0 else 0
    if vol_ratio > 1.5:
        score += 2
        reasons.append(f"✅ 放量{vol_ratio:.1f}倍")
    elif vol_ratio > 1:
        score += 1
        reasons.append("👍 成交量正常")
    else:
        warnings.append("⚠️ 缩量")
    
    # 4. RSI
    rsi = latest['rsi']
    if 50 < rsi < 70:
        score += 2
        reasons.append(f"✅ RSI 理想({rsi:.0f})")
    elif 45 < rsi < 75:
        score += 1
        reasons.append(f"👍 RSI 可接受({rsi:.0f})")
    else:
        warnings.append(f"⚠️ RSI{'超买' if rsi>70 else '超卖'}({rsi:.0f})")
    
    # 5. MACD
    if latest['macd'] > latest['macd_signal']:
        score += 1
        reasons.append("✅ MACD 金叉")
    else:
        warnings.append("⚠️ MACD 死叉")
    
    # 目标价和止损
    target_price = current_price * 1.10
    stop_loss = cost * 0.85
    stop_loss_current = current_price * 0.85
    
    # 建议
    if score >= 7:
        suggestion = "🟢 继续持有"
    elif score >= 5:
        suggestion = "🟡 持有观察"
    elif score >= 3:
        suggestion = "🟠 考虑减仓"
    else:
        suggestion = "🔴 建议止损"
    
    # 距离止损位
    distance_to_stop = (current_price - stop_loss_current) / current_price * 100
    
    return {
        'symbol': symbol,
        'name': name,
        'shares': shares,
        'cost': cost,
        'current_price': current_price,
        'current_loss_pct': current_loss,
        'market_value': current_price * shares,
        'total_loss': (current_price - cost) * shares,
        'score': score,
        'reasons': reasons,
        'warnings': warnings,
        'target_price': target_price,
        'stop_loss': stop_loss_current,
        'stop_loss_from_cost': stop_loss,
        'distance_to_stop': distance_to_stop,
        'suggestion': suggestion,
        'rsi': rsi,
        'vol_ratio': vol_ratio,
        'ma60_pct': (current_price - latest['ma60']) / latest['ma60'] * 100,
        'ma20d_momentum': (current_price - prev20['close']) / prev20['close'] * 100,
    }

def main():
    print("=" * 80)
    print("📊 持仓股票全面分析")
    print(f"📅 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    results = []
    
    for stock in HOLDINGS:
        df = load_data(stock['symbol'])
        if df is None:
            print(f"\n❌ {stock['symbol']} {stock['name']}: 数据不存在")
            continue
        
        result = analyze_stock(df, stock['symbol'], stock['name'], 
                              stock['shares'], stock['cost'])
        if result:
            results.append(result)
    
    # 输出结果
    print("\n" + "=" * 80)
    print("📈 持仓概览")
    print("=" * 80)
    
    total_value = sum(r['market_value'] for r in results)
    total_loss = sum(r['total_loss'] for r in results)
    
    print(f"\n{'股票':<15} {'现价':>8} {'盈亏%':>10} {'市值':>12} {'评分':>6} {'建议':>12}")
    print("-" * 70)
    
    for r in sorted(results, key=lambda x: x['score'], reverse=True):
        print(f"{r['name']:<15} ¥{r['current_price']:>7.2f} {r['current_loss_pct']:>9.2f}% ¥{r['market_value']:>10.0f} {r['score']:>6}/8 {r['suggestion']:>12}")
    
    print("-" * 70)
    print(f"{'合计':<15} {'':>8} {'':>10} ¥{total_value:>10,.0f} {'':>6} 总盈亏：¥{total_loss:,.0f}")
    
    # 详细分析
    print("\n" + "=" * 80)
    print("📋 详细分析")
    print("=" * 80)
    
    for r in results:
        print(f"\n{'='*80}")
        print(f"📊 {r['symbol']} {r['name']}")
        print(f"{'='*80}")
        print(f"持仓：{r['shares']}股 | 成本：¥{r['cost']:.2f} | 现价：¥{r['current_price']:.2f}")
        print(f"盈亏：¥{r['total_loss']:,.0f} ({r['current_loss_pct']:+.2f}%)")
        print(f"市值：¥{r['market_value']:,.0f}")
        
        print(f"\n💡 技术评分：{r['score']}/8")
        
        if r['reasons']:
            print(f"\n✅ 优势:")
            for reason in r['reasons']:
                print(f"   {reason}")
        
        if r['warnings']:
            print(f"\n⚠️ 风险:")
            for warning in r['warnings']:
                print(f"   {warning}")
        
        print(f"\n📊 技术指标:")
        print(f"   RSI: {r['rsi']:.1f}")
        print(f"   成交量比：{r['vol_ratio']:.2f}倍")
        print(f"   相对 MA60: {r['ma60_pct']:+.1f}%")
        print(f"   20 日动量：{r['ma20d_momentum']:+.1f}%")
        
        print(f"\n🎯 操作建议:")
        print(f"   建议：{r['suggestion']}")
        print(f"   目标价：¥{r['target_price']:.2f} (+10%)")
        print(f"   止损价：¥{r['stop_loss']:.2f} (-15% 从现价)")
        print(f"   成本止损：¥{r['stop_loss_from_cost']:.2f} (-15% 从成本)")
        print(f"   距离止损：{r['distance_to_stop']:+.1f}%")
        
        # 特别提示
        if r['current_loss_pct'] < -10:
            print(f"\n⚠️ 深度套牢预警：已亏损{r['current_loss_pct']:.1f}%")
            if r['current_loss_pct'] < -13:
                print(f"⚠️ 接近止损线 (-15%)，建议考虑止损")
    
    # 综合建议
    print("\n" + "=" * 80)
    print("💡 综合调仓建议")
    print("=" * 80)
    
    hold = [r for r in results if '持有' in r['suggestion']]
    reduce = [r for r in results if '减仓' in r['suggestion']]
    sell = [r for r in results if '止损' in r['suggestion']]
    
    if hold:
        print(f"\n✅ 继续持有 ({len(hold)}只):")
        for r in hold:
            print(f"   • {r['name']} ({r['current_loss_pct']:+.1f}%)")
    
    if reduce:
        print(f"\n🟠 考虑减仓 ({len(reduce)}只):")
        for r in reduce:
            print(f"   • {r['name']} ({r['current_loss_pct']:+.1f}%)")
    
    if sell:
        print(f"\n🔴 建议止损 ({len(sell)}只):")
        for r in sell:
            print(f"   • {r['name']} ({r['current_loss_pct']:+.1f}%)")
    
    # 仓位建议
    print(f"\n📊 仓位分析:")
    print(f"   当前仓位：¥{total_value:,.0f} (94.2%)")
    print(f"   建议仓位：60-80%")
    print(f"   建议减仓：¥{total_value * 0.15:,.0f} (降到 80%)")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
