#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
右侧交易选股脚本 (传统技术指标)
只做上升趋势，追涨强势股
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
import sys
warnings.filterwarnings('ignore')

# 配置
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/selections")

# 右侧交易条件
CONDITIONS = {
    'ret5_min': 0.05,      # 5 日涨超 5%
    'ret10_min': 0.08,     # 10 日涨超 8%
    'rsi_min': 50,         # RSI >= 50 (强势区)
    'rsi_max': 70,         # RSI < 70 (避免超买)
    'ma5_above_ma10': True, # MA5 > MA10
    'ma10_above_ma20': True, # MA10 > MA20 (多头排列)
    'price_above_ma5': True, # 股价 >= MA5
    'vol_ratio_min': 1.2,   # 成交量放大 20%
}

TOP_N = 20

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

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
    rsi = 100 - (100 / (1 + rs))
    return rsi

def check_right_side_conditions(df):
    """检查右侧交易条件"""
    try:
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        volumes = df['vol'].values if 'vol' in df.columns else df['amount'].values
        
        if len(closes) < 60:
            return None
        
        # 均线
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        ma60 = np.mean(closes[-60:])
        
        # 收益率
        ret5 = closes[-1] / closes[-6] - 1 if len(closes) >= 6 else 0
        ret10 = closes[-1] / closes[-11] - 1 if len(closes) >= 11 else 0
        ret20 = closes[-1] / closes[-21] - 1 if len(closes) >= 21 else 0
        
        # RSI
        rsi = calculate_rsi(closes)
        
        # 均线关系
        ma5_above_ma10 = ma5 > ma10
        ma10_above_ma20 = ma10 > ma20
        price_above_ma5 = closes[-1] >= ma5
        
        # 成交量
        vol_ma5 = np.mean(volumes[-5:])
        vol_ma10 = np.mean(volumes[-10:])
        vol_ratio = vol_ma5 / vol_ma10 if vol_ma10 > 0 else 1
        
        # 检查条件
        score = 0
        max_score = 8
        
        if ret5 >= CONDITIONS['ret5_min']: score += 1
        if ret10 >= CONDITIONS['ret10_min']: score += 1
        if CONDITIONS['rsi_min'] <= rsi < CONDITIONS['rsi_max']: score += 1
        if CONDITIONS['ma5_above_ma10'] and ma5_above_ma10: score += 1
        if CONDITIONS['ma10_above_ma20'] and ma10_above_ma20: score += 1
        if CONDITIONS['price_above_ma5'] and price_above_ma5: score += 1
        if vol_ratio >= CONDITIONS['vol_ratio_min']: score += 1
        
        # 额外加分：20 日收益
        if ret20 > 0.15: score += 0.5
        if ret20 > 0.25: score += 0.5
        
        # 计算综合评分 (0-10)
        final_score = (score / max_score) * 10
        
        return {
            'ret5': ret5,
            'ret10': ret10,
            'ret20': ret20,
            'rsi': rsi,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma5_slope': (ma5 - ma10) / ma10,
            'vol_ratio': vol_ratio,
            'score': final_score,
            'close': closes[-1],
            'change': (closes[-1] / closes[-2] - 1) * 100 if len(closes) >= 2 else 0,
            # 均线位置
            'p_ma5': closes[-1] / ma5 - 1,
            'p_ma10': closes[-1] / ma10 - 1,
            'p_ma20': closes[-1] / ma20 - 1,
        }
        
    except Exception as e:
        return None

def scan_stocks():
    """扫描全市场股票"""
    log(f"\n{'='*70}")
    log("🚀 右侧交易选股系统 (传统技术指标)")
    log(f"{'='*70}")
    
    log(f"\n📋 选股条件:")
    for key, value in CONDITIONS.items():
        log(f"   • {key}: {value}")
    
    stock_list_path = HISTORY_DIR / "stock_list.json"
    with open(stock_list_path, 'r') as f:
        stock_list = json.load(f)
    
    total = len(stock_list)
    log(f"\n📊 扫描全市场：{total} 只股票")
    
    results = []
    score_dist = []
    
    for i, stock in enumerate(stock_list):
        code = stock.get('ts_code', '')
        if '.' in code:
            code = code.split('.')[0]
        name = stock.get('name', stock.get('short_name', ''))
        
        data_path = HISTORY_DIR / f"{code}.json"
        if not data_path.exists():
            continue
        
        try:
            with open(data_path, 'r') as f:
                data = json.load(f)
            
            if not data.get('items'):
                continue
            
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df = df.drop_duplicates(subset=['trade_date'], keep='last').reset_index(drop=True)
            
            metrics = check_right_side_conditions(df)
            if metrics is None:
                continue
            
            score_dist.append(metrics['score'])
            
            # 只保留高分股票 (评分>=6)
            if metrics['score'] >= 6:
                results.append({
                    'code': code,
                    'name': name,
                    'score': metrics['score'],
                    'rsi': metrics['rsi'],
                    'ret5': metrics['ret5'],
                    'ret10': metrics['ret10'],
                    'ret20': metrics['ret20'],
                    'p_ma5': metrics['p_ma5'],
                    'p_ma10': metrics['p_ma10'],
                    'p_ma20': metrics['p_ma20'],
                    'vol_ratio': metrics['vol_ratio'],
                    'close': metrics['close'],
                    'change': metrics['change'],
                    'ma5_slope': metrics['ma5_slope']
                })
            
            if (i + 1) % 1000 == 0:
                log(f"进度：{i+1}/{total} ({(i+1)/total*100:.1f}%)")
                
        except Exception as e:
            continue
    
    # 统计
    score_dist = np.array(score_dist)
    log(f"\n{'='*70}")
    log("✅ 扫描完成！")
    log(f"{'='*70}")
    log(f"扫描股票：{total} 只")
    log(f"成功计算：{len(score_dist)} 只")
    log(f"\n📊 评分分布:")
    log(f"  最小值：{score_dist.min():.1f}")
    log(f"  最大值：{score_dist.max():.1f}")
    log(f"  平均值：{score_dist.mean():.1f}")
    log(f"\n📈 高分股票统计:")
    for thresh in [8, 7, 6, 5]:
        count = np.sum(score_dist >= thresh)
        log(f"  评分≥{thresh}: {count}只 ({count/len(score_dist)*100:.2f}%)")
    
    return results

def save_results(results):
    """保存选股结果"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = OUTPUT_DIR / f"right_side_selection_{timestamp}.json"
    
    # 排序
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'time': timestamp,
            'strategy': 'right_side_technical',
            'conditions': CONDITIONS,
            'total': len(results),
            'selections': results
        }, f, indent=2, ensure_ascii=False)
    
    log(f"\n💾 结果保存：{output_path}")
    return output_path

def display_results(results):
    """显示选股结果"""
    results = results[:TOP_N]
    
    log(f"\n{'='*70}")
    log(f"🏆 右侧交易选股 TOP{len(results)} (评分≥6.0)")
    log(f"{'='*70}")
    
    if not results:
        log("\n⚠️  未找到符合条件的股票")
        log(f"\n建议:")
        log(f"  1. 放宽收益率要求 (5 日>3%, 10 日>5%)")
        log(f"  2. 放宽 RSI 范围 (45-75)")
        log(f"  3. 取消均线多头要求")
        return
    
    log(f"\n{'排名':<4} {'代码':<8} {'名称':<12} {'评分':<6} {'RSI':<6} {'5 日':<8} {'10 日':<8} {'20 日':<8} {'现价':<10}")
    log(f"{'-'*70}")
    
    for i, r in enumerate(results, 1):
        # 评级
        if r['score'] >= 8:
            rating = "⭐⭐⭐⭐⭐"
        elif r['score'] >= 7:
            rating = "⭐⭐⭐⭐"
        elif r['score'] >= 6:
            rating = "⭐⭐⭐"
        else:
            rating = "⭐⭐"
        
        log(f"{i:<4} {r['code']:<8} {r['name']:<12} {r['score']:<6.1f} {r['rsi']:<6.1f} {r['ret5']*100:>+7.1f}% {r['ret10']*100:>+7.1f}% {r['ret20']*100:>+7.1f}% ¥{r['close']:>8.2f}  {rating}")
    
    log(f"\n{'='*70}")
    log("💡 操作建议:")
    log(f"  • 评分≥8.0: 强烈买入，仓位 30%")
    log(f"  • 评分 7.0-8.0: 买入，仓位 20%")
    log(f"  • 评分 6.0-7.0: 关注，仓位 10%")
    log(f"  • 止损：-8%，止盈：+20% 后回撤 5%")
    log(f"  • 持有期：5-15 天")
    log(f"\n策略特点 (右侧交易):")
    log(f"  ✅ 已经涨起来了 (5 日>5%, 10 日>8%)")
    log(f"  ✅ 强势区 (RSI 50-70)")
    log(f"  ✅ 均线多头排列 (MA5>MA10>MA20)")
    log(f"  ✅ 成交量放大")
    log(f"{'='*70}\n")

def main():
    results = scan_stocks()
    save_results(results)
    display_results(results)

if __name__ == "__main__":
    main()
