"""
选股系统配置
鹏总专用 - 稳健盈利策略
"""

# 基本面筛选条件
FUNDAMENTAL_FILTERS = {
    'min_roe': 15,           # 最小 ROE (%)
    'min_revenue_growth': 10, # 最小营收增长率 (%)
    'min_profit_growth': 15,  # 最小净利润增长率 (%)
    'max_debt_ratio': 60,     # 最大资产负债率 (%)
    'min_cash_flow': 0,       # 最小经营现金流 (亿)
}

# 技术面筛选条件
TECHNICAL_FILTERS = {
    'price_above_ma60': True,    # 股价在 60 日均线上方
    'volume_ratio': 1.2,         # 成交量比率 (5 日/20 日)
    'rsi_min': 40,               # RSI 最小值
    'rsi_max': 70,               # RSI 最大值
}

# 资金面筛选条件
MONEY_FLOW_FILTERS = {
    'northbound_days': 5,        # 北向资金连续流入天数
    'main_force_net_inflow': 0,  # 主力资金净流入 (亿)
}

# 交易策略参数
TRADING_PARAMS = {
    'stop_loss_pct': 8,          # 止损百分比 (%)
    'take_profit_pct': 25,       # 止盈百分比 (%)
    'trailing_stop_pct': 10,     # 移动止盈回撤 (%)
    'max_position_pct': 20,      # 单只股票最大仓位 (%)
    'max_industry_pct': 30,      # 单行业最大仓位 (%)
}

# 评分权重
SCORE_WEIGHTS = {
    'fundamental': 0.35,         # 基本面权重
    'technical': 0.35,           # 技术面权重
    'money_flow': 0.20,          # 资金面权重
    'sentiment': 0.10,           # 情绪面权重
}

# 买入阈值
BUY_THRESHOLDS = {
    'excellent': 85,             # 强烈推荐
    'good': 70,                  # 推荐
    'neutral': 50,               # 观望
    'avoid': 0,                  # 避免
}

# 10 日收益预测参数
RETURN_PREDICTION = {
    'base_return': 5,            # 基础预期收益 (%)
    'excellent_bonus': 15,       # 优秀股额外收益 (%)
    'good_bonus': 8,             # 良好股额外收益 (%)
    'market_adjustment': 0.3,    # 市场调整系数
}

# 成功概率计算参数
SUCCESS_PROBABILITY = {
    'base_probability': 50,      # 基础成功率 (%)
    'score_bonus': 0.5,          # 评分每分增加成功率
    'volume_bonus': 5,           # 成交量放大奖励
    'northbound_bonus': 10,      # 北向资金奖励
    'max_probability': 85,       # 最大成功率
    'min_probability': 20,       # 最小成功率
}
