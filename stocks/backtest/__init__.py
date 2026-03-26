"""
回测模块 - v1.0

包含:
- 回测引擎
- 回测分析器
- 绩效评估
- 报告生成
"""

from .engine import BacktestEngine, BacktestResult, Trade, Position
from .analyzer import BacktestAnalyzer

__all__ = [
    'BacktestEngine',
    'BacktestResult',
    'Trade',
    'Position',
    'BacktestAnalyzer',
]

__version__ = '1.0.0'
