#!/usr/bin/env python3
"""
江恩理论策略模块

基于《江恩华尔街 45 年》- 威廉·江恩

核心原理:
1. 价格与时间的正方形关系
2. 江恩角度线 (Gann Angles)
3. 重要百分比回调位
4. 时间周期理论
5. 价格轮动 (Price Wheel)

用法:
    from gann_theory import GannAnalyzer
    analyzer = GannAnalyzer()
    gann_data = analyzer.analyze(kline_data)
"""

import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class GannAnalyzer:
    """江恩理论分析器"""
    
    # 江恩重要角度
    GANN_ANGLES = [
        (1, 1),    # 45 度 - 最重要
        (2, 1),    # 63.75 度
        (1, 2),    # 26.25 度
        (4, 1),    # 75 度
        (1, 4),    # 15 度
    ]
    
    # 江恩重要百分比
    GANN_PERCENTAGES = [
        0.125,  # 1/8
        0.25,   # 2/8
        0.375,  # 3/8
        0.5,    # 4/8 - 最重要
        0.625,  # 5/8
        0.75,   # 6/8
        0.875,  # 7/8
        1.0,    # 8/8
    ]
    
    # 江恩时间周期 (天)
    GANN_CYCLES = [30, 45, 60, 90, 120, 180, 270, 360]
    
    def __init__(self):
        self.current_price = 0
        self.swing_high = 0
        self.swing_low = 0
    
    def analyze(self, data: List[Dict]) -> Dict:
        """
        江恩理论综合分析
        
        Returns:
            {
                'trend': str,  # 趋势
                'support_levels': List[float],  # 支撑位
                'resistance_levels': List[float],  # 阻力位
                'time_cycle': str,  # 时间周期
                'angle_position': str,  # 角度线位置
                'score': float,  # 综合评分
            }
        """
        if len(data) < 30:
            return {'error': '数据不足'}
        
        # 1. 识别高低点
        self.swing_high = max(k['high'] for k in data[-90:])  # 90 日最高
        self.swing_low = min(k['low'] for k in data[-90:])   # 90 日最低
        self.current_price = data[-1]['close']
        
        # 2. 计算江恩支撑/阻力位
        support_levels = self._calculate_support_levels()
        resistance_levels = self._calculate_resistance_levels()
        
        # 3. 江恩角度线分析
        angle_position = self._analyze_gann_angles(data)
        
        # 4. 时间周期分析
        time_cycle = self._analyze_time_cycles(data)
        
        # 5. 百分比回调分析
        fib_levels = self._calculate_percentage_retracement()
        
        # 6. 综合评分
        score = self._calculate_score(support_levels, resistance_levels, angle_position)
        
        # 7. 趋势判断
        trend = self._determine_trend(data)
        
        return {
            'trend': trend,
            'support_levels': support_levels,
            'resistance_levels': resistance_levels,
            'time_cycle': time_cycle,
            'angle_position': angle_position,
            'percentage_levels': fib_levels,
            'score': score,
            'swing_high': self.swing_high,
            'swing_low': self.swing_low,
            'current_price': self.current_price,
        }
    
    def _calculate_support_levels(self) -> List[float]:
        """计算江恩支撑位"""
        levels = []
        price_range = self.swing_high - self.swing_low
        
        # 江恩百分比支撑位
        for pct in self.GANN_PERCENTAGES:
            level = self.swing_high - price_range * pct
            levels.append(round(level, 2))
        
        # 江恩轮动位 (简化)
        base = self.swing_low
        for i in range(1, 9):
            levels.append(round(base + i * (price_range / 8), 2))
        
        # 去重排序
        levels = sorted(list(set(levels)))
        
        # 只保留当前价格下方的支撑位
        support = [l for l in levels if l < self.current_price]
        
        return support[-5:] if len(support) > 5 else support
    
    def _calculate_resistance_levels(self) -> List[float]:
        """计算江恩阻力位"""
        levels = []
        price_range = self.swing_high - self.swing_low
        
        # 江恩百分比阻力位
        for pct in self.GANN_PERCENTAGES:
            level = self.swing_low + price_range * pct
            levels.append(round(level, 2))
        
        # 江恩轮动位 (简化)
        base = self.swing_high
        for i in range(1, 9):
            levels.append(round(base + i * (price_range / 8), 2))
        
        # 去重排序
        levels = sorted(list(set(levels)))
        
        # 只保留当前价格上方的阻力位
        resistance = [l for l in levels if l > self.current_price]
        
        return resistance[:5] if len(resistance) > 5 else resistance
    
    def _analyze_gann_angles(self, data: List[Dict]) -> Dict:
        """江恩角度线分析"""
        # 简化版：计算价格相对于 45 度线的位置
        if len(data) < 60:
            return {'position': 'unknown', 'angle': '45 度'}
        
        # 找到 60 日前的低点
        low_60 = min(k['low'] for k in data[-90:-30])
        low_date_idx = next(i for i, k in enumerate(data) if k['low'] == low_60)
        
        # 计算 45 度线理论位置
        days_elapsed = len(data) - low_date_idx
        price_per_day = (data[-1]['close'] - low_60) / days_elapsed if days_elapsed > 0 else 0
        
        # 江恩 45 度线：1 单位价格 = 1 单位时间
        # 简化判断
        if price_per_day > 0.5:
            position = '45 度线上方 (强势)'
            signal = 'bullish'
        elif price_per_day < 0.1:
            position = '45 度线下方 (弱势)'
            signal = 'bearish'
        else:
            position = '45 度线附近 (震荡)'
            signal = 'neutral'
        
        return {
            'position': position,
            'angle': '45 度',
            'signal': signal,
            'price_per_day': round(price_per_day, 3),
        }
    
    def _analyze_time_cycles(self, data: List[Dict]) -> Dict:
        """时间周期分析"""
        # 计算从重要高低点以来的天数
        if not data:
            return {'cycle': 'unknown', 'days': 0}
        
        # 找到最近的重要低点
        recent_low = min(k['low'] for k in data[-60:])
        low_date_idx = next(i for i, k in enumerate(data) if k['low'] == recent_low)
        days_from_low = len(data) - low_date_idx
        
        # 检查是否接近江恩时间周期
        nearest_cycle = min(self.GANN_CYCLES, key=lambda x: abs(x - days_from_low))
        cycle_diff = abs(nearest_cycle - days_from_low)
        
        if cycle_diff <= 5:
            status = f'接近{nearest_cycle}天周期 (±{cycle_diff}天)'
            signal = 'important'
        else:
            status = f'距离最近周期：{nearest_cycle}天 (还有{nearest_cycle - days_from_low}天)'
            signal = 'normal'
        
        return {
            'cycle': status,
            'days': days_from_low,
            'nearest_cycle': nearest_cycle,
            'signal': signal,
        }
    
    def _calculate_percentage_retracement(self) -> Dict:
        """百分比回调分析"""
        price_range = self.swing_high - self.swing_low
        
        levels = {}
        for pct in [0.25, 0.5, 0.75]:
            level = self.swing_high - price_range * pct
            levels[f'{int(pct*100)}%'] = round(level, 2)
        
        # 判断当前位置
        if price_range > 0:
            current_retracement = (self.swing_high - self.current_price) / price_range
        else:
            current_retracement = 0
        
        levels['current'] = current_retracement
        
        return levels
    
    def _determine_trend(self, data: List[Dict]) -> str:
        """趋势判断"""
        if len(data) < 20:
            return 'unknown'
        
        # 简单趋势判断
        ma20 = sum(k['close'] for k in data[-20:]) / 20
        
        if self.current_price > ma20 * 1.05:
            return 'strong_bullish'  # 强势上涨
        elif self.current_price > ma20:
            return 'bullish'  # 上涨
        elif self.current_price < ma20 * 0.95:
            return 'strong_bearish'  # 强势下跌
        else:
            return 'bearish'  # 下跌
    
    def _calculate_score(self, support: List[float], resistance: List[float], 
                        angle_data: Dict) -> float:
        """
        江恩理论综合评分 (0-10 分)
        
        评分标准:
        - 价格在支撑位上方：+2 分
        - 价格在阻力位下方：+2 分
        - 45 度线上方：+3 分
        - 时间周期重要位：+2 分
        - 趋势向上：+1 分
        """
        score = 5.0  # 基础分
        
        # 支撑位评分
        if support:
            nearest_support = max(support)
            if self.current_price > nearest_support * 1.02:
                score += 2
            elif self.current_price < nearest_support * 0.98:
                score -= 2
        
        # 阻力位评分
        if resistance:
            nearest_resistance = min(resistance)
            if self.current_price < nearest_resistance * 0.98:
                score += 2
            elif self.current_price > nearest_resistance * 1.02:
                score += 1  # 突破阻力
        
        # 角度线评分
        if angle_data.get('signal') == 'bullish':
            score += 3
        elif angle_data.get('signal') == 'bearish':
            score -= 2
        
        # 趋势评分
        trend = self._determine_trend([])
        if 'bullish' in trend:
            score += 1
        elif 'bearish' in trend:
            score -= 1
        
        return min(max(score, 0), 10)
    
    def get_trading_signal(self, gann_data: Dict) -> Dict:
        """
        根据江恩分析获取交易信号
        
        Returns:
            {
                'signal': str,  # buy/sell/hold
                'reason': str,  # 理由
                'target': float,  # 目标位
                'stop_loss': float,  # 止损位
                'confidence': float,  # 置信度
            }
        """
        score = gann_data.get('score', 5)
        trend = gann_data.get('trend', 'unknown')
        support = gann_data.get('support_levels', [])
        resistance = gann_data.get('resistance_levels', [])
        angle_signal = gann_data.get('angle_position', {}).get('signal', 'neutral')
        
        # 江恩交易逻辑
        if score >= 7 and 'bullish' in trend:
            signal = 'buy'
            reason = f'江恩评分{score:.1f}，趋势向上，角度线强势'
            target = resistance[0] if resistance else self.current_price * 1.10
            stop_loss = support[-1] * 0.97 if support else self.current_price * 0.95
            confidence = score / 10
        elif score <= 3 or 'bearish' in trend:
            signal = 'sell'
            reason = f'江恩评分{score:.1f}，趋势向下，角度线弱势'
            target = support[-1] if support else self.current_price * 0.90
            stop_loss = self.current_price * 1.05
            confidence = (10 - score) / 10
        else:
            signal = 'hold'
            reason = f'江恩评分{score:.1f}，震荡整理'
            target = self.current_price * 1.05
            stop_loss = self.current_price * 0.95
            confidence = 0.5
        
        return {
            'signal': signal,
            'reason': reason,
            'target': round(target, 2),
            'stop_loss': round(stop_loss, 2),
            'confidence': round(confidence, 2),
        }


# 集成到评分系统
def gann_score(gann_data: Dict) -> float:
    """
    江恩理论评分 (0-10 分)
    """
    return gann_data.get('score', 5)


if __name__ == '__main__':
    print('江恩理论模块 - 测试')
    print('='*60)
    
    # 模拟数据
    test_data = [
        {'day': '2026-01-01', 'high': 10, 'low': 9, 'close': 9.5},
        {'day': '2026-01-02', 'high': 11, 'low': 9.5, 'close': 10.5},
        # ... 需要更多数据
    ]
    
    analyzer = GannAnalyzer()
    result = analyzer.analyze(test_data)
    print(f'江恩分析结果：{result}')
