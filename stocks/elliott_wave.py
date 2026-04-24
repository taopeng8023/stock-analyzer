#!/usr/bin/env python3
"""
艾略特波浪理论策略模块

基于《艾略特波浪理论》- 拉尔夫·艾略特

核心原理:
1. 市场走势呈 5-3 波浪形态
2. 驱动浪 (1-3-5) + 调整浪 (A-B-C)
3. 第 3 浪通常是最强的
4. 波浪之间有斐波那契比例关系

用法:
    from elliott_wave import ElliottWaveAnalyzer
    analyzer = ElliottWaveAnalyzer()
    wave_data = analyzer.analyze(kline_data)
"""

import math
from typing import List, Dict, Optional, Tuple


class ElliottWaveAnalyzer:
    """艾略特波浪分析器"""
    
    # 斐波那契回调位
    FIB_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]
    
    def __init__(self):
        self.wave_count = 0
        self.current_wave = None
    
    def identify_wave_pattern(self, data: List[Dict]) -> Dict:
        """
        识别当前波浪形态
        
        Returns:
            {
                'pattern': str,  # 波浪形态
                'wave_stage': str,  # 当前阶段
                'confidence': float,  # 置信度
                'target': float,  # 目标位
                'support': float,  # 支撑位
            }
        """
        if len(data) < 50:
            return {'pattern': '数据不足', 'wave_stage': 'unknown', 'confidence': 0}
        
        # 识别高低点
        pivots = self._find_pivots(data, lookback=10)
        
        if len(pivots) < 5:
            return {'pattern': '形态不完整', 'wave_stage': 'unknown', 'confidence': 0}
        
        # 分析波浪结构
        wave_analysis = self._analyze_wave_structure(pivots, data)
        
        return wave_analysis
    
    def _find_pivots(self, data: List[Dict], lookback: int = 10) -> List[Dict]:
        """识别关键高低点"""
        pivots = []
        
        for i in range(lookback, len(data) - lookback):
            # 找高点
            is_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and data[j]['high'] >= data[i]['high']:
                    is_high = False
                    break
            
            if is_high:
                pivots.append({
                    'type': 'high',
                    'index': i,
                    'price': data[i]['high'],
                    'date': data[i]['day']
                })
            
            # 找低点
            is_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and data[j]['low'] <= data[i]['low']:
                    is_low = False
                    break
            
            if is_low:
                pivots.append({
                    'type': 'low',
                    'index': i,
                    'price': data[i]['low'],
                    'date': data[i]['day']
                })
        
        # 按索引排序
        pivots.sort(key=lambda x: x['index'])
        return pivots[-10:]  # 返回最近 10 个
    
    def _analyze_wave_structure(self, pivots: List[Dict], data: List[Dict]) -> Dict:
        """分析波浪结构"""
        if len(pivots) < 5:
            return {'pattern': '形态不完整', 'wave_stage': 'unknown', 'confidence': 0}
        
        # 简化分析：判断是上升趋势还是下降趋势
        recent_pivots = pivots[-5:]
        
        highs = [p['price'] for p in recent_pivots if p['type'] == 'high']
        lows = [p['price'] for p in recent_pivots if p['type'] == 'low']
        
        if not highs or not lows:
            return {'pattern': '无法识别', 'wave_stage': 'unknown', 'confidence': 0}
        
        # 判断趋势
        if len(highs) >= 2 and highs[-1] > highs[0]:
            trend = '上升'
        elif len(highs) >= 2 and highs[-1] < highs[0]:
            trend = '下降'
        else:
            trend = '震荡'
        
        # 斐波那契回调分析
        fib_analysis = self._fibonacci_analysis(pivots, data)
        
        # 波浪阶段判断
        wave_stage = self._determine_wave_stage(pivots, trend)
        
        # 目标位计算
        target = self._calculate_target(pivots, trend, fib_analysis)
        
        # 支撑位计算
        support = self._calculate_support(pivots, trend, fib_analysis)
        
        # 置信度
        confidence = self._calculate_confidence(pivots, trend, fib_analysis)
        
        return {
            'pattern': f'{trend}趋势',
            'wave_stage': wave_stage,
            'confidence': confidence,
            'target': target,
            'support': support,
            'fib_levels': fib_analysis,
        }
    
    def _fibonacci_analysis(self, pivots: List[Dict], data: List[Dict]) -> Dict:
        """斐波那契回调分析"""
        if len(pivots) < 2:
            return {}
        
        # 找到最近的显著高低点
        highs = [p for p in pivots if p['type'] == 'high']
        lows = [p for p in pivots if p['type'] == 'low']
        
        if not highs or not lows:
            return {}
        
        swing_high = max(highs, key=lambda x: x['price'])
        swing_low = min(lows, key=lambda x: x['price'])
        
        swing_range = swing_high['price'] - swing_low['price']
        current_price = data[-1]['close']
        
        fib_levels = {}
        for level in self.FIB_LEVELS:
            fib_price = swing_low['price'] + swing_range * level
            fib_levels[f'{level:.3f}'] = fib_price
        
        # 判断当前价格在哪个斐波那契位附近
        current_fib = (current_price - swing_low['price']) / swing_range if swing_range > 0 else 0
        
        return {
            'swing_high': swing_high['price'],
            'swing_low': swing_low['price'],
            'current_fib': current_fib,
            'levels': fib_levels,
        }
    
    def _determine_wave_stage(self, pivots: List[Dict], trend: str) -> str:
        """判断波浪阶段"""
        if len(pivots) < 3:
            return 'unknown'
        
        # 简化判断
        if trend == '上升':
            # 检查是否创新高
            if pivots[-1]['type'] == 'high' and pivots[-1]['price'] > pivots[-3]['price']:
                return '驱动浪 (可能第 3 浪)'
            elif pivots[-1]['type'] == 'low':
                return '调整浪 (可能第 2 浪或第 4 浪)'
            else:
                return '驱动浪延续'
        elif trend == '下降':
            if pivots[-1]['type'] == 'low' and pivots[-1]['price'] < pivots[-3]['price']:
                return '驱动浪下跌'
            elif pivots[-1]['type'] == 'high':
                return '调整浪反弹'
            else:
                return '下跌趋势延续'
        else:
            return '震荡整理'
    
    def _calculate_target(self, pivots: List[Dict], trend: str, fib: Dict) -> float:
        """计算目标位"""
        if not fib or 'swing_high' not in fib:
            return 0
        
        if trend == '上升':
            # 上升趋势目标：斐波那契扩展位
            return fib['swing_high'] * 1.1618  # 161.8% 扩展
        else:
            # 下降趋势目标：支撑位
            return fib['swing_low'] * 0.95
    
    def _calculate_support(self, pivots: List[Dict], trend: str, fib: Dict) -> float:
        """计算支撑位"""
        if not fib or 'swing_low' not in fib:
            return 0
        
        # 支撑位：斐波那契回调位
        if 'levels' in fib and '0.618' in fib['levels']:
            return fib['levels']['0.618']
        return fib['swing_low']
    
    def _calculate_confidence(self, pivots: List[Dict], trend: str, fib: Dict) -> float:
        """计算置信度"""
        confidence = 0.5  # 基础置信度
        
        # 波浪形态完整度
        if len(pivots) >= 5:
            confidence += 0.1
        if len(pivots) >= 7:
            confidence += 0.1
        
        # 斐波那契共振
        if fib and 'current_fib' in fib:
            current_fib = fib['current_fib']
            # 在关键斐波那契位附近
            for level in [0.382, 0.5, 0.618]:
                if abs(current_fib - level) < 0.05:
                    confidence += 0.1
                    break
        
        # 趋势一致性
        if trend in ['上升', '下降']:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def get_trading_signal(self, wave_data: Dict, current_price: float) -> Dict:
        """
        根据波浪分析获取交易信号
        
        Returns:
            {
                'signal': str,  # buy/sell/hold
                'reason': str,  # 理由
                'target': float,  # 目标位
                'stop_loss': float,  # 止损位
                'confidence': float,  # 置信度
            }
        """
        stage = wave_data.get('wave_stage', 'unknown')
        confidence = wave_data.get('confidence', 0)
        target = wave_data.get('target', 0)
        support = wave_data.get('support', 0)
        
        # 波浪理论交易逻辑
        if '驱动浪' in stage and confidence > 0.6:
            signal = 'buy'
            reason = f'驱动浪中，趋势强劲 ({stage})'
            stop_loss = support * 0.97 if support else current_price * 0.95
        elif '调整浪' in stage and confidence > 0.6:
            signal = 'hold'
            reason = f'调整浪中，等待驱动浪 ({stage})'
            stop_loss = support * 0.95 if support else current_price * 0.90
        elif '下跌' in stage and confidence > 0.6:
            signal = 'sell'
            reason = f'下跌驱动浪 ({stage})'
            stop_loss = current_price * 1.05
        else:
            signal = 'hold'
            reason = f'波浪形态不明确 ({stage})'
            stop_loss = current_price * 0.90
        
        return {
            'signal': signal,
            'reason': reason,
            'target': target if target else current_price * 1.10,
            'stop_loss': stop_loss,
            'confidence': confidence,
        }


# 集成到评分系统
def elliott_wave_score(wave_data: Dict) -> float:
    """
    波浪理论评分 (0-10 分)
    
    评分标准:
    - 驱动浪 + 高置信度：+8-10 分
    - 调整浪 + 中置信度：+5-7 分
    - 形态不明确：+3-5 分
    - 下跌驱动浪：0-3 分
    """
    stage = wave_data.get('wave_stage', 'unknown')
    confidence = wave_data.get('confidence', 0)
    
    base_score = 5
    
    # 波浪阶段评分
    if '驱动浪' in stage and '下跌' not in stage:
        base_score = 8
    elif '调整浪' in stage:
        base_score = 6
    elif '下跌' in stage:
        base_score = 2
    else:
        base_score = 5
    
    # 置信度调整
    score = base_score * confidence + 5 * (1 - confidence)
    
    return min(max(score, 0), 10)


if __name__ == '__main__':
    # 测试
    print('艾略特波浪理论模块 - 测试')
    print('='*60)
    
    # 模拟数据
    test_data = [
        {'day': '2026-01-01', 'high': 10, 'low': 9, 'close': 9.5},
        {'day': '2026-01-02', 'high': 11, 'low': 9.5, 'close': 10.5},
        {'day': '2026-01-03', 'high': 12, 'low': 10, 'close': 11.5},
        # ... 需要更多数据
    ]
    
    analyzer = ElliottWaveAnalyzer()
    result = analyzer.identify_wave_pattern(test_data)
    print(f'波浪分析结果：{result}')
