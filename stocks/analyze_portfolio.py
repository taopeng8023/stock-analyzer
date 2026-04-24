#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量股票金叉分析 - 检查指定股票池的金叉信号和买入建议
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

CACHE_DIR = Path(__file__).parent / 'data_tushare'

def load_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """从缓存加载股票数据"""
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
    except Exception as e:
        return None

def calc_ma(series: pd.Series, period: int) -> pd.Series:
    """计算移动平均线"""
    return series.rolling(window=period).mean()

def analyze_stock(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """分析单只股票"""
    if len(df) < 200:
        return None
    
    # 计算均线
    df['ma15'] = calc_ma(df['close'], 15)
    df['ma20'] = calc_ma(df['close'], 20)
    df['ma60'] = calc_ma(df['close'], 60)
    df['ma200'] = calc_ma(df['close'], 200)
    
    # 计算成交量均线
    df['volume_ma20'] = df['volume'].rolling(window=20).mean()
    
    # 计算 RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 获取最新数据
    latest_idx = len(df) - 1
    current_price = df['close'].iloc[latest_idx]
    current_date = df['date'].iloc[latest_idx]
    
    # 检查是否已金叉（最近 10 天内）
    golden_cross_day = None
    days_since_cross = None
    
    for i in range(latest_idx, max(0, latest_idx - 10), -1):
        if i < 20:
            continue
        
        prev_ma15 = df['ma15'].iloc[i-1]
        prev_ma20 = df['ma20'].iloc[i-1]
        curr_ma15 = df['ma15'].iloc[i]
        curr_ma20 = df['ma20'].iloc[i]
        
        if pd.notna(prev_ma15) and pd.notna(prev_ma20) and pd.notna(curr_ma15) and pd.notna(curr_ma20):
            if prev_ma15 <= prev_ma20 and curr_ma15 > curr_ma20:
                golden_cross_day = i
                days_since_cross = latest_idx - i
                break
    
    # 检查当前是否仍保持金叉状态
    ma15_curr = df['ma15'].iloc[latest_idx]
    ma20_curr = df['ma20'].iloc[latest_idx]
    is_golden_cross = pd.notna(ma15_curr) and pd.notna(ma20_curr) and ma15_curr > ma20_curr
    
    # 计算评分
    score = 0
    reasons = []
    warnings = []
    
    volume = df['volume'].iloc[latest_idx]
    volume_ma20 = df['volume_ma20'].iloc[latest_idx]
    ma60 = df['ma60'].iloc[latest_idx]
    ma200 = df['ma200'].iloc[latest_idx]
    rsi = df['rsi'].iloc[latest_idx]
    
    # 1. 成交量评分
    if pd.notna(volume_ma20) and volume > volume_ma20 * 1.5:
        score += 2
        reasons.append(f"✅ 放量 {volume/volume_ma20:.2f}倍")
    elif pd.notna(volume_ma20) and volume > volume_ma20:
        score += 1
        reasons.append(f"👍 成交量正常 ({volume/volume_ma20:.2f}倍)")
    else:
        warnings.append(f"⚠️ 成交量不足 ({volume/volume_ma20:.2f}倍)" if pd.notna(volume_ma20) else "⚠️ 成交量数据缺失")
    
    # 2. 趋势评分
    if pd.notna(ma60) and current_price > ma60:
        score += 2
        reasons.append(f"✅ 多头趋势 (股价>MA60 +{(current_price-ma60)/ma60*100:.1f}%)")
    else:
        warnings.append(f"⚠️ 股价在 MA60 下方 ({(current_price-ma60)/ma60*100:.1f}%)")
    
    # 3. 长期趋势
    if pd.notna(ma200) and current_price > ma200:
        score += 1
        reasons.append(f"✅ 长期趋势向上")
    else:
        warnings.append(f"⚠️ 长期趋势偏弱")
    
    # 4. RSI 评分
    if pd.notna(rsi):
        if 50 < rsi < 70:
            score += 2
            reasons.append(f"✅ RSI 理想 ({rsi:.1f})")
        elif 45 < rsi < 75:
            score += 1
            reasons.append(f"👍 RSI 可接受 ({rsi:.1f})")
        else:
            warnings.append(f"⚠️ RSI {'超买' if rsi > 75 else '超卖'} ({rsi:.1f})")
    
    # 5. 金叉强度
    if is_golden_cross and pd.notna(ma15_curr) and pd.notna(ma20_curr):
        cross_strength = (ma15_curr - ma20_curr) / ma20_curr * 100
        if cross_strength > 1.5:
            score += 2
            reasons.append(f"✅ 金叉强劲 ({cross_strength:.2f}%)")
        elif cross_strength > 0.5:
            score += 1
            reasons.append(f"👍 金叉确认 ({cross_strength:.2f}%)")
        else:
            warnings.append(f"⚠️ 金叉较弱 ({cross_strength:.2f}%)")
    
    # 计算盈利概率
    win_probability = 30 + (score / 8) * 55
    
    # 计算目标价和止损
    target_price = current_price * 1.10
    stop_loss = current_price * 0.85
    
    # 计算 MA15/MA20 差值百分比
    ma_diff_pct = (ma15_curr - ma20_curr) / ma20_curr * 100 if pd.notna(ma15_curr) and pd.notna(ma20_curr) else 0
    
    return {
        'symbol': symbol,
        'score': score,
        'win_probability': win_probability,
        'current_price': current_price,
        'target_price': target_price,
        'stop_loss': stop_loss,
        'is_golden_cross': is_golden_cross,
        'golden_cross_date': df['date'].iloc[golden_cross_day].strftime('%Y-%m-%d') if golden_cross_day else None,
        'days_since_cross': days_since_cross,
        'reasons': reasons,
        'warnings': warnings,
        'volume_ratio': volume / volume_ma20 if pd.notna(volume_ma20) and volume_ma20 > 0 else 0,
        'rsi': rsi if pd.notna(rsi) else 0,
        'ma_diff_pct': ma_diff_pct,
        'current_date': current_date.strftime('%Y-%m-%d')
    }

def analyze_portfolio(symbols: List[str]):
    """分析股票组合"""
    print("=" * 80)
    print("📊 股票池金叉分析报告")
    print(f"📅 分析日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    results = []
    not_found = []
    
    print(f"\n🔍 分析 {len(symbols)} 只股票...\n")
    
    for symbol in symbols:
        df = load_stock_data(symbol)
        if df is None:
            not_found.append(symbol)
            print(f"❌ {symbol}: 数据不存在")
            continue
        
        result = analyze_stock(df, symbol)
        if result:
            results.append(result)
            status = "✅ 已金叉" if result['is_golden_cross'] else "⏳ 未金叉"
            print(f"✓ {symbol}: {status} | 评分：{result['score']}/8 | 盈利概率：{result['win_probability']:.1f}%")
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # 输出汇总
    print("\n" + "=" * 80)
    print(f"📊 汇总：{len(results)} 只股票已分析，{len(not_found)} 只数据缺失")
    golden_cross_count = sum(1 for r in results if r['is_golden_cross'])
    print(f"✅ 已金叉：{golden_cross_count}只 | ⏳ 未金叉：{len(results) - golden_cross_count}只")
    print("=" * 80)
    
    # 输出前 5 推荐
    golden_cross_results = [r for r in results if r['is_golden_cross']]
    
    if golden_cross_results:
        print("\n🏆 TOP 5 推荐买入（已金叉）\n")
        
        for i, r in enumerate(golden_cross_results[:5], 1):
            print(f"{'='*80}")
            print(f"🥇 第{i}名：{r['symbol']} | 评分：{r['score']}/8 | 盈利概率：{r['win_probability']:.1f}%")
            print(f"{'='*80}")
            print(f"💰 当前价：¥{r['current_price']:.2f}")
            print(f"🎯 目标价：¥{r['target_price']:.2f} (+10%)")
            print(f"🛑 止损位：¥{r['stop_loss']:.2f} (-15%)")
            if r['golden_cross_date']:
                print(f"📅 金叉日期：{r['golden_cross_date']} ({r['days_since_cross']}天前)")
            print(f"📊 成交量比：{r['volume_ratio']:.2f}倍 | RSI: {r['rsi']:.1f} | MA 差值：{r['ma_diff_pct']:.2f}%")
            
            if r['reasons']:
                print(f"\n✅ 优势:")
                for reason in r['reasons']:
                    print(f"   {reason}")
            
            if r['warnings']:
                print(f"\n⚠️ 风险:")
                for warning in r['warnings']:
                    print(f"   {warning}")
            print()
    
    # 输出未金叉股票（潜在关注）
    not_crossed = [r for r in results if not r['is_golden_cross']]
    if not_crossed:
        print("\n" + "=" * 80)
        print("⏳ 未金叉股票（可加入自选关注）")
        print("=" * 80)
        for r in not_crossed[:10]:
            print(f"{r['symbol']}: ¥{r['current_price']:.2f} | 评分：{r['score']}/8 | MA 差值：{r['ma_diff_pct']:.2f}%")
    
    # 输出数据缺失
    if not_found:
        print("\n" + "=" * 80)
        print(f"❌ 数据缺失：{', '.join(not_found)}")
        print("   建议：运行数据更新脚本获取最新数据")
        print("=" * 80)

if __name__ == '__main__':
    # 用户提供的股票池
    symbols = [
        '603738', '603365', '600791', '600750', '600645',
        '600433', '600233', '301295', '301222', '300938',
        '300565', '300453', '300143', '300055', '002923',
        '002812', '002709', '002569', '002246', '001338',
        '000909', '000729', '000048'
    ]
    
    analyze_portfolio(symbols)
