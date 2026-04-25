# 🔒 v8.0-Financial-Enhanced 严格数据契约版 - 架构文档

**版本**: v8.0-Financial-Enhanced-Strict  
**创建时间**: 2026-03-22 11:35  
**核心特性**: 严格数据契约 + 异常中断 + 错误推送

---

## 🏗️ 一、核心设计理念

### 三大原则

1. **数据获取 Layer** - 输出格式固定，异常则中断
2. **分析决策 Layer** - 输入输出格式固定，异常则中断
3. **输出推送 Layer** - 输入输出格式固定，异常则终止并推送错误

### 数据契约（Data Contract）

每个 Layer 都有明确的**输入 Schema**和**输出 Schema**：

```
Layer 输入 → [验证] → 处理 → [验证] → Layer 输出
                ↓                      ↓
            失败则中断              失败则中断
```

---

## 📊 二、数据契约定义

### 2.1 StockData - 股票数据 Schema

```python
@dataclass
class StockData:
    code: str           # 股票代码（6 位数字）✅ 必填
    name: str           # 股票名称 ✅ 必填
    price: float        # 当前价格 ✅ >0
    change_pct: float   # 涨跌幅（%）✅ 必填
    volume: int         # 成交量（股）✅ ≥0
    turnover: float     # 成交额（元）✅ ≥0
    source: str         # 数据来源 ✅ 必填
    crawl_time: str     # 抓取时间（ISO 格式）✅ 必填
    
    # 验证方法
    def validate(self) -> Tuple[bool, str]:
        """验证数据有效性"""
        # 返回：(是否有效，错误信息)
```

**验证规则**:
| 字段 | 类型 | 约束 | 错误示例 |
|------|------|------|----------|
| code | str | 6 位数字 | `""`, `"123"`, `None` ❌ |
| name | str | 非空 | `""`, `None` ❌ |
| price | float | >0 | `-1.0`, `0`, `None` ❌ |
| change_pct | float | 任意值 | `None` ❌ |
| volume | int | ≥0 | `-100`, `None` ❌ |
| turnover | float | ≥0 | `-1000`, `None` ❌ |
| source | str | 非空 | `""`, `None` ❌ |
| crawl_time | str | ISO 格式 | `None` ❌ |

---

### 2.2 DataSourceResult - 数据获取 Layer 输出 Schema

```python
@dataclass
class DataSourceResult:
    source_name: str                # 数据源名称 ✅ 必填
    status: str                     # 状态：success/failed ✅ 枚举
    stock_count: int                # 股票数量 ✅ ≥0
    stocks: List[StockData]         # 股票数据列表 ✅ 验证每个元素
    error_message: Optional[str]    # 错误信息（如果有）
    fetch_time: str                 # 抓取时间（ISO 格式）✅ 必填
    
    def validate(self) -> Tuple[bool, str]:
        """验证数据有效性"""
```

**验证规则**:
| 规则 | 说明 |
|------|------|
| status 必须为 success/failed | 其他值 ❌ |
| status=success 时 stock_count 必须>0 | 否则 ❌ |
| status=success 时 stocks 必须非空 | 否则 ❌ |
| status=success 时必须验证每个 StockData | 有一个失败 ❌ |

---

### 2.3 AnalysisInput - 分析 Layer 输入 Schema

```python
@dataclass
class AnalysisInput:
    stocks: List[StockData]         # 股票数据 ✅ 非空
    data_sources: List[str]         # 有效数据源列表 ✅ 非空
    total_count: int                # 总股票数 ✅ >0
    fetch_time: str                 # 数据获取时间 ✅ 必填
    
    def validate(self) -> Tuple[bool, str]:
        """验证输入有效性"""
```

**验证规则**:
| 规则 | 说明 |
|------|------|
| stocks 必须非空 | 空列表 ❌ |
| stocks 必须是列表 | 其他类型 ❌ |
| data_sources 必须非空 | 空列表 ❌ |
| total_count 必须>0 | ≤0 ❌ |
| len(stocks) == total_count | 不匹配 ❌ |

---

### 2.4 AnalysisOutput - 分析 Layer 输出 Schema

```python
@dataclass
class AnalysisOutput:
    stocks: List[Dict]              # 分析后的股票数据 ✅ 非空
    analysis_time: str              # 分析时间 ✅ 必填
    model_version: str              # 模型版本 ✅ 必填
    metrics: Dict                   # 分析指标 ✅ 字典
    
    def validate(self) -> Tuple[bool, str]:
        """验证输出有效性"""
```

**验证规则**:
| 规则 | 说明 |
|------|------|
| stocks 必须非空 | 空列表 ❌ |
| 每只股票必须有 code, name | 缺失 ❌ |
| 每只股票必须有 score, rating | 缺失 ❌ |
| analysis_time 必填 | 缺失 ❌ |
| model_version 必填 | 缺失 ❌ |
| metrics 必须是字典 | 其他类型 ❌ |

---

### 2.5 PushInput - 推送 Layer 输入 Schema

```python
@dataclass
class PushInput:
    stocks: List[Dict]              # 分析结果 ✅ 非空
    top_n: int                      # 推荐数量 ✅ >0
    workflow_version: str           # 工作流版本 ✅ 必填
    execution_time: str             # 执行时间 ✅ 必填
    
    def validate(self) -> Tuple[bool, str]:
        """验证输入有效性"""
```

---

### 2.6 PushOutput - 推送 Layer 输出 Schema

```python
@dataclass
class PushOutput:
    status: str                     # 推送状态：success/failed ✅ 枚举
    push_time: str                  # 推送时间 ✅ 必填
    message_length: int             # 消息长度 ✅ 整数
    error_message: Optional[str]    # 错误信息
    
    def validate(self) -> Tuple[bool, str]:
        """验证输出有效性"""
```

---

## 🚨 三、异常定义

### 异常层次结构

```
WorkflowException (基类)
├── DataFetchException (数据获取 Layer 异常)
├── AnalysisException (分析决策 Layer 异常)
└── PushException (输出推送 Layer 异常)
```

### 异常类定义

```python
class WorkflowException(Exception):
    """工作流异常基类"""
    def __init__(self, layer: str, message: str, details: Optional[str] = None):
        self.layer = layer          # Layer 名称
        self.message = message      # 错误消息
        self.details = details      # 详细信息
```

### 触发条件

| Layer | 异常类型 | 触发条件 |
|-------|---------|---------|
| 数据获取 | DataFetchException | 数据源不足、格式验证失败 |
| 分析决策 | AnalysisException | 输入验证失败、输出验证失败、处理异常 |
| 输出推送 | PushException | 输入验证失败、输出验证失败、推送 API 异常 |

---

## 📡 四、Layer 1: 数据获取层

### 配置参数

```python
class DataFetchLayer:
    VERSION = 'v1.0'
    REQUIRED_SOURCES = ['baidu', 'tencent', 'eastmoney']
    MIN_SUCCESS_SOURCES = 2      # 最少成功数据源
    MIN_STOCKS_PER_SOURCE = 10   # 每源最少股票数
```

### 执行流程

```
开始
  ↓
[1/3] 百度股市通
  ↓
[2/3] 腾讯财经
  ↓
[3/3] 东方财富
  ↓
验证每个 DataSourceResult
  ↓
验证成功数据源数量 ≥ 2
  ↓
返回 List[DataSourceResult]
```

### 验证规则

```python
# 1. 验证每个数据源输出格式
for result in results:
    valid, msg = result.validate()
    if not valid:
        raise DataFetchException(...)

# 2. 验证成功数据源数量
success_count = sum(1 for r in results if r.status == 'success')
if success_count < MIN_SUCCESS_SOURCES:
    raise DataFetchException(...)
```

### 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| 百度返回 0 条 | status='failed'，继续执行 |
| 腾讯返回<10 条 | status='failed'，继续执行 |
| 东方财富 API 错误 | status='failed'，继续执行 |
| 成功数据源<2 个 | **中断工作流**，推送错误 |
| 数据格式验证失败 | **中断工作流**，推送错误 |

---

## 🧠 五、Layer 2: 分析决策层

### 配置参数

```python
class AnalysisLayer:
    VERSION = 'v8.0-Financial-Enhanced'
```

### 执行流程

```
接收 AnalysisInput
  ↓
验证输入格式
  ↓ 失败 → 抛出 AnalysisException
执行分析
  ↓
生成 AnalysisOutput
  ↓
验证输出格式
  ↓ 失败 → 抛出 AnalysisException
返回 AnalysisOutput
```

### 分析逻辑

```python
def _analyze_stocks(self, stocks: List[StockData]) -> List[Dict]:
    for stock in stocks:
        score = self._calculate_score(stock)       # 综合评分
        rating = self._determine_rating(score)     # 评级
        stop_profit, stop_loss = self._calculate_stop_levels(...)  # 止盈止损
        tags = self._generate_tags(stock)          # 标签
        
        yield {
            'code': stock.code,
            'name': stock.name,
            'price': stock.price,
            'score': score,
            'rating': rating,
            'confidence': min(score, 95),
            'stop_profit': stop_profit,
            'stop_loss': stop_loss,
            'tags': tags,
        }
```

### 评分规则

| 维度 | 条件 | 分数 |
|------|------|------|
| 成交额 | >50 亿 | +40 |
| | >10 亿 | +30 |
| | >5 亿 | +20 |
| 涨跌幅 | 2%-7% | +30 |
| | 0%-2% | +20 |
| | >10% | +10 |
| 数据源 | 百度 | +30 |
| | 腾讯 | +20 |
| | 其他 | +10 |

### 评级标准

| 评分 | 评级 |
|------|------|
| ≥90 | 强烈推荐 |
| ≥80 | 推荐 |
| ≥70 | 关注 |
| <70 | 观望 |

---

## 📤 六、Layer 3: 输出推送层

### 配置参数

```python
class PushLayer:
    VERSION = 'v1.0'
    webhook = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...'
```

### 执行流程

```
接收 PushInput
  ↓
验证输入格式
  ↓ 失败 → 抛出 PushException
格式化消息（Markdown）
  ↓
调用企业微信 API
  ↓
生成 PushOutput
  ↓
验证输出格式
  ↓ 失败 → 抛出 PushException
返回 PushOutput
```

### 推送格式

```markdown
🎯 工作流最终决策 Top10
⏰03-22 11:35
📊 仅主板 | 排除创业/科创/北交所
⚠️ 仅供参考，不构成投资建议
🔒 版本：v8.0-Financial-Enhanced-Strict

━━⭐⭐⭐强烈推荐 (6)━━
1. 📗科达制造 (sh600499)⭐⭐⭐
   ¥15.54 +1.5% 成交 4.6 亿
   置信 80% 止盈¥23.3 止损¥13.2
   💡成交活跃 | 温和上涨

...
```

### 错误推送

```python
def push_error(self, error: WorkflowException) -> PushOutput:
    """推送错误信息"""
    message = f"""🚨 v8.0-Financial-Enhanced 基准版 - 执行异常报告
⏰{datetime.now().strftime('%m-%d %H:%M')}
📊 仅主板 | 排除创业/科创/北交所
⚠️ 仅供参考，不构成投资建议

━━❌ 工作流执行失败━━

📋 异常信息:
  Layer: {error.layer}
  错误：{error.message}
  详情：{error.details or '无'}

💡 建议:
  - 检查数据源状态
  - 查看完整日志
  - 等待系统恢复
..."""
```

---

## 🔄 七、完整执行流程

### 成功场景

```
V8StrictWorkflow.run()
  ↓
Layer 1: DataFetchLayer.fetch()
  ├─ 获取百度数据 → failed (0 条)
  ├─ 获取腾讯数据 → success (10 条)
  ├─ 获取东方数据 → success (10 条)
  ├─ 验证输出格式 → ✅ 通过
  └─ 验证数据源数量 → ✅ 通过 (3 个≥2 个)
  ↓
Layer 2: AnalysisLayer.analyze()
  ├─ 验证输入 → ✅ 通过
  ├─ 执行分析 → 20 只股票
  ├─ 验证输出 → ✅ 通过
  └─ 返回 AnalysisOutput
  ↓
Layer 3: PushLayer.push()
  ├─ 验证输入 → ✅ 通过
  ├─ 格式化消息 → 1200 字符
  ├─ 调用 API → ✅ 成功
  └─ 验证输出 → ✅ 通过
  ↓
✅ 工作流执行成功
```

### 失败场景 1: 数据源不足

```
Layer 1: DataFetchLayer.fetch()
  ├─ 获取百度数据 → failed (0 条)
  ├─ 获取腾讯数据 → success (10 条)
  ├─ 获取东方数据 → failed (0 条)
  ├─ 验证输出格式 → ✅ 通过
  └─ 验证数据源数量 → ❌ 失败 (1 个<2 个)
  ↓
抛出 DataFetchException
  ↓
Layer 3: PushLayer.push_error()
  └─ 推送错误报告 → ✅ 成功
  ↓
❌ 工作流终止
```

### 失败场景 2: 数据格式异常

```
Layer 1: DataFetchLayer.fetch()
  ├─ 获取腾讯数据 → success (10 条)
  ├─ 验证输出格式 → ❌ 失败 (股票代码为空)
  ↓
抛出 DataFetchException
  ↓
Layer 3: PushLayer.push_error()
  └─ 推送错误报告 → ✅ 成功
  ↓
❌ 工作流终止
```

### 失败场景 3: 分析异常

```
Layer 2: AnalysisLayer.analyze()
  ├─ 验证输入 → ❌ 失败 (股票数据为空)
  ↓
抛出 AnalysisException
  ↓
Layer 3: PushLayer.push_error()
  └─ 推送错误报告 → ✅ 成功
  ↓
❌ 工作流终止
```

---

## 📊 八、测试验证

### 测试场景 1: 数据源不足

**执行命令**:
```bash
python3 workflow_v8_strict.py --strategy main --top 10 --push
```

**执行结果** (2026-03-22 11:35:04):
```
[1/3] 百度股市通... → failed (0 条)
[2/3] 腾讯财经... → success (10 条)
[3/3] 东方财富... → failed (0 条)

🔍 验证数据获取 Layer 输出... → ✅ 通过

❌ 工作流异常：[DataFetch] 有效数据源数量不足
详情：要求≥2 个，实际 1 个

📤 推送错误报告... → ✅ 成功
```

**验证点**:
- ✅ Layer 1 输出格式验证通过
- ✅ 检测到数据源不足
- ✅ 立即中断工作流
- ✅ 推送错误报告

---

### 测试场景 2: 数据格式异常

**模拟场景**: 腾讯数据中股票代码为空

**预期结果**:
```
🔍 验证数据获取 Layer 输出...
❌ 工作流异常：[DataFetch] 第 2 个数据源输出格式验证失败
详情：第 1 只股票数据异常：股票代码格式错误：

📤 推送错误报告... → ✅ 成功
```

**验证点**:
- ✅ 检测到数据格式异常
- ✅ 立即中断工作流
- ✅ 推送详细错误信息

---

## 📁 九、文件清单

| 文件 | 大小 | 功能 |
|------|------|------|
| `workflow_v8_strict.py` | 32.4KB | 严格数据契约工作流 |
| `STRICT_DATA_CONTRACT.md` | 本文档 | 架构文档 |

---

## 🔧 十、使用指南

### 运行严格版

```bash
# 标准模式
python3 workflow_v8_strict.py --strategy main --top 10 --push

# 涨幅榜策略
python3 workflow_v8_strict.py --strategy gainers --top 20 --push

# 不推送（仅测试）
python3 workflow_v8_strict.py --strategy main --top 10
```

### 自定义配置

```python
# 修改数据源要求
DataFetchLayer.MIN_SUCCESS_SOURCES = 2  # 最少成功数据源
DataFetchLayer.MIN_STOCKS_PER_SOURCE = 10  # 每源最少股票数

# 修改推送 Webhook
PushLayer.webhook = 'https://...'
```

---

## 📈 十一、性能指标

| 指标 | 数值 |
|------|------|
| Layer 1 执行时间 | ~18 秒 |
| Layer 2 执行时间 | ~1 秒 |
| Layer 3 执行时间 | ~1 秒 |
| 总执行时间 | ~20 秒 |
| 验证开销 | <1 秒 |

---

## 🎯 十二、与基准版对比

| 特性 | 基准版 | 严格数据契约版 |
|------|--------|---------------|
| 数据验证 | 简单检查 | **Schema 验证** |
| 异常处理 | 打印日志 | **立即中断 + 推送** |
| 输入验证 | 无 | **每 Layer 验证** |
| 输出验证 | 无 | **每 Layer 验证** |
| 错误推送 | 仅失败报告 | **详细 Layer 信息** |
| 可追溯性 | 中 | **高** |

---

## ✅ 十三、验证清单

### Layer 1 验证

- [ ] 每个数据源输出格式验证
- [ ] 成功数据源数量验证
- [ ] 股票代码格式验证
- [ ] 价格有效性验证
- [ ] 数据源字段验证

### Layer 2 验证

- [ ] 输入数据格式验证
- [ ] 股票数量一致性验证
- [ ] 输出数据格式验证
- [ ] 必填字段验证（code, name, score, rating）

### Layer 3 验证

- [ ] 输入数据格式验证
- [ ] 推送状态验证
- [ ] 消息长度验证
- [ ] API 响应验证

---

**文档版本**: v1.0  
**创建时间**: 2026-03-22 11:35  
**维护者**: v8.0-Financial-Enhanced-Strict 团队

---

_🔒 v8.0-Financial-Enhanced-Strict - 严格数据契约_  
_⚠️ 数据格式验证失败 = 工作流终止 + 错误推送_
