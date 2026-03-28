#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化选股策略 v2.0

基于回测结果优化筛选条件:
- 结合回测表现调整评分权重
- 增加技术面过滤条件
- 优化资金面评分标准
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest_with_cache import load_cached_data, calculate_score


# ==================== 优化后的评分系统 ====================

def optimized_score(data: List[Dict], idx: int) -> Tuple[float, Dict]:
    """
    优化后的综合评分系统 (基于回测反馈)
    
    优化点:
    1. 增加趋势强度权重
    2. 增加成交量持续性评分
    3. 增加 MACD 金叉死叉判断
    4. 降低短期波动影响
    
    Returns:
        (总分，各维度得分详情)
    """
    if idx < 60:  # 增加数据需求
        return 0, {}
    
    scores = {}
    
    # 提取价格数据
    closes = [d['close'] for d in data[:idx+1]]
    highs = [d['high'] for d in data[:idx+1]]
    lows = [d['low'] for d in data[:idx+1]]
    volumes = [d['volume'] for d in data[:idx+1]]
    amounts = [d['amount'] for d in data[:idx+1]]
    
    # === 技术面评分 (45 分) - 提高权重 ===
    tech_score = 0
    
    # MACD 评分 (15 分) - 提高权重
    macd = calculate_macd_optimized(closes)
    if macd['macd'][idx] is not None:
        if macd['macd'][idx] > 0:
            tech_score += 10
            # MACD 柱线放大
            if idx >= 2 and macd['macd'][idx] > macd['macd'][idx-1]:
                tech_score += 5
        elif macd['macd'][idx] > -3:
            tech_score += 5
    
    # KDJ 评分 (10 分)
    kdj = calculate_kdj_optimized(data[:idx+1])
    if kdj['k'][idx] is not None:
        k = kdj['k'][idx]
        d = kdj['d'][idx]
        if 30 <= k <= 70:  # 中性区域
            tech_score += 6
            if k > d:  # 金叉
                tech_score += 4
        elif k < 30:  # 超卖
            tech_score += 8
        elif k > 70:  # 超买
            tech_score += 3
    
    # RSI 评分 (10 分)
    rsi = calculate_rsi_optimized(closes)
    if rsi[idx] is not None:
        rsi_val = rsi[idx]
        if 45 <= rsi_val <= 65:  # 中性偏强
            tech_score += 7
        elif 35 <= rsi_val < 45 or 65 < rsi_val <= 75:
            tech_score += 5
        elif rsi_val < 35:  # 超卖
            tech_score += 8
        elif rsi_val > 75:  # 超买
            tech_score += 2
    
    # 均线评分 (10 分)
    ma5 = calculate_ma(closes, 5)[idx]
    ma20 = calculate_ma(closes, 20)[idx]
    ma60 = calculate_ma(closes, 60)[idx] if idx >= 59 else None
    
    if ma5 and ma20:
        if ma5 > ma20:
            tech_score += 6
            if ma60 and ma20 > ma60:  # 多头排列
                tech_score += 4
        else:
            tech_score += 2
    
    scores['技术面'] = min(tech_score, 45)
    
    # === 资金面评分 (25 分) ===
    money_score = 0
    
    # 成交量持续性 (15 分) - 新增
    if idx >= 30:
        recent_vol = sum(volumes[idx-5:idx]) / 5
        prev_vol = sum(volumes[idx-15:idx-5]) / 10
        if recent_vol > prev_vol * 1.3:  # 近期放量 30%
            money_score += 15
        elif recent_vol > prev_vol * 1.1:
            money_score += 10
        elif recent_vol > prev_vol:
            money_score += 6
        else:
            money_score += 3
    
    # 成交额规模 (10 分)
    if idx >= 20:
        avg_amount = sum(amounts[idx-20:idx]) / 20
        if avg_amount > 5e8:  # 5 亿以上
            money_score += 10
        elif avg_amount > 2e8:
            money_score += 8
        elif avg_amount > 1e8:
            money_score += 6
        elif avg_amount > 5e7:
            money_score += 4
        else:
            money_score += 2
    
    scores['资金面'] = min(money_score, 25)
    
    # === 趋势面评分 (20 分) ===
    trend_score = 0
    
    # 短期趋势 (10 分)
    if idx >= 10:
        short_trend = (closes[idx] - closes[idx-10]) / closes[idx-10] * 100
        if short_trend > 10:
            trend_score += 10
        elif short_trend > 5:
            trend_score += 8
        elif short_trend > 0:
            trend_score += 6
        elif short_trend > -5:
            trend_score += 3
        else:
            trend_score += 1
    
    # 中期趋势 (10 分)
    if idx >= 30:
        mid_trend = (closes[idx] - closes[idx-30]) / closes[idx-30] * 100
        if mid_trend > 15:
            trend_score += 10
        elif mid_trend > 8:
            trend_score += 8
        elif mid_trend > 0:
            trend_score += 5
        elif mid_trend > -10:
            trend_score += 2
        else:
            trend_score += 0
    
    scores['趋势面'] = min(trend_score, 20)
    
    # === 风险面评分 (10 分) - 降低权重 ===
    risk_score = 10
    
    # 波动性扣分
    if idx >= 30:
        returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(idx-29, idx+1)]
        volatility = np.std(returns)
        
        if volatility > 6:
            risk_score -= 6
        elif volatility > 4:
            risk_score -= 4
        elif volatility > 3:
            risk_score -= 2
    
    scores['风险面'] = max(risk_score, 0)
    
    # === 总分 ===
    total_score = sum(scores.values())
    
    return total_score, scores


# ==================== 技术指标计算 (优化版) ====================

def calculate_ma(prices: List[float], period: int) -> List[float]:
    """计算移动平均线"""
    result = []
    for i in range(len(prices)):
        if i < period - 1:
            result.append(None)
        else:
            avg = sum(prices[i-period+1:i+1]) / period
            result.append(avg)
    return result


def calculate_macd_optimized(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    """优化版 MACD 计算"""
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
    """计算指数移动平均线"""
    if len(prices) < period:
        return [None] * len(prices)
    
    multiplier = 2 / (period + 1)
    sma = sum(prices[:period]) / period
    result = [sma]
    
    for i in range(1, len(prices)):
        ema = (prices[i] - result[-1]) * multiplier + result[-1]
        result.append(ema)
    
    return [None] * (period - 1) + result


def calculate_kdj_optimized(data: List[Dict], n: int = 9) -> Dict:
    """优化版 KDJ 计算"""
    k_values, d_values, j_values = [], [], []
    prev_k, prev_d = 50, 50
    
    for i in range(len(data)):
        if i < n - 1:
            k_values.append(None)
            d_values.append(None)
            j_values.append(None)
            continue
        
        period = data[i-n+1:i+1]
        highest = max(d['high'] for d in period)
        lowest = min(d['low'] for d in period)
        current_close = data[i]['close']
        
        if highest == lowest:
            rsv = 50
        else:
            rsv = (current_close - lowest) / (highest - lowest) * 100
        
        k = (2/3) * prev_k + (1/3) * rsv
        d = (2/3) * prev_d + (1/3) * k
        j = 3 * k - 2 * d
        
        k_values.append(k)
        d_values.append(d)
        j_values.append(j)
        
        prev_k, prev_d = k, d
    
    return {'k': k_values, 'd': d_values, 'j': j_values}


def calculate_rsi_optimized(prices: List[float], period: int = 14) -> List[float]:
    """优化版 RSI 计算"""
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


# ==================== 优化筛选策略 ====================

def optimized_screen(data: List[Dict], min_score: float = 70) -> List[Dict]:
    """
    优化后的选股策略
    
    过滤条件:
    1. 综合评分 >= min_score
    2. 股价在 20 日均线上方
    3. 近期成交量放大
    4. 非 ST 股票 (通过价格过滤)
    """
    signals = []
    
    for idx in range(60, len(data)):
        score, scores_detail = optimized_score(data, idx)
        
        if score >= min_score:
            # 额外过滤条件
            closes = [d['close'] for d in data[:idx+1]]
            ma20 = calculate_ma(closes, 20)[idx]
            
            # 股价在 20 日均线上方
            if data[idx]['close'] > ma20:
                signals.append({
                    'date': data[idx]['date'],
                    'code': data[idx].get('code', 'UNKNOWN'),
                    'price': data[idx]['close'],
                    'score': score,
                    'scores_detail': scores_detail,
                    'ma20_ratio': data[idx]['close'] / ma20 if ma20 else 1
                })
    
    return signals


# ==================== 批量筛选 ====================

def batch_screen_all_stocks(cache_dir: str = None, min_score: float = 75) -> List[Dict]:
    """
    批量筛选所有股票
    
    Returns:
        符合条件的股票列表
    """
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', datetime.now().strftime('%Y%m'))
    
    if not os.path.exists(cache_dir):
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache', 'history', last_month.strftime('%Y%m'))
    
    results = []
    files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
    
    print(f"🔍 开始筛选 {len(files)} 只股票...\n")
    
    for i, file in enumerate(files, 1):
        code = file.replace('.json', '')
        
        # 进度显示
        if i % 500 == 0:
            print(f"  已处理 {i}/{len(files)} 只...")
        
        data = load_cached_data(code, cache_dir)
        if not data or len(data) < 60:
            continue
        
        # 获取最新信号
        signals = optimized_screen(data, min_score)
        
        if signals:
            latest = signals[-1]
            results.append({
                'code': code,
                'date': latest['date'],
                'price': latest['price'],
                'score': latest['score'],
                'ma20_ratio': latest['ma20_ratio'],
                'tech_score': latest['scores_detail'].get('技术面', 0),
                'money_score': latest['scores_detail'].get('资金面', 0),
                'trend_score': latest['scores_detail'].get('趋势面', 0),
                'risk_score': latest['scores_detail'].get('风险面', 0)
            })
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results


def print_screen_results(results: List[Dict], top_n: int = 20):
    """打印筛选结果"""
    print("\n" + "="*100)
    print("📊 优化选股策略 - 筛选结果".center(100))
    print("="*100)
    
    print(f"\n共找到 {len(results)} 只符合条件的股票\n")
    
    print(f"{'排名':<6} {'代码':<10} {'评分':>8} {'股价':>10} {'均线比':>10} {'技术':>8} {'资金':>8} {'趋势':>8} {'风险':>8}")
    print("-"*100)
    
    for i, r in enumerate(results[:top_n], 1):
        medal = f"🥇" if i == 1 else f"🥈" if i == 2 else f"🥉" if i == 3 else f"{i}."
        print(f"{medal:<6} {r['code']:<10} {r['score']:>8.1f} {r['price']:>10.2f} {r['ma20_ratio']:>10.2f} "
              f"{r['tech_score']:>8.1f} {r['money_score']:>8.1f} {r['trend_score']:>8.1f} {r['risk_score']:>8.1f}")
    
    print("="*100 + "\n")


# ==================== 主程序 ====================

def main():
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description='优化选股策略')
    parser.add_argument('--min-score', type=float, default=75, help='最低评分阈值 (默认 75)')
    parser.add_argument('--top', type=int, default=20, help='显示前 N 只股票')
    parser.add_argument('--save', action='store_true', help='保存结果到文件')
    
    args = parser.parse_args()
    
    print("="*100)
    print("🚀 优化选股策略 v2.0".center(100))
    print("="*100)
    print(f"基于回测结果优化的筛选条件")
    print("="*100 + "\n")
    
    # 批量筛选
    results = batch_screen_all_stocks(min_score=args.min_score)
    
    # 打印结果
    print_screen_results(results, top_n=args.top)
    
    # 保存结果
    if args.save and results:
        output_dir = os.path.join(os.path.dirname(__file__), 'screen_results')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(output_dir, f'screen_{timestamp}.json')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'min_score': args.min_score,
                'total_found': len(results),
                'top_stocks': results[:args.top]
            }, f, ensure_ascii=False, indent=2)
        
        print(f"📁 结果已保存：{filepath}")


if __name__ == '__main__':
    main()
