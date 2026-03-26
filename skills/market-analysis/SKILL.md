# Market Analysis Skill - 市场分析技能

**完整的股票市场分析系统**

---

## 📋 技能概述

整合所有市场分析工具到一个统一的技能中，包括：
- 技术面分析
- 基本面分析
- 资金流分析
- 新闻政策分析
- 目标价计算
- 概率预测
- 卖出价策略
- 报告生成与推送

---

## 📁 文件结构

```
market-analysis/
├── SKILL.md                    # 技能说明文档
├── market_analysis_skill.py    # 主技能文件（整合版）
├── core/
│   ├── data_fetcher.py         # 数据获取模块
│   ├── technical.py            # 技术面分析
│   ├── fundamental.py          # 基本面分析
│   ├── probability.py          # 概率计算
│   ├── target_price.py         # 目标价计算
│   └── report_generator.py     # 报告生成
├── utils/
│   ├── data_validation.py      # 数据验证
│   └── wechat_push.py          # 微信推送
├── cache/                      # 缓存目录
└── README.md                   # 使用说明
```

---

## 🚀 快速开始

### 安装

```bash
cd /home/admin/.openclaw/workspace/skills/market-analysis
```

### 基本使用

```python
from market_analysis_skill import MarketAnalysisSkill

# 初始化技能
skill = MarketAnalysisSkill()

# 分析单只股票
result = skill.analyze_stock('600170.SH')

# 生成市场报告
report = skill.generate_market_report(top_n=10)

# 推送报告
skill.push_report(report)
```

### 命令行使用

```bash
# 完整市场分析
python market_analysis_skill.py --full

# 分析特定股票
python market_analysis_skill.py --stock 600170.SH

# 生成目标价
python market_analysis_skill.py --target

# 推送报告
python market_analysis_skill.py --push
```

---

## 📊 功能模块

### 1. 数据获取模块 (data_fetcher.py)

**功能：**
- 从腾讯财经获取真实数据
- 支持 Tushare（待接入）
- 支持 AKShare（待接入）
- 数据缓存机制

**使用：**
```python
from core.data_fetcher import DataFetcher

fetcher = DataFetcher()
stocks = fetcher.get_real_time_data(count=50)
```

---

### 2. 技术面分析 (technical.py)

**8 大分析维度：**
- K 线形态分析
- 均线系统 (MA5/10/20/60)
- MACD 指标
- KDJ 指标
- RSI 指标
- 成交量分析
- 支撑阻力位
- 综合技术评分

**使用：**
```python
from core.technical import TechnicalAnalyzer

analyzer = TechnicalAnalyzer()
result = analyzer.analyze(stock_data)
# 返回：评分、评级、信号、支撑/阻力
```

---

### 3. 基本面分析 (fundamental.py)

**8 大分析维度：**
- 估值分析 (PE/PB/PEG)
- 盈利能力 (ROE/ROA)
- 成长能力 (营收/利润增长)
- 偿债能力 (负债率)
- 现金流分析
- 杜邦分析
- 行业对比
- 综合基本面评分

**使用：**
```python
from core.fundamental import FundamentalAnalyzer

analyzer = FundamentalAnalyzer()
result = analyzer.analyze(stock_data)
# 返回：评分、评级、行业对比
```

---

### 4. 概率计算 (probability.py)

**4 个维度：**
- 技术面概率 (40%)
- 基本面概率 (30%)
- 资金流概率 (20%)
- 市场情绪 (10%)

**输出：**
- 上涨概率
- 下跌概率
- 评级 (⭐⭐⭐⭐⭐)
- 置信度

**使用：**
```python
from core.probability import ProbabilityCalculator

calc = ProbabilityCalculator()
prob = calc.calculate(stock_data)
# 返回：上涨概率、下跌概率、评级
```

---

### 5. 目标价计算 (target_price.py)

**计算方法：**
- 技术面目标价（支撑/阻力）
- 基本面目标价（PEG 估值）
- 综合目标价（加权平均）

**卖出价策略：**
- 止损价（必须设置）
- 止盈价（目标位）
- 分批卖出价（4 档）
- 强制止损（-10%）

**使用：**
```python
from core.target_price import TargetPriceCalculator

calc = TargetPriceCalculator()
target = calc.calculate(stock_data)
# 返回：目标价、止损价、止盈价、分批卖出价
```

---

### 6. 报告生成 (report_generator.py)

**报告类型：**
- 快速分析报告
- 完整分析报告
- 个股深度报告
- 市场日报/周报

**功能：**
- 3 句话摘要
- 数据标注
- 历史对比
- 风险提示

**使用：**
```python
from core.report_generator import ReportGenerator

generator = ReportGenerator()
report = generator.generate(stocks_data, type='full')
```

---

## 🎯 完整分析流程

```python
from market_analysis_skill import MarketAnalysisSkill

# 1. 初始化
skill = MarketAnalysisSkill()

# 2. 获取数据
stocks = skill.fetch_data(count=50)

# 3. 分析每只股票
for stock in stocks:
    # 技术面分析
    stock['technical'] = skill.analyze_technical(stock)
    
    # 基本面分析
    stock['fundamental'] = skill.analyze_fundamental(stock)
    
    # 概率计算
    stock['probability'] = skill.calculate_probability(stock)
    
    # 目标价计算
    stock['target_price'] = skill.calculate_target_price(stock)

# 4. 筛选优质股票
quality_stocks = skill.filter_quality(stocks, min_score=60)

# 5. 生成报告
report = skill.generate_report(quality_stocks, type='full')

# 6. 推送报告
skill.push_report(report)
```

---

## 📝 数据政策

### 核心原则

> **所有股票交易数据必须来自真实市场数据源**
> **严禁使用任何模拟/伪造数据**
> **此政策适用于所有场景**

### 数据标注

| 标注 | 含义 | 说明 |
|------|------|------|
| ✅ | 真实数据 | 来自腾讯财经实时行情 |
| ⚠️ | 估算数据 | 主力流入=成交额×15% |
| 📊 | 模型分析 | 目标价、概率为模型计算 |
| ❌ | 无数据 | 无法获取真实数据 |

### 数据验证

```python
from utils.data_validation import DataValidator

validator = DataValidator(strict_mode=True)

# 验证数据
if validator.validate(stock_data):
    # 数据有效，继续分析
    pass
else:
    # 数据无效，停止分析
    print("数据验证失败")
```

---

## 📊 输出示例

### 个股分析报告

```
📈 上海建工 (600170)

【行情数据】
  现价：¥2.94
  涨跌：+12.89%
  成交：139 亿
  主力：+20.87 亿

【概率分析】
  上涨概率：65% ⭐⭐⭐⭐
  下跌概率：35%
  评级：较大概率上涨

【目标价】
  当前价：¥2.94
  目标价：¥3.10
  空间：+5.4%

【卖出价】
  止损：¥2.65（-9.9%）
  止盈：¥3.10（+5.4%）
  分批：
    25%@¥2.95
    25%@¥3.10
    25%@¥3.20
    25%@¥3.50

【技术面】
  评分：72/100 ⭐⭐⭐⭐
  K 线：小阳线
  均线：多头排列
  MACD: 金叉

【基本面】
  评分：68/100 ⭐⭐⭐
  PE: 8x
  ROE: 12%
  增长：+15%

【操作建议】
  评级：推荐
  买入：¥2.90-2.95
  目标：¥3.10
  止损：¥2.65
```

---

## 🔧 配置选项

### 数据源配置

```python
config = {
    'data_sources': {
        'primary': 'tencent',      # 主要数据源
        'backup': ['tushare', 'akshare'],  # 备用数据源
        'cache_enabled': True,     # 启用缓存
        'cache_ttl': 600,          # 缓存有效期（秒）
    }
}
```

### 分析参数配置

```python
config = {
    'analysis': {
        'min_probability': 50,     # 最小上涨概率
        'min_score': 60,           # 最小综合评分
        'max_position': 0.3,       # 单只股票最大仓位
        'stop_loss_percent': 0.1,  # 止损比例
    }
}
```

### 推送配置

```python
config = {
    'push': {
        'enabled': True,
        'webhook': 'your_webhook_url',
        'schedule': 'daily_16:00',  # 推送时间
    }
}
```

---

## 📈 扩展开发

### 添加新数据源

```python
from core.data_fetcher import DataSourceBase

class MyDataSource(DataSourceBase):
    def fetch_data(self, symbol):
        # 实现数据获取逻辑
        pass
```

### 添加新指标

```python
from core.technical import IndicatorBase

class MyIndicator(IndicatorBase):
    def calculate(self, stock_data):
        # 实现指标计算逻辑
        pass
```

### 自定义报告模板

```python
from core.report_generator import ReportTemplate

class MyTemplate(ReportTemplate):
    def generate(self, stocks_data):
        # 实现报告生成逻辑
        pass
```

---

## ⚠️ 风险提示

1. **数据风险**
   - 所有数据仅供参考
   - 不保证数据准确性
   - 市场数据可能延迟

2. **模型风险**
   - 概率不保证实现
   - 目标价不保证达到
   - 模型存在局限性

3. **投资风险**
   - 股市有风险
   - 本报告仅供参考
   - 不构成投资建议
   - 请独立判断，自负风险

---

## 📚 相关文档

- `README.md` - 详细使用说明
- `DATA_POLICY.md` - 数据政策
- `API.md` - API 接口文档
- `EXAMPLES.md` - 使用示例

---

**版本：v1.0**

**最后更新：2026-03-18**

**⚠️ 仅用于研究学习，不构成投资建议**
