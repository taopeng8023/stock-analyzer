#!/usr/bin/env python3
"""
多维度评分系统 - v1.0

功能:
- 基本面评分（30%）
- 技术面评分（25%）
- 资金流评分（25%）
- 市场情绪评分（10%）
- 风险评估（10%）
- 加权总分计算

用法:
    from decision.scoring import MultiDimensionScoring
    
    scoring = MultiDimensionScoring()
    result = scoring.calculate_score(stock_data, fundamental, technical, capital_flow)
"""

from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

try:
    from .weights import ScoringWeights, AdaptiveWeightManager
except ImportError:
    from weights import ScoringWeights, AdaptiveWeightManager


@dataclass
class ScoringResult:
    """评分结果"""
    total_score: float                # 总分（0-100）
    subscores: Dict[str, float]       # 各维度评分
    weights: Dict[str, float]         # 使用的权重
    rating: str                       # 评级
    check_time: str                   # 评分时间


class MultiDimensionScoring:
    """多维度评分系统"""
    
    # 评分阈值配置
    THRESHOLDS = {
        'excellent': 90,    # 优秀
        'good': 80,         # 良好
        'fair': 70,         # 一般
        'poor': 60,         # 较差
    }
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        """
        初始化评分系统
        
        Args:
            weights: 权重配置（可选，默认使用均衡型）
        """
        self.weights = weights or ScoringWeights()
        self.weight_manager = AdaptiveWeightManager()
    
    def calculate_score(self, stock: Dict,
                        fundamental_data: Optional[Dict] = None,
                        technical_data: Optional[Dict] = None,
                        capital_flow_data: Optional[Dict] = None,
                        sentiment_data: Optional[Dict] = None) -> ScoringResult:
        """
        计算多维度综合评分
        
        Args:
            stock: 股票基础数据
            fundamental_data: 基本面数据（可选）
            technical_data: 技术面数据（可选）
            capital_flow_data: 资金流数据（可选）
            sentiment_data: 市场情绪数据（可选）
        
        Returns:
            ScoringResult: 评分结果
        """
        # 1. 各维度评分
        fundamental_score = self._score_fundamental(stock, fundamental_data)
        technical_score = self._score_technical(stock, technical_data)
        capital_flow_score = self._score_capital_flow(stock, capital_flow_data)
        sentiment_score = self._score_sentiment(stock, sentiment_data)
        risk_score = self._score_risk(stock, fundamental_data)
        
        # 2. 加权总分
        total_score = (
            fundamental_score * self.weights.fundamental +
            technical_score * self.weights.technical +
            capital_flow_score * self.weights.capital_flow +
            sentiment_score * self.weights.sentiment +
            risk_score * self.weights.risk
        )
        
        # 3. 确定评级
        rating = self._determine_rating(total_score)
        
        return ScoringResult(
            total_score=round(total_score, 2),
            subscores={
                'fundamental': fundamental_score,
                'technical': technical_score,
                'capital_flow': capital_flow_score,
                'sentiment': sentiment_score,
                'risk': risk_score,
            },
            weights=self.weights.to_dict(),
            rating=rating,
            check_time=datetime.now().isoformat()
        )
    
    def _score_fundamental(self, stock: Dict, 
                           fundamental_data: Optional[Dict]) -> float:
        """
        基本面评分（0-100）
        
        评估维度:
        - 估值（PE/PB）30%
        - 盈利能力（ROE）30%
        - 成长性（营收增长）25%
        - 财务健康（负债率）15%
        """
        if not fundamental_data:
            return 50.0  # 默认中等评分
        
        score = 0
        
        # 1. 估值评分（30 分）
        pe_score = self._score_pe(fundamental_data.get('pe_ratio', 0))
        pb_score = self._score_pb(fundamental_data.get('pb_ratio', 0))
        score += (pe_score + pb_score) / 2 * 0.30
        
        # 2. 盈利能力评分（30 分）
        roe_score = self._score_roe(fundamental_data.get('roe', 0))
        score += roe_score * 0.30
        
        # 3. 成长性评分（25 分）
        growth_score = self._score_growth(fundamental_data.get('revenue_growth', 0))
        score += growth_score * 0.25
        
        # 4. 财务健康评分（15 分）
        health_score = self._score_health(fundamental_data.get('debt_to_assets', 0))
        score += health_score * 0.15
        
        return min(100, max(0, score))
    
    def _score_technical(self, stock: Dict, 
                         technical_data: Optional[Dict]) -> float:
        """
        技术面评分（0-100）
        
        评估维度:
        - 趋势（均线）40%
        - 动量（MACD/RSI）35%
        - 成交量 25%
        """
        if not technical_data:
            # 使用涨跌幅作为简单技术指标
            change_pct = stock.get('change_pct', 0)
            if 2 <= change_pct <= 7:
                return 80.0
            elif 0 <= change_pct < 2:
                return 65.0
            elif change_pct > 10:
                return 70.0  # 涨停可能回调
            else:
                return 40.0
        
        score = 0
        
        # 1. 趋势评分（40 分）
        trend_score = self._score_trend(technical_data)
        score += trend_score * 0.40
        
        # 2. 动量评分（35 分）
        momentum_score = self._score_momentum(technical_data)
        score += momentum_score * 0.35
        
        # 3. 成交量评分（25 分）
        volume_score = self._score_volume(technical_data)
        score += volume_score * 0.25
        
        return min(100, max(0, score))
    
    def _score_capital_flow(self, stock: Dict, 
                            capital_flow_data: Optional[Dict]) -> float:
        """
        资金流评分（0-100）
        
        评估维度:
        - 主力净流入 50%
        - 成交额 30%
        - 资金流向持续性 20%
        """
        if not capital_flow_data:
            # 使用成交额作为简单指标
            turnover = stock.get('turnover', 0)
            if turnover > 5000000000:  # >50 亿
                return 85.0
            elif turnover > 1000000000:  # >10 亿
                return 70.0
            elif turnover > 100000000:  # >1 亿
                return 55.0
            else:
                return 40.0
        
        score = 0
        
        # 1. 主力净流入评分（50 分）
        main_flow_score = self._score_main_flow(capital_flow_data)
        score += main_flow_score * 0.50
        
        # 2. 成交额评分（30 分）
        turnover_score = self._score_turnover(capital_flow_data)
        score += turnover_score * 0.30
        
        # 3. 持续性评分（20 分）
        continuity_score = self._score_continuity(capital_flow_data)
        score += continuity_score * 0.20
        
        return min(100, max(0, score))
    
    def _score_sentiment(self, stock: Dict, 
                         sentiment_data: Optional[Dict]) -> float:
        """
        市场情绪评分（0-100）
        
        评估维度:
        - 新闻情感 50%
        - 社交媒体热度 30%
        - 分析师评级 20%
        """
        if not sentiment_data:
            return 60.0  # 默认中等
        
        score = 0
        
        # 1. 新闻情感评分（50 分）
        news_score = self._score_news_sentiment(sentiment_data)
        score += news_score * 0.50
        
        # 2. 社交媒体评分（30 分）
        social_score = self._score_social_sentiment(sentiment_data)
        score += social_score * 0.30
        
        # 3. 分析师评级评分（20 分）
        analyst_score = self._score_analyst_rating(sentiment_data)
        score += analyst_score * 0.20
        
        return min(100, max(0, score))
    
    def _score_risk(self, stock: Dict, 
                    fundamental_data: Optional[Dict]) -> float:
        """
        风险评估（0-100，分数越高风险越低）
        
        评估维度:
        - ST 风险 30%
        - 高位风险 25%
        - 估值风险 25%
        - 流动性风险 20%
        """
        score = 100.0  # 从 100 分开始扣
        
        # 1. ST 风险（扣 30 分）
        if 'ST' in stock.get('name', '') or '*' in stock.get('name', ''):
            score -= 30
        
        # 2. 高位风险（扣 25 分）
        change_pct = stock.get('change_pct', 0)
        if change_pct > 50:
            score -= 25
        elif change_pct > 30:
            score -= 15
        
        # 3. 估值风险（扣 25 分）
        if fundamental_data:
            pe = fundamental_data.get('pe_ratio', 0)
            if pe > 100:
                score -= 20
            elif pe > 50:
                score -= 10
            
            if pe < 0:  # 亏损
                score -= 15
        
        # 4. 流动性风险（扣 20 分）
        turnover = stock.get('turnover', 0)
        if turnover < 100000000:  # <1 亿
            score -= 20
        elif turnover < 500000000:  # <5 亿
            score -= 10
        
        return min(100, max(0, score))
    
    # ========== 基本面评分辅助方法 ==========
    
    def _score_pe(self, pe_ratio: float) -> float:
        """PE 评分"""
        if pe_ratio <= 0:
            return 30.0  # 亏损
        elif pe_ratio < 15:
            return 90.0  # 低估
        elif pe_ratio < 30:
            return 75.0  # 合理
        elif pe_ratio < 50:
            return 50.0  # 偏高
        else:
            return 25.0  # 高估
    
    def _score_pb(self, pb_ratio: float) -> float:
        """PB 评分"""
        if pb_ratio <= 0:
            return 30.0
        elif pb_ratio < 2:
            return 85.0
        elif pb_ratio < 5:
            return 70.0
        elif pb_ratio < 10:
            return 50.0
        else:
            return 25.0
    
    def _score_roe(self, roe: float) -> float:
        """ROE 评分"""
        if roe < 0:
            return 20.0
        elif roe < 10:
            return 50.0
        elif roe < 15:
            return 70.0
        elif roe < 20:
            return 85.0
        else:
            return 100.0
    
    def _score_growth(self, growth_rate: float) -> float:
        """成长性评分"""
        if growth_rate < -20:
            return 20.0
        elif growth_rate < 0:
            return 40.0
        elif growth_rate < 10:
            return 60.0
        elif growth_rate < 30:
            return 80.0
        else:
            return 100.0
    
    def _score_health(self, debt_ratio: float) -> float:
        """财务健康评分"""
        if debt_ratio < 30:
            return 90.0
        elif debt_ratio < 50:
            return 75.0
        elif debt_ratio < 70:
            return 50.0
        else:
            return 25.0
    
    # ========== 技术面评分辅助方法 ==========
    
    def _score_trend(self, technical_data: Dict) -> float:
        """趋势评分"""
        ma5 = technical_data.get('ma5', 0)
        ma20 = technical_data.get('ma20', 0)
        ma60 = technical_data.get('ma60', 0)
        
        if ma5 > ma20 > ma60:
            return 90.0  # 多头排列
        elif ma5 > ma20:
            return 70.0
        elif ma5 < ma20 < ma60:
            return 20.0  # 空头排列
        else:
            return 50.0
    
    def _score_momentum(self, technical_data: Dict) -> float:
        """动量评分"""
        rsi = technical_data.get('rsi', 50)
        macd_golden = technical_data.get('macd_golden_cross', False)
        macd_dead = technical_data.get('macd_dead_cross', False)
        
        score = 50.0
        
        # RSI 评分
        if 50 <= rsi <= 70:
            score += 20
        elif rsi > 70:
            score -= 10  # 超买
        
        # MACD 评分
        if macd_golden:
            score += 20
        elif macd_dead:
            score -= 20
        
        return min(100, max(0, score))
    
    def _score_volume(self, technical_data: Dict) -> float:
        """成交量评分"""
        volume_ratio = technical_data.get('volume_ratio', 1)
        
        if volume_ratio > 2:
            return 85.0  # 放量
        elif volume_ratio > 1.5:
            return 70.0
        elif volume_ratio > 0.8:
            return 50.0
        else:
            return 30.0  # 缩量
    
    # ========== 资金流评分辅助方法 ==========
    
    def _score_main_flow(self, capital_flow_data: Dict) -> float:
        """主力净流入评分"""
        main_flow = capital_flow_data.get('main_flow', 0)  # 万
        
        if main_flow > 10000:  # >1 亿
            return 95.0
        elif main_flow > 5000:  # >5000 万
            return 80.0
        elif main_flow > 1000:  # >1000 万
            return 65.0
        elif main_flow > 0:
            return 50.0
        else:
            return 30.0
    
    def _score_turnover(self, capital_flow_data: Dict) -> float:
        """成交额评分"""
        turnover = capital_flow_data.get('turnover', 0)
        
        if turnover > 5000000000:  # >50 亿
            return 95.0
        elif turnover > 1000000000:  # >10 亿
            return 80.0
        elif turnover > 100000000:  # >1 亿
            return 65.0
        else:
            return 40.0
    
    def _score_continuity(self, capital_flow_data: Dict) -> float:
        """持续性评分"""
        flow_days = capital_flow_data.get('continuous_inflow_days', 0)
        
        if flow_days >= 5:
            return 95.0
        elif flow_days >= 3:
            return 80.0
        elif flow_days >= 1:
            return 65.0
        else:
            return 40.0
    
    # ========== 情绪评分辅助方法 ==========
    
    def _score_news_sentiment(self, sentiment_data: Dict) -> float:
        """新闻情感评分"""
        sentiment_score = sentiment_data.get('news_sentiment_score', 0)
        
        if sentiment_score > 0.5:
            return 90.0
        elif sentiment_score > 0.2:
            return 75.0
        elif sentiment_score > -0.2:
            return 50.0
        elif sentiment_score > -0.5:
            return 30.0
        else:
            return 15.0
    
    def _score_social_sentiment(self, sentiment_data: Dict) -> float:
        """社交媒体评分"""
        social_score = sentiment_data.get('social_sentiment', 0)
        
        if social_score > 0.7:
            return 90.0
        elif social_score > 0.3:
            return 70.0
        elif social_score > -0.3:
            return 50.0
        else:
            return 30.0
    
    def _score_analyst_rating(self, sentiment_data: Dict) -> float:
        """分析师评级评分"""
        rating = sentiment_data.get('analyst_rating', 3)  # 1-5，5 为买入
        
        if rating >= 4.5:
            return 95.0
        elif rating >= 4:
            return 80.0
        elif rating >= 3:
            return 60.0
        elif rating >= 2:
            return 40.0
        else:
            return 20.0
    
    # ========== 评级方法 ==========
    
    def _determine_rating(self, total_score: float) -> str:
        """
        确定评级
        
        Args:
            total_score: 总分
        
        Returns:
            str: 评级
        """
        if total_score >= self.THRESHOLDS['excellent']:
            return '强烈推荐'
        elif total_score >= self.THRESHOLDS['good']:
            return '推荐'
        elif total_score >= self.THRESHOLDS['fair']:
            return '关注'
        elif total_score >= self.THRESHOLDS['poor']:
            return '观望'
        else:
            return '回避'


# 测试
if __name__ == '__main__':
    scoring = MultiDimensionScoring()
    
    # 测试数据
    test_stock = {
        'code': '600519',
        'name': '贵州茅台',
        'price': 1800.00,
        'change_pct': 2.5,
        'turnover': 5000000000,
    }
    
    test_fundamental = {
        'pe_ratio': 35.5,
        'pb_ratio': 8.2,
        'roe': 25.3,
        'revenue_growth': 15.5,
        'debt_to_assets': 35.0,
    }
    
    test_technical = {
        'ma5': 1800,
        'ma20': 1750,
        'ma60': 1700,
        'rsi': 65,
        'macd_golden_cross': True,
        'volume_ratio': 1.5,
    }
    
    test_capital_flow = {
        'main_flow': 15000,  # 1.5 亿
        'turnover': 5000000000,
        'continuous_inflow_days': 3,
    }
    
    print("="*80)
    print("📊 多维度评分系统测试")
    print("="*80)
    
    result = scoring.calculate_score(
        test_stock,
        fundamental_data=test_fundamental,
        technical_data=test_technical,
        capital_flow_data=test_capital_flow,
    )
    
    print(f"\n{test_stock['code']} {test_stock['name']}:")
    print(f"\n总评分：{result.total_score:.1f}")
    print(f"评级：{result.rating}")
    print(f"\n各维度评分:")
    for dim, score in result.subscores.items():
        print(f"  {dim}: {score:.1f}")
    
    print(f"\n权重配置:")
    for dim, weight in result.weights.items():
        print(f"  {dim}: {weight:.1%}")
