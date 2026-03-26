# ⚠️ 研究系统数据政策

**严格遵守：所有股票交易数据必须来自真实市场数据源**

---

## 🚫 禁止行为

### 严禁生成或使用模拟数据

**无论什么场景，都禁止：**

- ❌ 生成随机股票价格数据
- ❌ 伪造交易量/成交额
- ❌ 模拟资金流数据
- ❌ 创建虚假 K 线
- ❌ 使用"示例数据"、"测试数据"名义生成模拟行情

**原因：**
1. 可能误导研究结论
2. 违反 DATA_POLICY.md 政策
3. 可能被误用于交易决策
4. 违背诚信原则

---

## ✅ 允许的数据源

### 1. Tushare Pro（推荐）

**状态：** ✅ 真实数据

**获取：**
```bash
# 1. 注册 https://tushare.pro
# 2. 获取 Token（需要 120 积分解锁资金流）
# 3. 配置
python3 tushare_flow.py --config <your_token>

# 4. 导入数据
python3 research_import.py --code 600000.SH
```

**数据质量：** ⭐⭐⭐⭐⭐

---

### 2. 腾讯财经（估算）

**状态：** ⚠️ 基于真实成交额估算

**说明：**
- 使用真实成交额数据
- 主力净流入为估算值（成交额×系数）
- 已明确标注"估算"

**使用：**
```bash
python3 fund_flow.py --top 20 --source tencent
```

**数据质量：** ⭐⭐⭐

---

### 3. CSV 导入

**状态：** ✅ 取决于数据来源

**要求：**
- 必须来自合法数据源
- 不得是生成的模拟数据
- 需标注数据来源

**使用：**
```bash
python3 research_import.py --csv data.csv --code 600000.SH
```

---

### 4. 现有缓存

**状态：** ✅ 之前获取的真实数据

**使用：**
```bash
python3 research_import.py --from-cache 600000.SH
```

---

## 📋 数据导入流程

### 推荐流程

```bash
# 1. 配置 Tushare（获取真实数据）
python3 tushare_flow.py --config <your_token>

# 2. 验证 Token
python3 tushare_flow.py --check

# 3. 导入数据
python3 research_import.py --code 600000.SH --days 250

# 4. 验证数据
python3 research_db.py --query 600000.SH

# 5. 分析
python3 research_simple.py --code 600000.SH
```

---

## 🔍 数据验证

### 检查数据真实性

```bash
# 查看数据来源
python3 research_db.py --query 600000.SH

# 检查数据完整性
python3 research_db.py --stats
```

### 真实数据特征

- ✅ 价格符合市场范围（A 股通常 1-500 元）
- ✅ 成交量合理（通常 10 万 -1000 万手）
- ✅ 日期连续（跳过周末节假日）
- ✅ 有明确数据来源标注

### 模拟数据特征（禁止！）

- ❌ 价格异常（如 0.01 元或 10000 元）
- ❌ 成交量异常（如 0 或天文数字）
- ❌ 日期不连续
- ❌ 无数据来源标注

---

## 📁 文件更新

### 已修改

| 文件 | 修改内容 |
|------|---------|
| `research_import.py` | 禁用 `--sample` 功能 |
| `research_db.py` | 仅接受真实数据导入 |
| `RESEARCH_GUIDE.md` | 更新数据源说明 |

### 新增

| 文件 | 说明 |
|------|------|
| `RESEARCH_DATA_POLICY.md` | 本文档 |

---

## ⚠️ 违规处理

如发现使用模拟数据：

1. **立即删除** 所有模拟数据
2. **重新导入** 真实数据
3. **记录原因** 避免再次发生
4. **学习政策** DATA_POLICY.md

---

## 💡 替代方案

### 如果无法获取真实数据

**方案 1：使用公开数据集**

```bash
# Kaggle 股票数据集
# https://www.kaggle.com/datasets?tags=13207-Stock+Market

# 下载后导入
python3 research_import.py --csv kaggle_data.csv --code AAPL
```

**方案 2：使用历史真实数据**

```bash
# Yahoo Finance 历史数据
# https://finance.yahoo.com/

# 下载 CSV 后导入
python3 research_import.py --csv yahoo_data.csv --code AAPL
```

**方案 3：等待 Tushare 积分足够**

- 注册送 100 积分
- 每日签到 +10 积分
- 2 天后达到 120 积分
- 解锁资金流接口

---

## 📞 帮助

**政策咨询：**
- DATA_POLICY.md - 总数据政策
- RESEARCH_DATA_POLICY.md - 本研究系统政策

**技术支持：**
- RESEARCH_GUIDE.md - 使用指南
- TUSHARE_SETUP.md - Tushare 配置

---

**最后更新：2026-03-17 23:35**

**状态：✅ 模拟数据功能已禁用**

**⚠️ 严格遵守：仅使用真实市场数据**
