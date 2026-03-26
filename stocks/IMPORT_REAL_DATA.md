# 📥 导入真实数据指南

**状态：等待 Tushare 权限恢复**

---

## ⚠️ 当前情况

### Tushare 状态

- **Token：** ✅ 已配置
- **积分：** ✅ 120 积分（已足够）
- **权限：** ⏳ 等待生效（可能需要重新登录）

### 解决方案

```bash
# 1. 重新登录 Tushare
访问 https://tushare.pro 重新登录

# 2. 等待几分钟让权限生效

# 3. 验证
python3 tushare_flow.py --check

# 4. 导入数据
python3 research_import.py --code 600000.SH
```

---

## 🔄 临时方案：使用腾讯财经真实行情

虽然 K 线 API 不可用，但可以使用实时行情：

```bash
# 获取真实主力流入排行（基于真实成交额估算）
python3 fund_flow.py --top 20
```

**数据说明：**
- ✅ 成交额是真实数据
- ⚠️ 主力净流入为估算值（已标注）
- ✅ 可用于研究分析

---

## 📊 使用现有真实数据

### 方案 1：从缓存导入

```bash
# 如果之前获取过数据，可以从缓存导入
python3 research_import.py --from-cache 600000.SH
```

### 方案 2：手动导入 CSV

从其他平台下载真实数据：

1. 访问 https://quote.eastmoney.com
2. 搜索股票代码
3. 下载历史数据 CSV
4. 导入：

```bash
python3 research_import.py --csv downloaded_data.csv --code 600000.SH
```

---

## ✅ Tushare 恢复后的操作

```bash
# 1. 验证权限
python3 tushare_flow.py --check

# 2. 导入单只股票
python3 research_import.py --code 600000.SH --days 250

# 3. 导入多只股票
python3 research_import.py --all --days 60

# 4. 验证导入
python3 research_db.py --stats

# 5. 分析
python3 research_simple.py --code 600000.SH
```

---

## 📁 数据源优先级

1. **Tushare Pro** ⭐⭐⭐⭐⭐
   - 真实主力数据
   - 需要 120 积分
   - 等待权限恢复

2. **腾讯财经** ⭐⭐⭐
   - 真实成交额
   - 主力为估算
   - 立即可用

3. **CSV 导入** ⭐⭐⭐⭐
   - 取决于数据源
   - 需手动下载
   - 灵活定制

---

**最后更新：2026-03-17 23:40**

**状态：⏳ 等待 Tushare 权限恢复**
