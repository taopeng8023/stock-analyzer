# 筹码分布 (CYQ) 接口集成文档

**更新时间**: 2026-03-27  
**接口**: `stock_cyq_em`  
**数据源**: 东方财富网

---

## 📊 什么是筹码分布 (CYQ)

筹码分布 (Chip Yield Query) 是分析股票持仓成本分布的技术指标。

### 核心用途

| 用途 | 说明 |
|------|------|
| **判断主力成本** | 识别主力资金的持仓成本区域 |
| **识别支撑/压力** | 筹码密集区形成支撑或压力位 |
| **判断集中度** | 筹码越集中，变盘可能性越大 |
| **发现主力行为** | 吸筹/出货迹象分析 |

---

## 🔧 接口集成

### 1. 数据源管理器集成

```python
# data_source_manager.py

def get_cyq_data(self, symbol: str, adjust: str = 'qfq') -> Optional[Dict]:
    """
    获取个股筹码分布数据
    
    Args:
        symbol: 股票代码
        adjust: 复权类型 (qfq/hfq/空)
    
    Returns:
        筹码分布数据
    """
    data = ak.stock_cyq_em(symbol=symbol, adjust=adjust)
    
    return {
        'symbol': symbol,
        'data': data.to_dict('records'),
        'columns': list(data.columns),
    }
```

### 2. 选股系统集成

```python
# stock_selector_v2.py

def analyze_stock(self, symbol: str, fund_flow_data: Dict = None, cyq_data: Dict = None):
    """分析股票 (新增 cyq_data 参数)"""
    
    # ... 原有逻辑 ...
    
    # 筹码分布评分 (0-4 分)
    cyq_score_val = 0
    if cyq_data and 'data' in cyq_data:
        # 计算集中度
        # 计算获利盘比例
        # 判断价格位置
        score += cyq_score_val
```

---

## 📈 筹码分析指标

### 1. 筹码集中度

```python
# 计算 90% 筹码的价格区间
p5 = prices[int(len(prices) * 0.05)]
p95 = prices[int(len(prices) * 0.95)]
concentration_range = p95 - p5

# 集中度比率 (越小越集中)
concentration_ratio = concentration_range / avg_price
```

**评分标准**:
| 集中度比率 | 状态 | 评分 |
|------------|------|------|
| <0.2 | 高度集中 | +3 分 |
| 0.2-0.4 | 相对集中 | +2 分 |
| >0.4 | 分散 | +1 分 |

---

### 2. 获利盘比例

```python
# 当前价下方的筹码比例 (获利盘)
profit_count = sum(1 for p in prices if p < current_price)
profit_ratio = profit_count / len(prices) * 100
```

**解读**:
| 获利盘比例 | 解读 |
|------------|------|
| >80% | 大部分获利，可能回调 |
| 50-80% | 多空平衡 |
| <20% | 大部分套牢，可能反弹 |

---

### 3. 平均成本

```python
avg_cost = sum(prices) / len(prices)
```

**用法**:
- 当前价 > 平均成本：多头市场
- 当前价 < 平均成本：空头市场

---

### 4. 筹码峰值

```python
# 最大筹码量对应的价格
max_chip = 0
peak_price = 0
for item in data:
    if item['筹码量'] > max_chip:
        max_chip = item['筹码量']
        peak_price = item['筹码价']
```

**解读**:
- 筹码峰值是强支撑/压力位
- 突破筹码峰 = 强势信号

---

### 5. 价格位置

| 位置 | 说明 | 信号 |
|------|------|------|
| **低位** | 价格<筹码峰*0.8 | 主力吸筹 |
| **震荡** | 筹码峰*0.8<价格<筹码峰*1.2 | 震荡整理 |
| **高位** | 价格>筹码峰*1.2 | 可能出货 |

---

## 🎯 选股应用

### 策略 1: 低位吸筹

```python
# 条件
if (concentration_ratio < 0.3 and  # 筹码集中
    current_price < avg_cost * 1.1 and  # 价格接均成本
    profit_ratio < 40):  # 获利盘少
    
    # 主力吸筹信号
    score += 3
```

### 策略 2: 突破筹码峰

```python
# 条件
if (current_price > peak_price * 1.1 and  # 突破筹码峰
    concentration_ratio < 0.4 and  # 筹码较集中
    volume > avg_volume * 2):  # 放量
    
    # 突破信号
    score += 2
```

### 策略 3: 筹码集中 + 资金流入

```python
# 综合评分
total_score = (
    technical_score * 0.4 +  # 技术面 40%
    fund_flow_score * 0.3 +  # 资金流 30%
    cyq_score * 0.3  # 筹码面 30%
)

if total_score >= 7:
    recommendation = '强烈推荐'
```

---

## 📊 综合评分系统 (更新后)

| 维度 | 满分 | 说明 |
|------|------|------|
| 基础金叉 | 1 分 | MA5 上穿 MA20 |
| 成交量 | 1 分 | 放量 1.5 倍 |
| 趋势 | 1 分 | 价格>MA200 |
| RSI | 1 分 | RSI 50-75 |
| MACD | 1 分 | MACD 金叉 |
| 均线斜率 | 1 分 | 均线向上 |
| 资金流 | 3 分 | 主力净流入 |
| **筹码分布** | **4 分** | **集中度 + 位置** |
| 波浪理论 | 2.5 分 | 艾略特波浪 |
| 江恩理论 | 2.5 分 | 江恩角度线 |
| **总计** | **17 分** | |

**评级标准**:
| 总分 | 评级 |
|------|------|
| >=12 | 强烈推荐 |
| >=10 | 推荐 |
| >=8 | 观望 |
| <8 | 回避 |

---

## 📁 使用示例

### 1. 获取筹码数据

```python
from data_source_manager import DataSourceManager

manager = DataSourceManager()

# 获取筹码分布
cyq_data = manager.get_cyq_data(symbol='000001', adjust='qfq')
```

### 2. 分析筹码

```python
from akshare_cyq_demo import analyze_cyq, cyq_score

# 分析
analysis = analyze_cyq(cyq_data)

# 评分
score = cyq_score(analysis)
```

### 3. 选股系统调用

```python
from stock_selector_v2 import EnhancedStockSelector

selector = EnhancedStockSelector()

# 获取资金流
fund_data = selector.data_source.get_fund_flow_rank(period='即时')

# 获取筹码
cyq_data = selector.data_source.get_cyq_data(symbol='000001')

# 分析
result = selector.analyze_stock(
    symbol='000001',
    fund_flow_data=fund_data[0] if fund_data else None,
    cyq_data=cyq_data
)
```

---

## ⚠️ 注意事项

1. **接口限流** - 东方财富有反爬，建议加延迟
2. **数据时效** - 筹码分布每日更新
3. **复权选择** - 建议使用前复权 (qfq)
4. **综合分析** - 筹码面需结合技术面、资金流

---

## 🔗 相关文件

| 文件 | 说明 |
|------|------|
| `akshare_cyq_demo.py` | CYQ 接口使用示例 |
| `data_source_manager.py` | 数据源管理器 (已集成) |
| `stock_selector_v2.py` | 选股系统 (已集成) |

---

**版本**: v3.1  
**最后更新**: 2026-03-27  
**状态**: ✅ 已完成集成
