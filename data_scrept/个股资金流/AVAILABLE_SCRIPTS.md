# 东方财富个股资金流数据 - 可用脚本说明

> ⚠️ **重要提示**: 东方财富网有反爬虫机制，直接 API 访问受限。**推荐使用 browser 工具手动获取**。

---

## ✅ 可用脚本清单

### 🥇 首选方案：Browser 工具手动获取

**说明**: 使用 OpenClaw browser 工具访问东方财富网页面，手动完成验证码后提取数据。

**支持排行类型**:
- ✅ 今日排行（当日数据）
- ✅ 3 日排行（近 3 日累计）
- ✅ 5 日排行（近 5 日累计）
- ✅ 10 日排行（近 10 日累计）

**相关脚本/文档**:
- `stock_capital_flow_browser.py` - Browser 工具使用说明
- `fetch_multi_day_capital_flow.py` - 多日排行获取脚本
- `MULTI_DAY_GUIDE.md` - 多日排行详细指南
- `QUICK_START.md` - 快速开始指南

**操作步骤**:

```bash
# 1. 打开东方财富网个股资金流页面
browser open https://data.eastmoney.com/zjlx/detail.html

# 2. 在浏览器中手动完成验证码

# 3. 等待数据加载
browser act <targetId> wait --time-ms 10000

# 4. 滚动页面触发数据加载
browser act <targetId> evaluate --fn "() => { window.scrollTo(0, document.body.scrollHeight); }"
browser act <targetId> wait --time-ms 5000

# 5. 提取数据（完整命令见 QUICK_START.md 或 MULTI_DAY_GUIDE.md）

# 6. 将返回的 JSON 数据保存为文件，然后用 process_data.py 处理
```

**优点**: 
- ✅ 可绕过验证码
- ✅ 获取真实数据
- ✅ 稳定可靠
- ✅ 支持所有排行类型

**缺点**:
- ⚠️ 需要手动操作
- ⚠️ 无法完全自动化

---

### 🥈 备选方案：处理已有数据

**脚本**: `process_data.py`

**说明**: 如果你已经通过其他方式获取了 JSON 数据，使用此脚本处理和保存。

**使用方法**:

```bash
# 处理 JSON 数据文件
python3 /home/admin/.openclaw/workspace/data_scrept/process_data.py /path/to/data.json 100

# 从标准输入读取
echo '<JSON 数据>' | python3 /home/admin/.openclaw/workspace/data_scrept/process_data.py -
```

**输出**:
- JSON 格式：`/home/admin/.openclaw/workspace/data_files/capital_flow_*.json`
- CSV 格式：`/home/admin/.openclaw/workspace/data_files/capital_flow_*.csv`

---

## 📁 脚本目录结构

```
data_scrept/
├── AVAILABLE_SCRIPTS.md          # 📖【重要】可用脚本说明（本文档）
├── stock_capital_flow_browser.py # ✅ Browser 工具使用说明
├── process_data.py               # ✅ 数据处理脚本
├── fetch_multi_day_capital_flow.py  # ✅ 多日排行获取脚本
├── MULTI_DAY_GUIDE.md            # 📖 多日排行详细指南
├── QUICK_START.md                # 📖 快速开始指南
└── README.md                     # 📖 主文档
```

---

## 📊 输出文件命名规则

| 排行类型 | JSON 文件名前缀 | CSV 文件名前缀 |
|---------|----------------|---------------|
| 今日 | `capital_flow_today_` | `capital_flow_today_` |
| 3 日 | `capital_flow_3d_` | `capital_flow_3d_` |
| 5 日 | `capital_flow_5d_` | `capital_flow_5d_` |
| 10 日 | `capital_flow_10d_` | `capital_flow_10d_` |

完整文件名：`capital_flow_[today|3d|5d|10d]_YYYYMMDD_HHMMSS.json/csv`

---

## ❌ 已删除的不可用脚本

以下脚本因依赖直接 API 访问，在网络受限环境下无法使用，已删除：

| 脚本 | 原因 |
|------|------|
| `stock_capital_flow.py` | 直接 API 请求，被防火墙阻止 |
| `stock_capital_flow_fetch.py` | web_fetch 无法访问东方财富 API |
| `test_fetch.py` | 使用模拟数据（已禁止） |
| `capital_flow_data.json` | 模拟数据文件（已删除） |
| `run_fetch.py` | 受验证码限制，无法自动化 |
| `fetch_full_capital_flow.py` | API 访问失败 |

---

## 🚀 推荐工作流程

### 获取今日排行数据

```bash
# 1. 使用 browser 工具打开页面
browser open https://data.eastmoney.com/zjlx/detail.html

# 2. 在浏览器中手动完成验证码

# 3. 等待并提取数据（见 QUICK_START.md）

# 4. 保存 JSON 数据到文件

# 5. 使用 process_data.py 处理
python3 /home/admin/.openclaw/workspace/data_scrept/process_data.py data.json 100
```

### 获取多日排行数据

详见 `MULTI_DAY_GUIDE.md`

### 输出文件位置

```
/home/admin/.openclaw/workspace/data_files/
├── capital_flow_today_YYYYMMDD_HHMMSS.json  # 今日排行 JSON
├── capital_flow_today_YYYYMMDD_HHMMSS.csv   # 今日排行 CSV
├── capital_flow_3d_YYYYMMDD_HHMMSS.json     # 3 日排行 JSON
├── capital_flow_3d_YYYYMMDD_HHMMSS.csv      # 3 日排行 CSV
├── capital_flow_5d_YYYYMMDD_HHMMSS.json     # 5 日排行 JSON
├── capital_flow_5d_YYYYMMDD_HHMMSS.csv      # 5 日排行 CSV
├── capital_flow_10d_YYYYMMDD_HHMMSS.json    # 10 日排行 JSON
└── capital_flow_10d_YYYYMMDD_HHMMSS.csv     # 10 日排行 CSV
```

---

## 📋 数据字段说明

| 字段 | 说明 |
|------|------|
| 排名 | 主力净流入排名 |
| 代码 | 股票代码 |
| 名称 | 股票名称 |
| 最新价 | 当前股价 |
| 涨跌幅 | 涨跌幅（今日或累计） |
| 主力净流入 | 主力资金净流入金额 |
| 主力净占比 | 主力净流入占成交额比例 |

**多日排行特有字段**:
- 排行类型（今日/3 日/5 日/10 日）
- 超大单净流入
- 大单净流入
- 中单净流入
- 小单净流入

---

## ⚠️ 注意事项

1. **验证码**: 东方财富网会显示滑块验证码，需要手动完成
2. **数据时效**: 仅在交易日有实时数据
3. **请求频率**: 避免频繁访问，建议间隔至少 5 分钟
4. **使用限制**: 仅供个人学习研究使用
5. **多日排行**: 切换排行类型后需要等待数据重新加载

---

## 📖 相关资源

- 东方财富个股资金流：https://data.eastmoney.com/zjlx/detail.html
- 东方财富数据中心：https://data.eastmoney.com/
- **多日排行指南**: `MULTI_DAY_GUIDE.md`
- **快速开始**: `QUICK_START.md`
- **完整文档**: `README.md`

---

## 📝 更新记录

| 日期 | 操作 |
|------|------|
| 2026-03-14 | 删除模拟数据和不可用脚本 |
| 2026-03-14 | 标记可用脚本和推荐方案 |
| 2026-03-14 | 添加多日排行获取支持 |
| 2026-03-14 | 更新本文档 |
