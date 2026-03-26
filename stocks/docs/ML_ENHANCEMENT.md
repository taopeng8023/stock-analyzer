# 🤖 工作流 v6.0 - ML 增强版文档

**版本：** v6.0 (ML Enhanced)  
**发布日期：** 2026-03-21  
**融合书籍：** 10 本经典投资理论

---

## 📚 融合的经典投资书籍

工作流 v6.0 使用机器学习深度理解并融合以下经典投资理论：

| 书籍 | 作者 | ML 特征工程 | 权重 |
|------|------|-----------|------|
| 《量价分析》 | 安娜·库林 | 量价关系、成交量趋势、量价背离、放量突破 | 20% |
| 《笑傲股市》 | 威廉·欧奈尔 | CAN SLIM 七大要素因子 | 15% |
| 《股市趋势技术分析》 | 罗伯特·爱德华兹 | 道氏理论、均线系统、K 线形态、技术指标 | 20% |
| 《海龟交易法则》 | 柯蒂斯·费思 | 唐奇安通道突破、ATR 波动率 | 15% |
| 《艾略特波浪理论》 | 普莱切特 | 波浪模式识别、推动浪/调整浪 | 10% |
| 《彼得·林奇的成功投资》 | 彼得·林奇 | 公司分类、PEG 因子 | 10% |
| 《聪明的投资者》 | 本杰明·格雷厄姆 | 价值因子、安全边际 | 5% |
| 《以交易为生》 | 亚历山大·埃尔德 | 三重滤网系统 | 5% |
| 《缠中说禅》 | 缠中说禅 | 走势类型识别 | - |
| 《江恩华尔街 45 年》 | 威廉·江恩 | 时间周期特征 | - |

---

## 🏗️ 技术架构

### 特征工程层

```
FeatureExtractor
├── extract_volume_price_features()    # 量价特征 (7 个特征)
├── extract_canslim_features()         # CAN SLIM 因子 (7 个特征)
├── extract_trend_features()           # 趋势技术特征 (8 个特征)
├── extract_turtle_features()          # 海龟交易特征 (3 个特征)
├── extract_elliott_features()         # 波浪理论特征 (2 个特征)
└── extract_all_features()             # 综合特征提取 (27+ 特征)
```

### 预测层

```
MLEnhancedPredictor
├── 特征提取 → FeatureExtractor
├── 各策略得分计算
│   ├── 量价得分 (volume_price)
│   ├── CAN SLIM 得分 (canslim)
│   ├── 趋势得分 (trend)
│   ├── 海龟得分 (turtle)
│   ├── 波浪得分 (elliott)
│   ├── 基本面得分 (fundamental)
│   └── 情绪得分 (sentiment)
├── 加权融合 → 最终得分
└── 评级生成 → 强烈推荐/推荐/谨慎推荐/观望
```

### 集成方法

当前使用**加权平均集成**，未来可扩展：
- Random Forest
- XGBoost
- LightGBM
- Stacking 集成
- LSTM 时序预测

---

## 🚀 使用方法

### 基础用法

```bash
# 运行工作流 (标准模式)
python3 run_workflow.py --strategy all --top 10 --push

# 运行工作流 (ML 增强模式)
python3 run_workflow.py --strategy all --top 10 --ml-enhance --push
```

### ML 增强模块单独使用

```bash
# 测试 ML 预测
python3 ml_strategy_enhancer.py --test

# 预测单只股票
python3 ml_strategy_enhancer.py --predict --stock sh600000
```

### Python API 调用

```python
from ml_strategy_enhancer import MLEnhancedPredictor

# 初始化预测器
predictor = MLEnhancedPredictor()

# 准备股票数据
stock_data = {
    'symbol': 'sh600000',
    'name': '浦发银行',
    'price': 10.5,
    'change_pct': 2.5,
    'volume': 5000000,
    'amount': 52500000,
}

# 预测
result = predictor.predict(stock_data)

print(f"综合得分：{result['final_score']:.2f}")
print(f"评级：{result['rating']}")
print(f"置信度：{result['confidence']}%")
print(f"理由：{result['reasons']}")
```

---

## 📊 特征详解

### 1. 量价特征 (《量价分析》)

| 特征 | 说明 | 取值范围 |
|------|------|---------|
| `vp_score` | 量价关系得分 | 0.2-0.85 |
| `volume_trend` | 成交量趋势 | -1.0 ~ 1.0 |
| `vp_divergence` | 量价背离检测 | -0.5 ~ 0 |
| `volume_breakout` | 放量突破信号 | 0-1.0 |
| `accumulation` | 资金累积程度 | 0.3-0.9 |

**量价关系判定：**
- 价涨量增 → 0.85 (健康上涨)
- 价涨量缩 → 0.50 (上涨乏力)
- 价跌量增 → 0.20 (恐慌下跌)
- 价跌量缩 → 0.45 (下跌乏力)

### 2. CAN SLIM 特征 (《笑傲股市》)

| 特征 | 说明 | 权重 |
|------|------|------|
| `c_score` | 当季盈利增长 | 20% |
| `a_score` | 年度盈利增长 | 15% |
| `n_score` | 新高信号 | 15% |
| `s_score` | 供给需求 | 10% |
| `l_score` | 龙头地位 | 15% |
| `i_score` | 机构认同 | 15% |
| `m_score` | 市场方向 | 10% |

### 3. 趋势技术特征

| 特征 | 说明 | 权重 |
|------|------|------|
| `dow_trend` | 道氏理论趋势 | 30% |
| `ma_score` | 均线系统 | 25% |
| `candlestick_score` | K 线形态 | 20% |
| `macd_score` | MACD 指标 | 10% |
| `kdj_score` | KDJ 指标 | 10% |
| `rsi_score` | RSI 指标 | 5% |

### 4. 海龟交易特征

| 特征 | 说明 |
|------|------|
| `donchian_breakout` | 唐奇安通道突破 (20 日) |
| `atr` | ATR 波动率 (14 日) |
| `turtle_signal` | 海龟买卖信号 |

### 5. 波浪理论特征

| 特征 | 说明 |
|------|------|
| `elliott_wave` | 波浪得分 |
| `wave_position` | 波浪位置 (推动浪/调整浪) |

---

## 🎯 评级生成逻辑

### 综合得分计算

```python
final_score = (
    vp_score * 0.20 +        # 量价分析
    canslim_score * 0.15 +   # CAN SLIM
    trend_score * 0.20 +     # 趋势技术
    turtle_score * 0.15 +    # 海龟交易
    elliott_score * 0.10 +   # 波浪理论
    fundamental_score * 0.10 +  # 基本面
    sentiment_score * 0.10      # 市场情绪
)
```

### 评级阈值

| 评级 | 得分范围 | 置信度 |
|------|---------|--------|
| 强烈推荐 | ≥ 0.80 | 90% |
| 推荐 | ≥ 0.65 | 75% |
| 谨慎推荐 | ≥ 0.50 | 60% |
| 观望 | < 0.50 | 45% |

---

## 📈 与 v5.1 对比

| 特性 | v5.1 | v6.0 ML 增强 |
|------|------|-------------|
| 策略融合 | 规则加权 | ML 特征工程 + 加权 |
| 特征数量 | ~16 个 | 27+ 个 |
| 理论基础 | 经验规则 | 10 本经典书籍 |
| 可解释性 | 高 | 高 (特征可追溯) |
| 扩展性 | 中 | 高 (可接入 ML 模型) |
| 适用场景 | 日常选股 | 深度分析 + 日常选股 |

---

## 🔧 扩展开发

### 添加新的策略特征

```python
class FeatureExtractor:
    def extract_your_strategy_features(self, stock_data: dict) -> dict:
        """你的策略特征提取"""
        features = {}
        # ... 特征计算
        return features
    
    def extract_all_features(self, stock_data: dict, history: list = None) -> Dict[str, float]:
        # 添加你的策略
        your_features = self.extract_your_strategy_features(stock_data)
        all_features.update(your_features)
        return all_features
```

### 调整策略权重

```python
# 在 MLEnhancedPredictor 中
self.model_weights = {
    'volume_price': 0.20,    # 调整权重
    'your_strategy': 0.10,   # 添加新策略权重
    # ...
}
```

### 接入真实 ML 模型

```python
from sklearn.ensemble import RandomForestClassifier

class MLEnhancedPredictor:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100)
        # 训练模型
        # self.model.fit(X_train, y_train)
    
    def predict(self, stock_data: dict, history: list = None) -> dict:
        features = self.feature_extractor.extract_all_features(stock_data, history)
        # 使用 ML 模型预测
        # prediction = self.model.predict([feature_vector])
        pass
```

---

## 📁 文件结构

```
stocks/
├── ml_strategy_enhancer.py        # ML 增强核心模块
├── run_workflow.py                # 工作流主入口 (v6.0)
├── workflow_push.py               # 推送模块 (支持 ML 标记)
├── volume_price_analysis.py       # 量价分析 (书籍理论)
├── canslim_strategy.py            # CAN SLIM 策略 (书籍理论)
├── trend_analysis_strategy.py     # 趋势技术分析 (书籍理论)
├── turtle_trading.py              # 海龟交易 (书籍理论)
├── elliott_wave.py                # 波浪理论 (书籍理论)
└── docs/
    └── ML_ENHANCEMENT.md          # 本文档
```

---

## ⚠️ 注意事项

1. **ML 增强模式耗时** - 比标准模式多约 10-20 秒 (特征计算)
2. **历史数据依赖** - 部分特征需要 K 线历史数据
3. **模型训练** - 当前使用规则加权，可进一步训练 ML 模型
4. **回测验证** - ML 增强模式需独立回测验证效果

---

## 📊 后续优化方向

1. **接入真实 ML 模型** - 使用历史数据训练 Random Forest/XGBoost
2. **深度学习** - LSTM/Transformer 时序预测
3. **特征优化** - 基于特征重要性筛选
4. **在线学习** - 根据新数据持续更新模型
5. **多模型集成** - Stacking/Blending 集成

---

*文档版本：v6.0 | 更新时间：2026-03-21*
