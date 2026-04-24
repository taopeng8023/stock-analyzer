"""
收益预测与成功概率计算模块
"""

import numpy as np
from datetime import datetime, timedelta


class ReturnPredictor:
    """收益预测器"""
    
    def __init__(self):
        # 基于历史数据的经验参数
        self.base_return_10d = 3.5  # 10 日基础收益预期 (%)
        self.volatility_factor = 0.6  # 波动调整因子
        
    def predict_10d_return(self, 
                          technical_score: int, 
                          fundamental_score: int,
                          money_flow_score: int,
                          trend_data: dict = None) -> dict:
        """
        预测 10 日收益
        
        参数:
            technical_score: 技术面评分 (0-100)
            fundamental_score: 基本面评分 (0-100)
            money_flow_score: 资金面评分 (0-100)
            trend_data: 趋势数据
        
        返回:
            {
                'expected_return': 预期收益 (%)
                'optimistic': 乐观情景 (%)
                'pessimistic': 悲观情景 (%)
                'confidence': 置信度
            }
        """
        # 综合评分
        total_score = (technical_score * 0.4 + 
                      fundamental_score * 0.35 + 
                      money_flow_score * 0.25)
        
        # 基础收益 + 评分加成
        base = self.base_return_10d
        score_bonus = (total_score - 50) * 0.3  # 每分 0.3% 加成
        
        # 趋势调整
        trend_bonus = 0
        if trend_data:
            if trend_data.get('trend') in ['强势上涨', '上涨']:
                trend_bonus = 3
            elif trend_data.get('trend') in ['下跌', '强势下跌']:
                trend_bonus = -3
        
        # 计算预期收益
        expected_return = base + score_bonus + trend_bonus
        
        # 情景分析
        volatility = max(5, abs(expected_return) * self.volatility_factor)
        optimistic = expected_return + volatility
        pessimistic = expected_return - volatility * 1.5
        
        # 置信度 (基于评分离散度)
        score_std = np.std([technical_score, fundamental_score, money_flow_score])
        confidence = max(40, min(85, 70 - score_std * 0.5 + (total_score - 50) * 0.3))
        
        return {
            'expected_return': round(expected_return, 1),
            'optimistic': round(optimistic, 1),
            'pessimistic': round(pessimistic, 1),
            'confidence': round(confidence, 1),
            'total_score': round(total_score, 1),
        }
    
    def calculate_success_probability(self,
                                     technical_score: int,
                                     fundamental_score: int,
                                     money_flow_score: int,
                                     volume_ratio: float = 1.0,
                                     northbound_inflow: bool = False) -> dict:
        """
        计算成功概率
        
        成功定义：10 日内获得正收益
        
        参数:
            technical_score: 技术面评分
            fundamental_score: 基本面评分
            money_flow_score: 资金面评分
            volume_ratio: 成交量比率
            northbound_inflow: 北向资金是否流入
        
        返回:
            {
                'probability': 成功概率 (%)
                'level': 概率等级
                'factors': 影响因素
            }
        """
        # 基础概率
        base_prob = 50
        
        # 综合评分加成
        total_score = (technical_score * 0.4 + 
                      fundamental_score * 0.35 + 
                      money_flow_score * 0.25)
        score_bonus = (total_score - 50) * 0.6  # 每分 0.6% 概率加成
        
        # 成交量加成
        volume_bonus = 0
        if volume_ratio > 1.5:
            volume_bonus = 8
        elif volume_ratio > 1.2:
            volume_bonus = 5
        elif volume_ratio < 0.7:
            volume_bonus = -5
        
        # 北向资金加成
        northbound_bonus = 5 if northbound_inflow else 0
        
        # 计算最终概率
        probability = base_prob + score_bonus + volume_bonus + northbound_bonus
        
        # 限制范围
        probability = max(20, min(85, probability))
        
        # 概率等级
        if probability >= 75:
            level = '很高'
            icon = '✓✓✓'
        elif probability >= 65:
            level = '较高'
            icon = '✓✓'
        elif probability >= 55:
            level = '中等'
            icon = '✓'
        elif probability >= 45:
            level = '偏低'
            icon = '✗'
        else:
            level = '很低'
            icon = '✗✗'
        
        # 影响因素
        factors = []
        if technical_score >= 70:
            factors.append('技术面强势')
        if fundamental_score >= 70:
            factors.append('基本面良好')
        if money_flow_score >= 70:
            factors.append('资金流入')
        if volume_ratio > 1.2:
            factors.append('成交量放大')
        if northbound_inflow:
            factors.append('北向资金流入')
        
        if not factors:
            factors.append('无明显优势')
        
        return {
            'probability': round(probability, 1),
            'level': level,
            'icon': icon,
            'factors': factors,
        }
    
    def generate_target_price(self, 
                             current_price: float,
                             expected_return: float) -> dict:
        """
        生成目标价位
        
        参数:
            current_price: 当前股价
            expected_return: 预期收益率
        
        返回:
            {
                'target_price': 目标价
                'stop_loss': 止损价
                'upside': 上涨空间
                'downside': 下跌风险
            }
        """
        # 目标价
        target_price = current_price * (1 + expected_return / 100)
        
        # 止损价 (8% 止损)
        stop_loss = current_price * 0.92
        
        # 上涨/下跌空间
        upside = expected_return
        downside = -8.0
        
        # 盈亏比
        risk_reward = abs(expected_return) / 8.0 if expected_return > 0 else 0
        
        return {
            'target_price': round(target_price, 2),
            'stop_loss': round(stop_loss, 2),
            'upside': round(upside, 1),
            'downside': round(downside, 1),
            'risk_reward': round(risk_reward, 2),
        }


# 测试用
if __name__ == "__main__":
    predictor = ReturnPredictor()
    
    # 测试预测
    result = predictor.predict_10d_return(
        technical_score=75,
        fundamental_score=70,
        money_flow_score=65,
        trend_data={'trend': '上涨'}
    )
    print(f"10 日预期收益：{result['expected_return']}%")
    print(f"乐观：{result['optimistic']}%, 悲观：{result['pessimistic']}%")
    print(f"置信度：{result['confidence']}%")
    
    # 测试成功概率
    prob = predictor.calculate_success_probability(
        technical_score=75,
        fundamental_score=70,
        money_flow_score=65,
        volume_ratio=1.3,
        northbound_inflow=True
    )
    print(f"\n成功概率：{prob['probability']}% ({prob['level']})")
    print(f"因素：{prob['factors']}")
