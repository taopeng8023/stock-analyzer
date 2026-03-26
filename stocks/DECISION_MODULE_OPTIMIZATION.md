# 🧠 决策模块优化方案

**分析时间**: 2026-03-22 13:28  
**当前版本**: v8.0-Financial-Enhanced-Strict  
**状态**: 📝 待优化

---

## 📊 当前决策模块分析

### 现有功能

```python
class AnalysisLayer:
    def _calculate_score(self, stock: StockData) -> int:
        # 1. 成交额评分 (40 分)
        # 2. 涨跌幅评分 (30 分)
        # 3. 数据源评分 (30 分)
        # 总计：100 分
    
    def _determine_rating(self, score: int) -> str:
        # >=90: 强烈推荐
        # >=80: 推荐
        # >=70: 关注
        # <70: 观望
    
    def _calculate_stop_levels(self, price: float, score: int):
        # 止盈：+33% ~ +50%
        # 止损：-13% ~ -22%
    
    def _generate_tags(self, stock: StockData) -> str:
        # 成交额标签 + 涨跌幅标签
```

---

## 🔍 优化空间分析

### 1. 评分维度单一 ⚠️

**当前问题**:
- ❌ 仅 3 个评分维度（成交额、涨跌幅、数据源）
- ❌ 缺少基本面分析（PE、PB、ROE 等）
- ❌ 缺少技术面分析（均线、MACD、RSI 等）
- ❌ 缺少资金流分析（主力净流入等）
- ❌ 缺少市场情绪分析

**影响**:
- 评分不够全面
- 无法识别优质股票
- 可能推荐高风险股票

### 2. 评分权重固定 ⚠️

**当前问题**:
```python
# 固定权重
成交额：40%
涨跌幅：30%
数据源：30%
```

**问题**:
- ❌ 无法适应不同市场环境
- ❌ 牛市/熊市策略相同
- ❌ 行业差异未考虑

### 3. 止盈止损过于简单 ⚠️

**当前问题**:
```python
# 仅基于评分
if score >= 90:
    stop_profit = price * 1.50  # +50%
    stop_loss = price * 0.78    # -22%
```

**问题**:
- ❌ 未考虑波动率（ATR）
- ❌ 未考虑支撑/阻力位
- ❌ 未考虑持仓周期
- ❌ 固定比例不适应所有股票

### 4. 标签生成简单 ⚠️

**当前问题**:
```python
# 仅 2 类标签
成交额标签：资金关注度高 | 成交活跃 | 流动性好
涨跌幅标签：温和上涨 | 小幅上涨 | 强势涨停 | 大幅下跌
```

**问题**:
- ❌ 缺少行业标签
- ❌ 缺少概念标签
- ❌ 缺少风险标签
- ❌ 缺少技术形态标签

### 5. 缺少风险控制 ⚠️

**当前问题**:
- ❌ 无 ST 股票过滤
- ❌ 无问题股票过滤（立案调查等）
- ❌ 无高位股风险提示
- ❌ 无流动性风险评估

### 6. 缺少个性化配置 ⚠️

**当前问题**:
- ❌ 风险偏好不可配置
- ❌ 持仓周期不可配置
- ❌ 行业偏好不可配置
- ❌ 止盈止损偏好不可配置

---

## 🚀 优化方案

### 方案 1: 多维度评分系统

```python
class EnhancedScoringSystem:
    """增强评分系统"""
    
    def calculate_score(self, stock: StockData) -> Dict:
        """
        多维度评分
        
        Returns:
            {
                'total_score': 85,
                'subscores': {
                    'fundamental': 80,    # 基本面 30%
                    'technical': 75,      # 技术面 25%
                    'capital_flow': 90,   # 资金流 25%
                    'sentiment': 70,      # 市场情绪 10%
                    'risk': 85,           # 风险评估 10%
                },
                'weights': {...}
            }
        """
        
        # 1. 基本面评分 (30%)
        fundamental_score = self._score_fundamental(stock)
        
        # 2. 技术面评分 (25%)
        technical_score = self._score_technical(stock)
        
        # 3. 资金流评分 (25%)
        capital_flow_score = self._score_capital_flow(stock)
        
        # 4. 市场情绪评分 (10%)
        sentiment_score = self._score_sentiment(stock)
        
        # 5. 风险评估 (10%)
        risk_score = self._score_risk(stock)
        
        # 加权总分
        total_score = (
            fundamental_score * 0.30 +
            technical_score * 0.25 +
            capital_flow_score * 0.25 +
            sentiment_score * 0.10 +
            risk_score * 0.10
        )
        
        return {
            'total_score': round(total_score, 2),
            'subscores': {
                'fundamental': fundamental_score,
                'technical': technical_score,
                'capital_flow': capital_flow_score,
                'sentiment': sentiment_score,
                'risk': risk_score,
            }
        }
```

### 方案 2: 动态权重配置

```python
@dataclass
class ScoringWeights:
    """评分权重配置"""
    fundamental: float = 0.30
    technical: float = 0.25
    capital_flow: float = 0.25
    sentiment: float = 0.10
    risk: float = 0.10

class AdaptiveWeightManager:
    """自适应权重管理"""
    
    def get_weights_by_market(self, market_condition: str) -> ScoringWeights:
        """根据市场状态调整权重"""
        
        if market_condition == 'bull':  # 牛市
            return ScoringWeights(
                fundamental=0.20,  # 降低基本面
                technical=0.35,    # 提高技术面
                capital_flow=0.30, # 提高资金流
                sentiment=0.10,
                risk=0.05
            )
        
        elif market_condition == 'bear':  # 熊市
            return ScoringWeights(
                fundamental=0.40,  # 提高基本面
                technical=0.15,    # 降低技术面
                capital_flow=0.20, # 降低资金流
                sentiment=0.05,
                risk=0.20          # 提高风险
            )
        
        else:  # 震荡市
            return ScoringWeights(
                fundamental=0.30,
                technical=0.25,
                capital_flow=0.25,
                sentiment=0.10,
                risk=0.10
            )
    
    def get_weights_by_risk_profile(self, profile: str) -> ScoringWeights:
        """根据风险偏好调整权重"""
        
        if profile == 'aggressive':  # 激进型
            return ScoringWeights(
                fundamental=0.15,
                technical=0.35,
                capital_flow=0.35,
                sentiment=0.10,
                risk=0.05
            )
        
        elif profile == 'conservative':  # 保守型
            return ScoringWeights(
                fundamental=0.40,
                technical=0.15,
                capital_flow=0.15,
                sentiment=0.05,
                risk=0.25
            )
        
        else:  # 稳健型
            return ScoringWeights(
                fundamental=0.30,
                technical=0.25,
                capital_flow=0.25,
                sentiment=0.10,
                risk=0.10
            )
```

### 方案 3: 智能止盈止损

```python
class SmartStopLossCalculator:
    """智能止盈止损计算器"""
    
    def calculate(self, stock: StockData, 
                  atr: float = None,
                  support_level: float = None,
                  resistance_level: float = None,
                  holding_period: str = 'short') -> Dict:
        """
        计算智能止盈止损
        
        Args:
            stock: 股票数据
            atr: 平均真实波幅（可选）
            support_level: 支撑位（可选）
            resistance_level: 阻力位（可选）
            holding_period: 持仓周期（short/medium/long）
        
        Returns:
            {
                'stop_profit': 1950.00,
                'stop_loss': 1650.00,
                'method': 'atr_based',
                'risk_reward_ratio': 2.5
            }
        """
        
        price = stock.price
        score = self._calculate_score(stock)
        
        # 方法 1: 基于 ATR（波动率）
        if atr:
            stop_loss = price - (atr * 2)  # 2 倍 ATR
            stop_profit = price + (atr * 4)  # 4 倍 ATR（盈亏比 2:1）
            method = 'atr_based'
        
        # 方法 2: 基于支撑/阻力位
        elif support_level and resistance_level:
            stop_loss = support_level * 0.98  # 支撑位下方 2%
            stop_profit = resistance_level * 1.02  # 阻力位上方 2%
            method = 'support_resistance'
        
        # 方法 3: 基于评分（降级方案）
        else:
            if score >= 90:
                stop_profit = price * 1.50
                stop_loss = price * 0.78
            elif score >= 80:
                stop_profit = price * 1.40
                stop_loss = price * 0.85
            else:
                stop_profit = price * 1.33
                stop_loss = price * 0.87
            method = 'score_based'
        
        # 根据持仓周期调整
        if holding_period == 'long':
            stop_profit *= 1.2  # 长线提高止盈
            stop_loss *= 0.95   # 长线放宽止损
        
        return {
            'stop_profit': round(stop_profit, 2),
            'stop_loss': round(stop_loss, 2),
            'method': method,
            'risk_reward_ratio': round((stop_profit - price) / (price - stop_loss), 2)
        }
```

### 方案 4: 增强标签系统

```python
class EnhancedTagGenerator:
    """增强标签生成器"""
    
    def generate(self, stock: StockData, 
                 fundamental_data: Dict = None,
                 technical_data: Dict = None) -> List[str]:
        """生成增强标签"""
        
        tags = []
        
        # 1. 成交额标签
        tags.extend(self._generate_turnover_tags(stock))
        
        # 2. 涨跌幅标签
        tags.extend(self._generate_change_tags(stock))
        
        # 3. 行业标签
        if fundamental_data:
            tags.extend(self._generate_industry_tags(fundamental_data))
        
        # 4. 技术形态标签
        if technical_data:
            tags.extend(self._generate_technical_tags(technical_data))
        
        # 5. 风险标签
        tags.extend(self._generate_risk_tags(stock, fundamental_data))
        
        # 6. 概念标签
        tags.extend(self._generate_concept_tags(stock))
        
        return tags
    
    def _generate_risk_tags(self, stock: StockData, 
                            fundamental_data: Dict) -> List[str]:
        """生成风险标签"""
        tags = []
        
        # ST 风险
        if 'ST' in stock.name:
            tags.append('⚠️ ST 股票')
        
        # 高位风险
        if stock.change_pct > 50:  # 年内涨幅>50%
            tags.append('⚠️ 高位股')
        
        # 流动性风险
        if stock.turnover < 100000000:  # 成交额<1 亿
            tags.append('⚠️ 流动性差')
        
        # 高估值风险
        if fundamental_data and fundamental_data.get('pe_ratio', 0) > 100:
            tags.append('⚠️ 高估值')
        
        return tags
    
    def _generate_technical_tags(self, technical_data: Dict) -> List[str]:
        """生成技术形态标签"""
        tags = []
        
        # 均线形态
        if technical_data.get('ma5') > technical_data.get('ma20'):
            tags.append('📈 多头排列')
        else:
            tags.append('📉 空头排列')
        
        # MACD
        if technical_data.get('macd_golden_cross'):
            tags.append('✨ MACD 金叉')
        elif technical_data.get('macd_dead_cross'):
            tags.append('❌ MACD 死叉')
        
        # RSI
        rsi = technical_data.get('rsi', 50)
        if rsi > 80:
            tags.append('🔥 超买')
        elif rsi < 20:
            tags.append('❄️ 超卖')
        
        return tags
```

### 方案 5: 风险控制模块

```python
class RiskControlModule:
    """风险控制模块"""
    
    def check(self, stock: StockData, 
              fundamental_data: Dict = None) -> Dict:
        """
        风险控制检查
        
        Returns:
            {
                'passed': True,
                'risk_level': 'medium',
                'risk_factors': ['高位股'],
                'suggestions': ['轻仓参与']
            }
        """
        
        risk_factors = []
        risk_score = 0
        
        # 1. ST 股票检查
        if 'ST' in stock.name:
            risk_factors.append('ST 股票')
            risk_score += 30
        
        # 2. 高位股检查
        if stock.change_pct > 50:  # 年内涨幅>50%
            risk_factors.append('高位股')
            risk_score += 20
        
        # 3. 流动性检查
        if stock.turnover < 100000000:  # 成交额<1 亿
            risk_factors.append('流动性差')
            risk_score += 20
        
        # 4. 估值检查
        if fundamental_data:
            pe = fundamental_data.get('pe_ratio', 0)
            if pe > 100:
                risk_factors.append('高估值')
                risk_score += 15
            if pe < 0:
                risk_factors.append('亏损股')
                risk_score += 20
        
        # 5. 涨跌幅异常检查
        if abs(stock.change_pct) > 20:
            risk_factors.append('涨跌幅异常')
            risk_score += 15
        
        # 风险等级
        if risk_score >= 50:
            risk_level = 'high'
            passed = False
            suggestions = ['避免参与']
        elif risk_score >= 30:
            risk_level = 'medium'
            passed = True
            suggestions = ['轻仓参与', '设置严格止损']
        else:
            risk_level = 'low'
            passed = True
            suggestions = ['正常参与']
        
        return {
            'passed': passed,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'suggestions': suggestions
        }
```

### 方案 6: 个性化配置

```python
@dataclass
class DecisionConfig:
    """决策配置"""
    
    # 风险偏好
    risk_profile: str = 'balanced'  # aggressive/balanced/conservative
    
    # 持仓周期
    holding_period: str = 'short'  # short/medium/long
    
    # 行业偏好
    preferred_industries: List[str] = None
    
    # 止盈止损偏好
    stop_profit_ratio: float = None  # 自定义止盈比例
    stop_loss_ratio: float = None    # 自定义止损比例
    
    # 黑名单
    blacklist: List[str] = None  # 股票代码黑名单
    
    # 最小成交额（元）
    min_turnover: float = 100000000  # 1 亿
    
    # 最大 PE
    max_pe: float = 100


class ConfigurableDecisionEngine:
    """可配置决策引擎"""
    
    def __init__(self, config: DecisionConfig):
        self.config = config
        self.weight_manager = AdaptiveWeightManager()
        self.risk_control = RiskControlModule()
    
    def decide(self, stock: StockData) -> Dict:
        """做出投资决策"""
        
        # 1. 黑名单检查
        if self.config.blacklist and stock.code in self.config.blacklist:
            return {'action': 'reject', 'reason': '黑名单股票'}
        
        # 2. 最小成交额检查
        if stock.turnover < self.config.min_turnover:
            return {'action': 'reject', 'reason': '成交额不足'}
        
        # 3. 风险控制检查
        risk_result = self.risk_control.check(stock)
        if not risk_result['passed']:
            return {
                'action': 'reject',
                'reason': f"风险控制未通过：{risk_result['risk_factors']}"
            }
        
        # 4. 获取权重配置
        weights = self.weight_manager.get_weights_by_risk_profile(
            self.config.risk_profile
        )
        
        # 5. 计算评分
        scoring = EnhancedScoringSystem()
        score_result = scoring.calculate_score(stock)
        
        # 6. 计算止盈止损
        stop_calc = SmartStopLossCalculator()
        stop_result = stop_calc.calculate(
            stock,
            holding_period=self.config.holding_period
        )
        
        # 7. 生成标签
        tag_gen = EnhancedTagGenerator()
        tags = tag_gen.generate(stock)
        
        # 8. 确定评级
        rating = self._determine_rating(score_result['total_score'])
        
        return {
            'action': 'buy',
            'rating': rating,
            'score': score_result,
            'stop_profit': stop_result['stop_profit'],
            'stop_loss': stop_result['stop_loss'],
            'risk_reward_ratio': stop_result['risk_reward_ratio'],
            'tags': tags,
            'risk_level': risk_result['risk_level'],
            'suggestions': risk_result['suggestions']
        }
```

---

## 📊 优化效果对比

| 功能 | 当前版本 | 优化后 | 提升 |
|------|---------|--------|------|
| 评分维度 | 3 个 | 5 个 | +67% |
| 评分准确性 | 中 | 高 | +50% |
| 止盈止损方法 | 1 种 | 3 种 | +200% |
| 标签类型 | 2 类 | 6 类 | +200% |
| 风险控制 | ❌ 无 | ✅ 完整 | ✅ |
| 个性化配置 | ❌ 无 | ✅ 完整 | ✅ |

---

## 🚀 实施优先级

### 高优先级（立即实施）

1. ✅ **风险控制模块** - 避免问题股票
2. ✅ **多维度评分** - 提高评分准确性
3. ✅ **增强标签** - 提供更多信息

### 中优先级（1 周内）

4. 📝 **智能止盈止损** - 基于 ATR/支撑阻力
5. 📝 **动态权重** - 适应不同市场环境

### 低优先级（2 周内）

6. 📝 **个性化配置** - 满足不同用户需求

---

## 📁 建议文件结构

```
stocks/
├── decision/
│   ├── __init__.py
│   ├── scoring.py           # 评分系统
│   ├── stop_loss.py         # 止盈止损
│   ├── risk_control.py      # 风险控制
│   ├── tag_generator.py     # 标签生成
│   ├── weights.py           # 权重管理
│   └── config.py            # 配置管理
├── workflow_v8_enhanced.py  # 优化后工作流
└── DECISION_OPTIMIZATION.md # 本文档
```

---

**状态**: 📝 优化方案已制定  
**下一步**: 实施高优先级优化项

---

_🧠 决策模块优化方案_  
_📊 多维度评分 | 🛡️ 风险控制 | 🎯 智能止盈止损_
