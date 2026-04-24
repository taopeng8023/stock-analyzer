#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4 月全市场选股分析 - 基于 Tushare 缓存数据
扫描 5500+ 只股票，找出最佳操作标的
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')

def load_data(symbol: str) -> Optional[pd.DataFrame]:
    """加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            return None
        
        df = pd.DataFrame(data)
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount'
        })
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        return df
    except:
        return None

def calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算技术指标"""
    # 均线
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma15'] = df['close'].rolling(15).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['ma200'] = df['close'].rolling(200).mean()
    
    # 成交量均线
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    
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
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    return df

def check_golden_cross(df: pd.DataFrame) -> tuple:
    """检查金叉状态"""
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    
    # 当前金叉状态
    is_golden = latest['ma15'] > latest['ma20']
    
    # 最近金叉（5 天内）
    days_since_cross = None
    for i in range(len(df)-1, max(0, len(df)-6), -1):
        if i < 20:
            break
        if df['ma15'].iloc[i-1] <= df['ma20'].iloc[i-1] and df['ma15'].iloc[i] > df['ma20'].iloc[i]:
            days_since_cross = len(df) - 1 - i
            break
    
    return is_golden, days_since_cross

def analyze_stock(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """分析单只股票"""
    if len(df) < 200:
        return None
    
    df = calc_indicators(df)
    latest = df.iloc[-1]
    
    # 检查金叉
    is_golden, days_since_cross = check_golden_cross(df)
    
    # 只分析已金叉或即将金叉的股票
    ma_diff = latest['ma15'] - latest['ma20']
    if ma_diff < -0.05 * latest['ma20']:  # 死叉超过 5%
        return None
    
    # 计算评分
    score = 0
    reasons = []
    
    # 1. 均线排列 (2 分)
    if latest['close'] > latest['ma15'] > latest['ma20']:
        score += 2
        reasons.append("多头排列")
    elif latest['close'] > latest['ma20']:
        score += 1
    
    # 2. 中期趋势 (2 分)
    if latest['close'] > latest['ma60']:
        score += 2
        reasons.append("中期向上")
    
    # 3. 长期趋势 (1 分)
    if latest['close'] > latest['ma200']:
        score += 1
        reasons.append("长期向上")
    
    # 4. 成交量 (2 分)
    vol_ratio = latest['volume'] / latest['volume_ma20'] if latest['volume_ma20'] > 0 else 0
    if vol_ratio > 1.5:
        score += 2
        reasons.append(f"放量{vol_ratio:.1f}倍")
    elif vol_ratio > 1:
        score += 1
    
    # 5. RSI (2 分)
    rsi = latest['rsi']
    if 50 < rsi < 70:
        score += 2
        reasons.append(f"RSI 理想{rsi:.0f}")
    elif 45 < rsi < 75:
        score += 1
    
    # 6. MACD (1 分)
    if latest['macd'] > latest['macd_signal']:
        score += 1
        reasons.append("MACD 金叉")
    
    # 计算盈利概率
    win_prob = 30 + (score / 8) * 55
    
    # 计算预期收益（基于 20 日涨幅）
    prev20 = df.iloc[-20] if len(df) > 20 else latest
    momentum_20d = (latest['close'] - prev20['close']) / prev20['close'] * 100
    
    return {
        'symbol': symbol,
        'score': score,
        'win_prob': win_prob,
        'price': latest['close'],
        'ma_diff_pct': ma_diff / latest['ma20'] * 100,
        'is_golden': is_golden,
        'days_since_cross': days_since_cross,
        'vol_ratio': vol_ratio,
        'rsi': rsi,
        'macd_golden': latest['macd'] > latest['macd_signal'],
        'momentum_20d': momentum_20d,
        'reasons': reasons,
        'ma60_pct': (latest['close'] - latest['ma60']) / latest['ma60'] * 100,
        'ma200_pct': (latest['close'] - latest['ma200']) / latest['ma200'] * 100
    }

def scan_market():
    """扫描全市场"""
    print("=" * 80)
    print("🚀 4 月全市场选股分析")
    print(f"📅 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📊 数据源：Tushare 缓存 (5517 只股票)")
    print("=" * 80)
    
    results = []
    stock_files = list(CACHE_DIR.glob('*.json'))
    total = len(stock_files)
    
    print(f"\n🔍 开始扫描 {total} 只股票...\n")
    
    for i, filepath in enumerate(stock_files):
        symbol = filepath.stem
        
        # 进度显示
        if (i + 1) % 1000 == 0:
            print(f"  进度：{i+1}/{total} ({(i+1)/total*100:.1f}%)")
        
        df = load_data(symbol)
        if df is None:
            continue
        
        result = analyze_stock(df, symbol)
        if result:
            results.append(result)
    
    print(f"\n✅ 扫描完成，找到 {len(results)} 只候选股票\n")
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results

def print_top_recommendations(results: List[Dict], top_n: int = 10):
    """输出 TOP 推荐"""
    print("=" * 80)
    print(f"🏆 4 月 TOP {top_n} 推荐股票")
    print("=" * 80)
    
    # 筛选已金叉的股票
    golden_results = [r for r in results if r['is_golden']]
    
    for i, r in enumerate(golden_results[:top_n], 1):
        print(f"\n{'='*80}")
        print(f"🥇 第{i}名：{r['symbol']} | 评分：{r['score']}/8 | 盈利概率：{r['win_prob']:.1f}%")
        print(f"{'='*80}")
        print(f"💰 当前价：¥{r['price']:.2f}")
        print(f"📈 20 日 momentum: {r['momentum_20d']:+.1f}%")
        print(f"📊 MA15/20 差值：{r['ma_diff_pct']:+.2f}%")
        print(f"📊 相对 MA60: {r['ma60_pct']:+.1f}% | 相对 MA200: {r['ma200_pct']:+.1f}%")
        print(f"📊 成交量比：{r['vol_ratio']:.2f}倍 | RSI: {r['rsi']:.1f}")
        print(f"📅 金叉状态：{'✅ 已金叉' if r['is_golden'] else '⏳ 即将金叉'}")
        if r['days_since_cross']:
            print(f"   金叉于 {r['days_since_cross']} 天前")
        print(f"📊 MACD: {'✅ 金叉' if r['macd_golden'] else '❌ 死叉'}")
        
        if r['reasons']:
            print(f"\n✅ 优势:")
            for reason in r['reasons'][:5]:
                print(f"   • {reason}")
        
        # 操作建议
        target = r['price'] * 1.10
        stop_loss = r['price'] * 0.85
        print(f"\n🎯 目标价：¥{target:.2f} (+10%)")
        print(f"🛑 止损位：¥{stop_loss:.2f} (-15%)")
        print(f"💡 建议：{'🟢 强烈推荐' if r['score'] >= 7 else '🟡 关注' if r['score'] >= 5 else '⚪ 观望'}")
    
    print("\n" + "=" * 80)

def print_sector_analysis(results: List[Dict]):
    """板块分析（简化版）"""
    print("\n" + "=" * 80)
    print("📊 市场整体分析")
    print("=" * 80)
    
    golden_count = sum(1 for r in results if r['is_golden'])
    high_score = sum(1 for r in results if r['score'] >= 7)
    avg_score = sum(r['score'] for r in results) / len(results) if results else 0
    
    print(f"\n📈 市场情绪:")
    print(f"   候选股票：{len(results)}只")
    print(f"   已金叉：{golden_count}只 ({golden_count/len(results)*100:.1f}%)")
    print(f"   高评分 (≥7): {high_score}只 ({high_score/len(results)*100:.1f}%)")
    print(f"   平均评分：{avg_score:.2f}/8")
    
    print(f"\n💡 4 月策略建议:")
    if avg_score > 5:
        print("   🟢 市场偏多，可积极操作")
    elif avg_score > 4:
        print("   🟡 市场中性，精选个股")
    else:
        print("   🔴 市场偏弱，谨慎操作")
    
    print(f"\n📋 推荐策略:")
    print(f"   1. 首选：MA15/20 金叉 + 放量股票")
    print(f"   2. 止盈：移动止盈 10-15% (基于回测最优)")
    print(f"   3. 止损：固定 -15%")
    print(f"   4. 仓位：单只 30-40%，分散 3-5 只")

def main():
    """主函数"""
    results = scan_market()
    
    if not results:
        print("❌ 未找到符合条件的股票")
        return
    
    print_top_recommendations(results, top_n=10)
    print_sector_analysis(results)
    
    print("\n" + "=" * 80)
    print("⚠️ 风险提示")
    print("=" * 80)
    print("1. 本分析基于历史数据，不构成投资建议")
    print("2. 请结合基本面、消息面综合判断")
    print("3. 严格执行止损纪律")
    print("4. 4 月需关注：季报披露、政策变化、外围市场")
    print("=" * 80)

if __name__ == '__main__':
    main()
