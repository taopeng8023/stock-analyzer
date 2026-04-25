# 📊 多数据源股票筛选工作流

**创建时间**: 2026-03-20  
**状态**: ✅ 已激活

---

## 🎯 数据源配置

### 已激活数据源

| 优先级 | 数据源 | 类型 | 状态 | 说明 |
|--------|--------|------|------|------|
| **P0** | 腾讯财经 | 实时行情 | ✅ 可用 | 已有，实时行情/K 线 |
| **P0** | 百度股市通 | 资金流 | ✅ 可用 | 已有，资金流排行 |
| **P0** | 东方财富 | 板块/北向 | ✅ 可用 | 已有，板块资金流 |
| **P1** | 新浪财经 | 实时行情 | ✅ 新增 | 涨幅榜/实时报价 |
| **P1** | BaoStock | 历史 K 线 | ✅ 新增 | 历史数据/财务指标 |
| **P2** | AKShare | 综合数据 | ⚠️ 兼容性问题 | 同花顺资金流/多市场 |
| **P2** | Tushare | 规范数据 | ⚠️ 待激活 | 积分不足 (100/120) |

---

## 🚀 快速开始

### 1. 多数据源汇总

```bash
cd /home/admin/.openclaw/workspace/stocks

# 获取所有数据源数据
python3 data_sources.py --source all --top 20
```

### 2. 单数据源查询

```bash
# 新浪财经 - 涨幅榜
python3 data_sources.py --source sina --top 20

# 新浪财经 - 指定股票
python3 data_sources.py --source sina --codes sh600000,sz000001

# BaoStock - 历史 K 线
python3 data_sources.py --source baostock --code 600000.SH --days 60

# AKShare - 资金流排行 (Python 3.8+)
python3.8 data_sources.py --source akshare --top 20
```

### 3. 原有命令 (保持兼容)

```bash
# 主力资金流 (腾讯估算)
python3 fund_flow.py --top 20

# 股票排行
python3 local_crawler.py --query top10 --top 20

# K 线数据
python3 local_crawler.py --kline sh600000 --count 60
```

---

## 📋 工作流说明

### 全网筛选流程

```
1. 数据采集
   ├── 腾讯财经 → 实时行情、成交额
   ├── 百度股市通 → 资金流排行
   ├── 新浪财经 → 涨幅榜
   ├── 东方财富 → 板块资金流、北向资金
   ├── BaoStock → 历史 K 线、财务指标
   └── AKShare → 同花顺资金流 (安装后)

2. 数据清洗
   ├── 统一字段格式
   ├── 去重合并
   └── 异常值过滤

3. 筛选策略
   ├── 主力净流入排行
   ├── 涨幅排行
   ├── 成交量排行
   ├── 成交额排行
   └── 综合评分

4. 输出结果
   ├── 终端打印
   ├── JSON 缓存
   ├── CSV 导出
   └── 微信推送 (可选)
```

---

## 🔧 新增文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `data_sources.py` | 多数据源统一接口 | ✅ 已创建 |
| `MULTI_SOURCE_WORKFLOW.md` | 本文档 | ✅ 已创建 |

---

## 📦 依赖安装

### 已完成

```bash
# BaoStock (Python 3.6)
pip3 install baostock --user

# AKShare (需要 Python 3.8+)
python3.8 -m pip install akshare --user
```

### 验证安装

```bash
# 测试 BaoStock
python3 data_sources.py --source baostock --code 600000.SH --days 10

# 测试 AKShare
python3.8 data_sources.py --source akshare --top 10
```

---

## 🎯 筛选策略

### 策略 1: 主力净流入

```bash
# 百度股市通
python3 local_crawler.py --query main --top 20

# AKShare (更准确)
python3.8 data_sources.py --source akshare --top 20
```

### 策略 2: 综合评分

```bash
# 基于成交额 + 涨跌幅 + 成交量
python3 local_crawler.py --query top10 --top 20
```

### 策略 3: 涨幅监控

```bash
# 新浪财经涨幅榜
python3 data_sources.py --source sina --top 20
```

### 策略 4: 历史回测

```bash
# BaoStock 获取 60 天历史数据
python3 data_sources.py --source baostock --code 600000.SH --days 60
```

---

## 📊 数据对比

### 资金流数据准确性

| 数据源 | 准确性 | 延迟 | 覆盖范围 |
|--------|--------|------|---------|
| AKShare (同花顺) | ⭐⭐⭐⭐⭐ | 实时 | 全部 A 股 |
| 百度股市通 | ⭐⭐⭐⭐ | 实时 | 全部 A 股 |
| 腾讯估算 | ⭐⭐⭐ | 实时 | 全部 A 股 |
| Tushare | ⭐⭐⭐⭐⭐ | 日终 | 全部 A 股 |

### 历史数据完整性

| 数据源 | 年限 | 复权 | 财务指标 |
|--------|------|------|---------|
| BaoStock | 20+ 年 | ✅ | ✅ |
| AKShare | 10+ 年 | ✅ | ✅ |
| 腾讯财经 | 1 年 | ⚠️ 部分 | ❌ |

---

## ⚠️ 注意事项

1. **AKShare 需要 Python 3.8+**
   - 系统已安装 Python 3.8
   - 使用 `python3.8` 命令运行

2. **数据源优先级**
   - 真实数据 > 估算数据
   - 多数据源交叉验证

3. **访问频率限制**
   - 单个数据源请求间隔 >= 0.5 秒
   - 批量获取时使用缓存

4. **数据标注**
   - 💰 = 真实数据
   - 📊 = 估算数据

---

## 🔄 下一步

### 待完成

- [ ] AKShare 安装验证
- [ ] 整合到自动推送流程
- [ ] 添加数据质量监控
- [ ] Tushare 积分充值 (120 分)

### 可选扩展

- [ ] 添加 pytdx 实时行情
- [ ] 集成量化平台 API
- [ ] 添加预警功能
- [ ] 数据可视化图表

---

## 📞 帮助

查看详细代码注释:
```bash
head -100 data_sources.py
```

测试单个数据源:
```bash
python3 data_sources.py --help
```

---

**最后更新**: 2026-03-20 09:30
