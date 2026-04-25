# AKShare 适合选股的接口汇总

**整理时间**: 2026-03-27  
**文档**: https://akshare.akfamily.xyz/data/stock/stock.html

---

## 🎯 核心选股接口 (已测试✅)

### 1. 资金流类 ⭐⭐⭐⭐⭐

| 接口 | 功能 | 状态 | 推荐度 |
|------|------|------|--------|
| `stock_fund_flow_individual` | 个股资金流排行 | ✅ 已测试 | ⭐⭐⭐⭐⭐ |
| `stock_fund_flow_rank` | 资金流排名 | ⚠️ 待测试 | ⭐⭐⭐⭐ |
| `stock_main_fund_flow` | 主力资金流 | ⚠️ 待测试 | ⭐⭐⭐⭐ |

**使用示例**:
```python
# 即时资金流
ak.stock_fund_flow_individual(symbol='即时')

# 5 日资金流
ak.stock_fund_flow_individual(symbol='5 日排行')
```

---

### 2. 行情数据类 ⭐⭐⭐⭐⭐

| 接口 | 功能 | 状态 | 推荐度 |
|------|------|------|--------|
| `stock_zh_a_spot_em` | A 股实时行情 | ⚠️ 限流 | ⭐⭐⭐⭐ |
| `stock_zh_a_hist` | A 股历史行情 | ✅ 已测试 | ⭐⭐⭐⭐⭐ |
| `stock_zh_a_hist_min_em` | 分时行情 | ⚠️ 待测试 | ⭐⭐⭐ |

**使用示例**:
```python
# 历史行情
ak.stock_zh_a_hist(symbol='600152', period='daily', adjust='qfq')
```

---

### 3. 技术指标类 ⭐⭐⭐⭐

| 接口 | 功能 | 状态 | 推荐度 |
|------|------|------|--------|
| `stock_all_not_ful` | 非停牌股票 | ⚠️ 待测试 | ⭐⭐⭐⭐ |
| `stock_zh_a_st_em` | ST 股票列表 | ⚠️ 待测试 | ⭐⭐⭐ |

---

### 4. 基本面类 ⭐⭐⭐⭐

| 接口 | 功能 | 状态 | 推荐度 |
|------|------|------|--------|
| `stock_individual_basic_info_xq` | 个股基本信息 (雪球) | ✅ 已测试 | ⭐⭐⭐⭐ |
| `stock_info_a_code_name` | A 股代码名称 | ⚠️ 待测试 | ⭐⭐⭐⭐ |
| `stock_financial_abstract` | 财务摘要 | ⚠️ 待测试 | ⭐⭐⭐⭐ |
| `stock_pe_and_pb` | PE/PB 估值 | ⚠️ 待测试 | ⭐⭐⭐⭐ |

---

### 5. 板块概念类 ⭐⭐⭐⭐

| 接口 | 功能 | 状态 | 推荐度 |
|------|------|------|--------|
| `stock_board_industry_name_em` | 行业板块 | ✅ 已测试 | ⭐⭐⭐⭐ |
| `stock_board_concept_name_em` | 概念板块 | ⚠️ 待测试 | ⭐⭐⭐⭐ |
| `stock_sector_fund_flow_rank` | 板块资金流 | ⚠️ 待测试 | ⭐⭐⭐⭐ |

---

### 6. 龙虎榜类 ⭐⭐⭐

| 接口 | 功能 | 状态 | 推荐度 |
|------|------|------|--------|
| `stock_lhb_detail_em` | 龙虎榜详情 | ⚠️ 待测试 | ⭐⭐⭐ |
| `stock_lhb_stock_detail_em` | 个股龙虎榜 | ⚠️ 待测试 | ⭐⭐⭐ |

---

### 7. 融资融券类 ⭐⭐⭐

| 接口 | 功能 | 状态 | 推荐度 |
|------|------|------|--------|
| `stock_margin_sse` | 上交所融资融券 | ⚠️ 待测试 | ⭐⭐⭐ |
| `stock_margin_detail_sse` | 融资融券明细 | ⚠️ 待测试 | ⭐⭐⭐ |

---

## 🚀 推荐选股流程

```
┌─────────────────────────────────────────────────────────┐
│  第 1 步：获取股票池                                      │
│  - stock_info_a_code_name (全 A 股列表)                  │
│  - stock_all_not_ful (非停牌股票)                        │
├─────────────────────────────────────────────────────────┤
│  第 2 步：资金流筛选                                      │
│  - stock_fund_flow_individual (资金流排行)              │
│  - 筛选主力净流入前 100 名                                │
├─────────────────────────────────────────────────────────┤
│  第 3 步：技术面分析                                      │
│  - stock_zh_a_hist (获取历史行情)                       │
│  - 计算均线、RSI、MACD 等指标                            │
├─────────────────────────────────────────────────────────┤
│  第 4 步：基本面筛选                                      │
│  - stock_individual_basic_info_xq (基本信息)            │
│  - stock_pe_and_pb (估值)                               │
│  - stock_financial_abstract (财务)                      │
├─────────────────────────────────────────────────────────┤
│  第 5 步：综合评分                                        │
│  - 资金流 (30%) + 技术面 (40%) + 基本面 (30%)           │
│  - 输出 Top 20 推荐股票                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 已集成接口

| 接口 | 集成文件 | 状态 |
|------|---------|------|
| `stock_fund_flow_individual` | `akshare_fund_flow.py` | ✅ 完成 |
| `stock_zh_a_hist` | `data_source_manager.py` | ✅ 完成 |
| `stock_individual_spot_xq` | `data_source_manager.py` | ✅ 完成 |
| `stock_individual_basic_info_xq` | 测试脚本 | ✅ 完成 |

---

## ⚠️ 限流接口

| 接口 | 限流程度 | 建议 |
|------|---------|------|
| `stock_zh_a_spot_em` | 🔴 严重 | 使用缓存 |
| `stock_fund_flow_individual` | 🟡 中等 | 加延迟 |
| `stock_individual_spot_xq` | 🟡 中等 | 需要 Token |

---

## 💡 选股策略建议

### 策略 1: 资金流 + 技术面

```python
# 1. 获取资金流前 100
fund_flow = ak.stock_fund_flow_individual(symbol='即时')
top100 = fund_flow.head(100)

# 2. 获取历史行情
for stock in top100:
    hist = ak.stock_zh_a_hist(symbol=stock['股票代码'])
    # 3. 计算技术指标
    # 4. 筛选金叉 + 放量
```

### 策略 2: 基本面 + 估值

```python
# 1. 获取全 A 股列表
all_stocks = ak.stock_info_a_code_name()

# 2. 筛选低估值
for stock in all_stocks:
    pe_pb = ak.stock_pe_and_pb(symbol=stock)
    # 筛选 PE<20, PB<3
```

### 策略 3: 板块轮动

```python
# 1. 获取行业板块
sectors = ak.stock_board_industry_name_em()

# 2. 获取板块资金流
sector_flow = ak.stock_sector_fund_flow_rank()

# 3. 选择资金流入前 3 的板块
# 4. 从板块中选个股
```

---

## 🔗 相关文档

- [AKShare 官方文档](https://akshare.akfamily.xyz/)
- [股票数据接口](https://akshare.akfamily.xyz/data/stock/stock.html)
- [资金流接口](https://akshare.akfamily.xyz/data/stock/stock.html#stock-fund-flow-individual)

---

**最后更新**: 2026-03-27  
**已测试接口**: 5 个  
**待测试接口**: 15+ 个
