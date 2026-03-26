# 东方财富个股资金流数据脚本

> 📅 创建时间：2026-03-14  
> 📁 数据目录：`/home/admin/.openclaw/workspace/data_files/个股资金流/YYYY-MM-DD/`

---

## 📁 目录结构

```
data_scrept/个股资金流/
├── process_data.py                 # 数据处理脚本（支持按日期分类存储）
├── stock_capital_flow_browser.py   # Browser 工具使用说明
├── fetch_3day_capital_flow.py      # 3 日排行专用脚本
└── fetch_multi_day_capital_flow.py # 多日排行获取指南

data_files/个股资金流/
├── 2026-03-14/                     # 日期子目录
│   ├── capital_flow_today_*.json/csv    # 今日排行
│   ├── capital_flow_3d_*.json/csv       # 3 日排行
│   ├── capital_flow_5d_*.json/csv       # 5 日排行
│   └── capital_flow_10d_*.json/csv      # 10 日排行
├── 2026-03-15/                     # 明日数据...
└── ...
```

---

## 🚀 使用方法

### 1. 处理 JSON 数据

```bash
cd /home/admin/.openclaw/workspace/data_scrept/个股资金流

# 处理今日排行数据
python3 process_data.py /path/to/today_data.json 100

# 处理 3 日排行数据
python3 process_data.py /path/to/3day_data.json 100

# 处理 5 日排行数据
python3 process_data.py /path/to/5day_data.json 100

# 处理 10 日排行数据
python3 process_data.py /path/to/10day_data.json 100
```

### 2. 输出位置

数据会自动保存到按日期分类的目录中：

```bash
# 查看今日数据
ls -lh /home/admin/.openclaw/workspace/data_files/个股资金流/$(date +%Y-%m-%d)/

# 查看所有日期数据
ls -lh /home/admin/.openclaw/workspace/data_files/个股资金流/
```

---

## 📊 支持的排行类型

| 排行类型 | 说明 | 文件前缀 |
|---------|------|---------|
| **今日排行** | 当日主力净流入排名 | `capital_flow_today_*` |
| **3 日排行** | 近 3 日累计排名 | `capital_flow_3d_*` |
| **5 日排行** | 近 5 日累计排名 | `capital_flow_5d_*` |
| **10 日排行** | 近 10 日累计排名 | `capital_flow_10d_*` |

---

## 📋 CSV 表头格式

### 今日排行
```csv
排名，股票代码，股票名称，最新价，涨跌幅，主力净流入，主力净占比，排行类型，...
```

### 3 日排行
```csv
序号，代码，名称，相关，最新价，3 日涨跌幅，3 日主力净流入 - 净额，3 日主力净流入 - 净占比，...
```

### 5 日/10 日排行
```csv
序号，代码，名称，相关，最新价，5 日涨跌幅，5 日主力净流入 - 净额，5 日主力净流入 - 净占比，
5 日超大单净流入 - 净额，5 日超大单净流入 - 净占比，5 日大单净流入 - 净额，5 日大单净流入 - 净占比，
5 日中单净流入 - 净额，5 日中单净流入 - 净占比，5 日小单净流入 - 净额，5 日小单净流入 - 净占比
```

---

## 📁 数据文件示例

```
data_files/个股资金流/2026-03-14/
├── capital_flow_today_20260314_155827.json    (41 KB, 100 条)
├── capital_flow_today_20260314_155827.csv     (9.7 KB, 100 条)
├── capital_flow_3d_20260314_163927.json       (36 KB, 100 条)
├── capital_flow_3d_20260314_163927.csv        (9.8 KB, 100 条)
├── capital_flow_5d_20260314_165945.json       (36 KB, 100 条)
├── capital_flow_5d_20260314_165945.csv        (13 KB, 100 条)
├── capital_flow_10d_20260314_171147.json      (44 KB, 100 条)
└── capital_flow_10d_20260314_171147.csv       (14 KB, 100 条)
```

---

## 🔧 脚本说明

### process_data.py

**功能**: 处理 JSON 数据并按日期分类保存

**参数**:
- `input.json`: 输入的 JSON 数据文件
- `count`: 处理的数据条数（默认 100）

**输出**:
- JSON 文件：包含完整数据
- CSV 文件：可用 Excel 打开

---

## 📖 相关文档

- **主目录文档**: `/home/admin/.openclaw/workspace/data_scrept/README.md`
- **可用脚本说明**: `/home/admin/.openclaw/workspace/data_scrept/AVAILABLE_SCRIPTS.md`
- **快速开始**: `/home/admin/.openclaw/workspace/data_scrept/QUICK_START.md`

---

## ⚠️ 注意事项

1. **数据按日期分类**: 每天的数据自动保存到对应的日期子目录
2. **CSV 编码**: 使用 UTF-8 with BOM 编码，Excel 可直接打开
3. **数据时效**: 仅在交易日更新
4. **建议获取时间**: 市场收盘后（15:30 后）

---

## 📝 更新记录

| 日期 | 操作 |
|------|------|
| 2026-03-14 | 创建个股资金流专用目录 |
| 2026-03-14 | 迁移 4 个排行数据脚本 |
| 2026-03-14 | 添加日期子目录支持 |
| 2026-03-14 | 生成今日/3 日/5 日/10 日排行数据（各 100 条） |
