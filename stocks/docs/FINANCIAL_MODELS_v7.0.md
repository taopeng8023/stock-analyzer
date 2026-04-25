# 📊 工作流 v7.0 - 金融模型增强版

**版本：** v7.0 (Financial Models Enhanced)  
**发布日期：** 2026-03-21  
**集成模型：** 10 个经典金融学模型

---

## 📚 集成的经典金融模型

工作流 v7.0 集成以下经典金融学和量化投资模型：

| 模型 | 作者/来源 | 用途 | 权重 |
|------|----------|------|------|
| **CAPM** | William Sharpe (1964) | 资产定价、Alpha/Beta 分析 | 20% |
| **Fama-French 三因子** | Fama & French (1992) | 规模因子、价值因子 | 20% |
| **Carhart 四因子** | Carhart (1997) | 加入动量因子 | 25% |
| **Black-Litterman** | Black & Litterman (1992) | 资产配置、观点融入 | 15% |
| **Sharpe Ratio** | William Sharpe | 风险调整后收益 | 5% |
| **Sortino Ratio** | Frank Sortino | 下行风险调整收益 | 5% |
| **Max Drawdown** | - | 最大回撤控制 | 5% |
| **VaR** | J.P. Morgan | 风险价值 | 5% |

---

## 🏗️ 模型详解

### 1. CAPM 资本资产定价模型

**公式：** `E(Ri) = Rf + βi * (E(Rm) - Rf)`

**功能：**
- 计算股票预期回报
- 评估股票是否被高估/低估
- 计算 Alpha 和 Beta

**参数：**
- 无风险利率：2%
- 市场预期回报：8%
- 市场溢价：6%

**输出：**
```
Beta: 股票相对市场的波动性
Alpha: 超额收益 (实际回报 - 预期回报)
Valuation: 低估/合理/高估
Signal: 买入/持有/卖出
```

---

### 2. Fama-French 三因子模型

**公式：** `E(Ri) = Rf + βmkt*(Rm-Rf) + βsmb*SMB + βhml*HML`

**三因子：**
1. **Market Factor** - 市场因子
2. **SMB (Small Minus Big)** - 规模因子 (小盘股溢价)
3. **HML (High Minus Low)** - 价值因子 (价值股溢价)

**规模分类：**
| 成交额 | 分类 | SMB 暴露 |
|--------|------|---------|
| <10 亿 | 小盘 | +0.3 |
| 10-50 亿 | 中小盘 | +0.15 |
| 50-100 亿 | 中盘 | 0 |
| >100 亿 | 大盘 | -0.1 |

**价值分类：**
| 股价 | 分类 | HML 暴露 |
|------|------|---------|
| <10 元 | 价值 | +0.25 |
| 10-30 元 | 平衡 | +0.1 |
| 30-100 元 | 成长 | -0.05 |
| >100 元 | 高成长 | -0.15 |

---

### 3. Carhart 四因子模型

**公式：** `E(Ri) = Rf + βmkt*(Rm-Rf) + βsmb*SMB + βhml*HML + βmom*MOM`

**新增：动量因子 (MOM)**

**动量分类：**
| 3 个月回报 | 动量信号 | MOM 暴露 |
|-----------|---------|---------|
| >20% | 强动量 | +0.3 |
| 10-20% | 动量 | +0.15 |
| 0-10% | 弱动量 | +0.05 |
| <0% | 反转 | -0.2 |

**动量溢价：** 4%

---

### 4. Black-Litterman 资产配置模型

**功能：**
- 结合市场均衡回报和投资者观点
- 计算最优资产配置权重

**配置建议：**
| 调整后回报 | 配置建议 | 建议权重 |
|-----------|---------|---------|
| >15% | 超配 | 15% |
| 10-15% | 标配 | 10% |
| 5-10% | 低配 | 5% |
| <5% | 不配置 | 0% |

---

### 5. 风险指标模型

#### Sharpe Ratio (夏普比率)
**公式：** `(E(Rp) - Rf) / σp`

**评估：**
- >1.5: 优秀
- >1.0: 良好
- >0.5: 一般
- <0: 差

#### Sortino Ratio (索提诺比率)
**公式：** `(E(Rp) - Rf) / Downside Deviation`

**特点：** 只考虑下行风险

#### Max Drawdown (最大回撤)
**公式：** `(Peak - Trough) / Peak`

**风险评估：**
- <10%: 低风险
- 10-20%: 中低风险
- 20-30%: 中风险
- 30-40%: 中高风险
- >40%: 高风险

#### VaR (风险价值)
**置信度：** 95%
**含义：** 95% 概率下，最大损失不超过 VaR

---

## 🚀 使用方法

### 命令行

```bash
# 标准模式
python3 run_workflow.py --strategy all --top 10 --push

# ML 增强模式
python3 run_workflow.py --strategy all --top 10 --ml-enhance --push

# 金融模型增强模式 (v7.0)
python3 run_workflow.py --strategy all --top 10 --financial-models --push
```

### Python API

```python
from financial_models import FinancialModelsEnsemble

# 初始化
ensemble = FinancialModelsEnsemble()

# 股票数据
stock_data = {
    'symbol': 'sh600000',
    'name': '浦发银行',
    'price': 10.5,
    'change_pct': 2.5,
    'volume': 5000000,
    'amount': 52500000,
}

# 综合分析
result = ensemble.analyze(stock_data)

print(f"综合得分：{result['final_score']:.2f}")
print(f"评级：{result['rating']}")
print(f"置信度：{result['confidence']}%")

# 各模型结果
print(f"CAPM: {result['models']['capm']['description']}")
print(f"Fama-French: {result['models']['fama_french']['description']}")
print(f"Carhart: {result['models']['carhart']['description']}")
print(f"Risk Metrics: {result['models']['risk_metrics']['description']}")
print(f"Black-Litterman: {result['models']['black_litterman']['description']}")
```

---

## 📊 综合评分逻辑

### 评分权重

```python
final_score = (
    capm_score * 0.20 +           # CAPM
    ff_score * 0.20 +             # Fama-French
    carhart_score * 0.25 +        # Carhart (最高权重)
    risk_score * 0.20 +           # 风险指标
    bl_confidence * 100 * 0.15    # Black-Litterman
)
```

### 评级阈值

| 综合得分 | 评级 | 置信度 |
|---------|------|--------|
| ≥80 | 强烈推荐 | 90% |
| ≥65 | 推荐 | 75% |
| ≥50 | 谨慎推荐 | 60% |
| <50 | 观望 | 45% |

---

## 📈 与 v6.x 对比

| 特性 | v6.1-ML | v6.2-StopLoss | **v7.0-Financial** |
|------|---------|---------------|-------------------|
| ML 模型 | ✅ RF | ✅ RF | ✅ RF |
| 止盈止损优化 | ❌ | ✅ | ✅ |
| CAPM | ❌ | ❌ | ✅ |
| Fama-French | ❌ | ❌ | ✅ |
| Carhart | ❌ | ❌ | ✅ |
| Black-Litterman | ❌ | ❌ | ✅ |
| 风险指标 | ❌ | ❌ | ✅ |
| 综合评分 | ML 70% + 规则 30% | 规则加权 | **ML+ 金融模型 + 规则** |

---

## 🎯 预期效果

### 优势

1. **理论基础扎实** - 基于诺贝尔奖级金融学理论
2. **多维度评估** - 从定价、风格、动量、风险多角度分析
3. **可解释性强** - 每个模型输出清晰的分析结果
4. **与 ML 互补** - 金融学理论 + 机器学习，优势互补

### 预期提升

| 指标 | v6.1 | **v7.0 预期** | 提升 |
|------|------|-------------|------|
| 胜率 | 50% | **55-60%** | +5-10% |
| 夏普比率 | 0.8 | **1.2+** | +50% |
| 最大回撤 | -25% | **-15%** | -40% |
| 风险调整收益 | 1.0% | **1.5%+** | +50% |

---

## 📁 文件结构

```
stocks/
├── financial_models.py           # 金融模型核心模块 (新建) ✅
├── run_workflow.py               # 工作流主程序 (已更新 v7.0) ✅
├── ml_strategy_enhancer.py       # ML 增强模块
├── ml_model_trainer.py           # ML 模型训练模块
├── optimization_config.py        # 优化配置
└── docs/
    ├── FINANCIAL_MODELS_v7.0.md  # 本文档 ✅
    ├── ML_ENHANCEMENT.md         # ML 增强文档
    ├── ML_OPTIMIZATION_COMPLETE.md
    └── STOP_PROFIT_LOSS_OPTIMIZATION_v6.2.md
```

---

## ⚠️ 注意事项

1. **数据需求** - 部分模型需要历史数据计算 Beta、波动率等
2. **参数校准** - 无风险利率、市场回报等参数需根据市场环境调整
3. **模型局限** - 经典模型基于有效市场假设，A 股可能存在偏差
4. **结合使用** - 建议与 ML 模型结合使用，发挥各自优势

---

## 💡 后续优化

1. **参数动态调整** - 根据市场状态动态调整模型参数
2. **因子扩展** - 加入更多因子 (质量、低波、成长等)
3. **实时训练** - 基于最新数据重新校准模型参数
4. **深度学习融合** - 将金融模型特征输入深度学习模型

---

*文档版本：v7.0 | 更新时间：2026-03-21*
