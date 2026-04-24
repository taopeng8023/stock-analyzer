#!/usr/bin/env python3
"""
v8.0-Financial-Enhanced 基准版配置
作为后续优化的对比基准

十轮回测验证 (1200 次决策) 最优配置
"""

# ============================================================================
# v8.0 基准版核心指标
# ============================================================================

BASELINE_VERSION = 'v8.0-Financial-Enhanced'
BASELINE_DATE = '2026-03-21'

# 回测验证数据
BASELINE_METRICS = {
    # 95 只股票池表现
    'win_rate': 48.3,              # 胜率
    'total_return': 148.84,        # 总收益 (%)
    'avg_return': 1.24,            # 平均收益/次 (%)
    'stop_ratio': 0.51,            # 止盈/止损比
    
    # 综合统计 (10 轮 1200 次决策)
    'total_decisions': 1200,       # 总决策数
    'overall_win_rate': 49.0,      # 综合胜率 (%)
    'total_return_all': 1347.93,   # 总收益率 (%)
    'avg_return_all': 1.12,        # 综合平均收益/次 (%)
}

# 相对提升
BASELINE_IMPROVEMENT = {
    'vs_v6_1_ml': 2.35,            # 相对 v6.1-ML 提升 +235%
    'vs_v7_0': 0.02,               # 相对 v7.0 提升 +2%
    'vs_v9_0': -0.03,              # 相对 v9.0 提升 -3% (v9.0 下降)
}

# ============================================================================
# v8.0 模型配置 (15 个)
# ============================================================================

MODEL_COUNT = 15

MODEL_WEIGHTS = {
    # 经典定价模型 (4 个)
    'capm': 0.12,                  # CAPM
    'fama_french_3': 0.10,         # Fama-French 三因子
    'carhart_4': 0.13,             # Carhart 四因子
    'fama_french_5': 0.10,         # Fama-French 五因子
    
    # 资产配置 (1 个)
    'black_litterman': 0.15,       # Black-Litterman
    
    # 风险指标 (5 个)
    'risk_metrics': 0.10,          # Sharpe/Sortino/MaxDD/VaR
    'cvar': 0.10,                  # CVaR
    
    # 技术指标 (3 个)
    'technical': 0.10,             # MACD/RSI/Bollinger
    
    # ML 模型 (1 个)
    'random_forest': 0.10,         # Random Forest (29 维特征)
}

# ============================================================================
# 评级阈值
# ============================================================================

RATING_THRESHOLDS = {
    'strong_buy': {'min_score': 80, 'confidence': 90},
    'buy': {'min_score': 65, 'confidence': 75},
    'cautious_buy': {'min_score': 50, 'confidence': 60},
    'hold': {'min_score': 0, 'confidence': 45},
}

# ============================================================================
# 止盈止损配置 (v6.2 优化)
# ============================================================================

STOP_PROFIT_LOSS_CONFIG = {
    'high_volatility': {
        'stop_profit_pct': 0.12,
        'stop_loss_pct': 0.05,
        'trailing_stop': True,
        'trailing_pct': 0.05,
    },
    'medium_volatility': {
        'stop_profit_pct': 0.18,
        'stop_loss_pct': 0.07,
        'trailing_stop': True,
        'trailing_pct': 0.06,
    },
    'low_volatility': {
        'stop_profit_pct': 0.22,
        'stop_loss_pct': 0.08,
        'trailing_stop': True,
        'trailing_pct': 0.08,
    },
    'negative': {
        'stop_profit_pct': 0.25,
        'stop_loss_pct': 0.10,
        'trailing_stop': False,
        'trailing_pct': 0.10,
    }
}

# ============================================================================
# 黑名单/观察名单
# ============================================================================

BLACKLIST_SYMBOLS = {
    '601138',  # 工业富联
    '301205',  # 联特科技
    '002460',  # 赣锋锂业
    '688629',  # 华丰科技
}

WATCHLIST_SYMBOLS = {
    '002475',  # 立讯精密
    '300751',  # 迈为股份
    '300342',  # 天银机电
    '603026',  # 石大胜华
    '000862',  # 银星能源
    '300040',  # 九洲集团
}

# ============================================================================
# 使用方法
# ============================================================================

"""
# 作为基准对比
from baseline_v8 import BASELINE_METRICS

current_avg_return = 1.30  # 当前版本平均收益
baseline_avg_return = BASELINE_METRICS['avg_return']

improvement = (current_avg_return / baseline_avg_return - 1) * 100
print(f"相对 v8.0 基准提升：{improvement:+.1f}%")

# 判断是否显著优于基准
if improvement > 5:
    print("✅ 显著优于基准")
elif improvement > 0:
    print("✅ 优于基准")
else:
    print("⚠️ 未超越基准")
"""

# ============================================================================
# 文档
# ============================================================================

BASELINE_DOCUMENTATION = '''
v8.0-Financial-Enhanced 基准版

十轮回测验证 (1200 次决策) 最优配置:
- 平均收益：+1.24%/次 (+235% 提升)
- 综合胜率：49.0%
- 总收益率：+1347.93%
- 模型数量：15 个金融模型

关键发现:
- v8.0 是性能峰值
- v9.0 (25 个模型) 性能下降 3.2%
- 15 个模型是最优平衡点

后续优化建议:
- 所有新版本都与 v8.0 对比
- 显著优于基准：提升 >5%
- 优于基准：提升 >0%
- 未超越基准：提升 ≤0%
'''
