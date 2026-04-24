"""
决策模块 - v2.0（完整版）

包含:
- 风险控制模块 ✅
- 标签生成模块 ✅
- 智能止盈止损 ✅
- 动态权重配置 ✅
- 多维度评分系统 ✅
"""

from .risk_control import RiskControlModule, RiskCheckResult
from .tag_generator import EnhancedTagGenerator
from .stop_loss_calculator import SmartStopLossCalculator, StopLossResult
from .weights import AdaptiveWeightManager, ScoringWeights
from .scoring import MultiDimensionScoring, ScoringResult

__all__ = [
    'RiskControlModule',
    'RiskCheckResult',
    'EnhancedTagGenerator',
    'SmartStopLossCalculator',
    'StopLossResult',
    'AdaptiveWeightManager',
    'ScoringWeights',
    'MultiDimensionScoring',
    'ScoringResult',
]

__version__ = '2.0.0'
