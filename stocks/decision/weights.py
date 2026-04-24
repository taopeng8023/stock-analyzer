#!/usr/bin/env python3
"""
动态权重配置模块 - v1.0

功能:
- 根据市场状态调整权重
- 根据风险偏好调整权重
- 根据行业特性调整权重
- 权重配置管理

用法:
    from decision.weights import AdaptiveWeightManager
    
    manager = AdaptiveWeightManager()
    weights = manager.get_weights_by_market('bull')
    weights = manager.get_weights_by_risk_profile('aggressive')
"""

from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime


@dataclass
class ScoringWeights:
    """评分权重配置"""
    fundamental: float = 0.30       # 基本面权重
    technical: float = 0.25         # 技术面权重
    capital_flow: float = 0.25      # 资金流权重
    sentiment: float = 0.10         # 市场情绪权重
    risk: float = 0.10              # 风险评估权重
    
    def validate(self) -> bool:
        """验证权重和是否为 1"""
        total = (self.fundamental + self.technical + 
                 self.capital_flow + self.sentiment + self.risk)
        return abs(total - 1.0) < 0.001
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            'fundamental': self.fundamental,
            'technical': self.technical,
            'capital_flow': self.capital_flow,
            'sentiment': self.sentiment,
            'risk': self.risk,
        }


class AdaptiveWeightManager:
    """自适应权重管理"""
    
    # 默认权重（均衡型）
    DEFAULT_WEIGHTS = ScoringWeights(
        fundamental=0.30,
        technical=0.25,
        capital_flow=0.25,
        sentiment=0.10,
        risk=0.10
    )
    
    # 市场状态权重配置
    MARKET_WEIGHTS = {
        'bull': ScoringWeights(        # 牛市
            fundamental=0.20,
            technical=0.35,
            capital_flow=0.30,
            sentiment=0.10,
            risk=0.05
        ),
        'bear': ScoringWeights(        # 熊市
            fundamental=0.40,
            technical=0.15,
            capital_flow=0.20,
            sentiment=0.05,
            risk=0.20
        ),
        'volatile': ScoringWeights(    # 震荡市
            fundamental=0.30,
            technical=0.25,
            capital_flow=0.25,
            sentiment=0.10,
            risk=0.10
        ),
    }
    
    # 风险偏好权重配置
    RISK_PROFILE_WEIGHTS = {
        'aggressive': ScoringWeights(   # 激进型
            fundamental=0.15,
            technical=0.35,
            capital_flow=0.35,
            sentiment=0.10,
            risk=0.05
        ),
        'balanced': ScoringWeights(     # 稳健型
            fundamental=0.30,
            technical=0.25,
            capital_flow=0.25,
            sentiment=0.10,
            risk=0.10
        ),
        'conservative': ScoringWeights( # 保守型
            fundamental=0.40,
            technical=0.15,
            capital_flow=0.15,
            sentiment=0.05,
            risk=0.25
        ),
    }
    
    # 行业特性权重配置
    INDUSTRY_WEIGHTS = {
        'technology': ScoringWeights(   # 科技股
            fundamental=0.25,
            technical=0.30,
            capital_flow=0.25,
            sentiment=0.15,
            risk=0.05
        ),
        'finance': ScoringWeights(      # 金融股
            fundamental=0.40,
            technical=0.20,
            capital_flow=0.20,
            sentiment=0.05,
            risk=0.15
        ),
        'consumer': ScoringWeights(     # 消费股
            fundamental=0.35,
            technical=0.20,
            capital_flow=0.25,
            sentiment=0.10,
            risk=0.10
        ),
        'energy': ScoringWeights(       # 能源股
            fundamental=0.30,
            technical=0.25,
            capital_flow=0.25,
            sentiment=0.05,
            risk=0.15
        ),
    }
    
    def get_weights_by_market(self, market_condition: str) -> ScoringWeights:
        """
        根据市场状态获取权重
        
        Args:
            market_condition: 市场状态（bull/bear/volatile）
        
        Returns:
            ScoringWeights: 权重配置
        """
        return self.MARKET_WEIGHTS.get(market_condition, self.DEFAULT_WEIGHTS)
    
    def get_weights_by_risk_profile(self, profile: str) -> ScoringWeights:
        """
        根据风险偏好获取权重
        
        Args:
            profile: 风险偏好（aggressive/balanced/conservative）
        
        Returns:
            ScoringWeights: 权重配置
        """
        return self.RISK_PROFILE_WEIGHTS.get(profile, self.DEFAULT_WEIGHTS)
    
    def get_weights_by_industry(self, industry: str) -> ScoringWeights:
        """
        根据行业获取权重
        
        Args:
            industry: 行业名称
        
        Returns:
            ScoringWeights: 权重配置
        """
        industry_lower = industry.lower()
        
        # 行业匹配
        if any(kw in industry_lower for kw in ['科技', '芯片', '半导体', '电子', 'computer', 'tech']):
            return self.INDUSTRY_WEIGHTS['technology']
        elif any(kw in industry_lower for kw in ['金融', '银行', '保险', '券商', 'finance', 'bank']):
            return self.INDUSTRY_WEIGHTS['finance']
        elif any(kw in industry_lower for kw in ['消费', '食品', '饮料', '白酒', 'consumer', 'food']):
            return self.INDUSTRY_WEIGHTS['consumer']
        elif any(kw in industry_lower for kw in ['能源', '石油', '煤炭', 'energy', 'oil', 'coal']):
            return self.INDUSTRY_WEIGHTS['energy']
        else:
            return self.DEFAULT_WEIGHTS
    
    def get_custom_weights(self, **kwargs) -> ScoringWeights:
        """
        获取自定义权重
        
        Args:
            **kwargs: 权重参数
        
        Returns:
            ScoringWeights: 权重配置
        """
        weights = ScoringWeights(
            fundamental=kwargs.get('fundamental', self.DEFAULT_WEIGHTS.fundamental),
            technical=kwargs.get('technical', self.DEFAULT_WEIGHTS.technical),
            capital_flow=kwargs.get('capital_flow', self.DEFAULT_WEIGHTS.capital_flow),
            sentiment=kwargs.get('sentiment', self.DEFAULT_WEIGHTS.sentiment),
            risk=kwargs.get('risk', self.DEFAULT_WEIGHTS.risk),
        )
        
        # 验证权重和
        if not weights.validate():
            # 归一化
            total = (weights.fundamental + weights.technical + 
                     weights.capital_flow + weights.sentiment + weights.risk)
            if total > 0:
                weights.fundamental /= total
                weights.technical /= total
                weights.capital_flow /= total
                weights.sentiment /= total
                weights.risk /= total
        
        return weights
    
    def blend_weights(self, weights_list: list, 
                      blend_factors: Optional[list] = None) -> ScoringWeights:
        """
        混合多个权重配置
        
        Args:
            weights_list: 权重配置列表
            blend_factors: 混合因子列表（权重），默认平均
        
        Returns:
            ScoringWeights: 混合后的权重
        """
        if not weights_list:
            return self.DEFAULT_WEIGHTS
        
        if blend_factors is None:
            blend_factors = [1.0 / len(weights_list)] * len(weights_list)
        
        # 归一化混合因子
        total_factor = sum(blend_factors)
        blend_factors = [f / total_factor for f in blend_factors]
        
        # 计算混合权重
        fundamental = sum(w.fundamental * f for w, f in zip(weights_list, blend_factors))
        technical = sum(w.technical * f for w, f in zip(weights_list, blend_factors))
        capital_flow = sum(w.capital_flow * f for w, f in zip(weights_list, blend_factors))
        sentiment = sum(w.sentiment * f for w, f in zip(weights_list, blend_factors))
        risk = sum(w.risk * f for w, f in zip(weights_list, blend_factors))
        
        return ScoringWeights(
            fundamental=fundamental,
            technical=technical,
            capital_flow=capital_flow,
            sentiment=sentiment,
            risk=risk
        )
    
    def detect_market_condition(self, market_data: Dict) -> str:
        """
        检测市场状态
        
        Args:
            market_data: 市场数据（包含 index_change, volatility 等）
        
        Returns:
            str: 市场状态（bull/bear/volatile）
        """
        index_change = market_data.get('index_change', 0)  # 指数涨跌幅
        volatility = market_data.get('volatility', 0)      # 波动率
        
        # 牛市：指数上涨>20%
        if index_change > 20:
            return 'bull'
        
        # 熊市：指数下跌>20%
        if index_change < -20:
            return 'bear'
        
        # 震荡市：波动率高
        if volatility > 0.25:
            return 'volatile'
        
        # 默认震荡市
        return 'volatile'
    
    def get_weights_summary(self, weights: ScoringWeights) -> str:
        """
        获取权重摘要
        
        Args:
            weights: 权重配置
        
        Returns:
            str: 权重摘要
        """
        lines = [
            "📊 权重配置",
            "="*50,
            f"基本面：{weights.fundamental:.1%}",
            f"技术面：{weights.technical:.1%}",
            f"资金流：{weights.capital_flow:.1%}",
            f"市场情绪：{weights.sentiment:.1%}",
            f"风险：{weights.risk:.1%}",
            "="*50,
        ]
        
        # 判断类型
        if weights.fundamental > 0.35:
            style = "📈 价值型"
        elif weights.technical > 0.30:
            style = "📊 技术型"
        elif weights.capital_flow > 0.30:
            style = "💰 资金型"
        elif weights.risk > 0.20:
            style = "🛡️ 防御型"
        else:
            style = "⚖️ 均衡型"
        
        lines.append(f"风格：{style}")
        
        return "\n".join(lines)


# 测试
if __name__ == '__main__':
    manager = AdaptiveWeightManager()
    
    print("="*80)
    print("⚖️ 动态权重配置管理器测试")
    print("="*80)
    
    # 测试 1: 市场状态权重
    print("\n[测试 1] 市场状态权重")
    for market in ['bull', 'bear', 'volatile']:
        weights = manager.get_weights_by_market(market)
        print(f"\n{market.upper()}:")
        print(manager.get_weights_summary(weights))
    
    # 测试 2: 风险偏好权重
    print("\n\n[测试 2] 风险偏好权重")
    for profile in ['aggressive', 'balanced', 'conservative']:
        weights = manager.get_weights_by_risk_profile(profile)
        print(f"\n{profile.upper()}:")
        print(manager.get_weights_summary(weights))
    
    # 测试 3: 行业权重
    print("\n\n[测试 3] 行业权重")
    for industry in ['科技', '金融', '消费', '能源', '其他']:
        weights = manager.get_weights_by_industry(industry)
        print(f"\n{industry}:")
        print(manager.get_weights_summary(weights))
    
    # 测试 4: 自定义权重
    print("\n\n[测试 4] 自定义权重")
    weights = manager.get_custom_weights(
        fundamental=0.40,
        technical=0.30,
        capital_flow=0.20,
        sentiment=0.05,
        risk=0.05
    )
    print(manager.get_weights_summary(weights))
    
    # 测试 5: 混合权重
    print("\n\n[测试 5] 混合权重")
    weights_list = [
        manager.get_weights_by_market('bull'),
        manager.get_weights_by_risk_profile('aggressive'),
    ]
    blended = manager.blend_weights(weights_list)
    print("混合（牛市 + 激进）:")
    print(manager.get_weights_summary(blended))
