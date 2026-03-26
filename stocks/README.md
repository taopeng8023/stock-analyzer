# 📊 股票数据工具集

**⚠️ 重要声明：本工具所有数据均来自真实市场数据源，严禁使用任何模拟数据。**

详见：[DATA_POLICY.md](DATA_POLICY.md)

---

## 📁 文件结构

```
stocks/
├── local_crawler.py      # 主爬虫脚本（实时行情、排行榜、板块、K 线）
├── kline.py              # K 线数据获取模块（独立）
├── auto_push.py          # 自动推送脚本
├── capital_flow.py       # 主力资金排行
├── top_volume.py         # 成交量排行
├── sina_stock.py         # 个股行情查询
├── wechat_push.py        # 微信推送模块
├── push_daily.py         # 每日推送配置
├── DATA_POLICY.md        # ⚠️ 数据使用政策（必读）
├── README.md             # 本文档
├── README_v2.md          # v2.0 功能文档
└── cache/                # 缓存目录
    ├── stocks_cache.json       # 股票行情
    ├── kline_*.json            # K 线数据
    ├── sector_*.json           # 板块数据
    ├── north_bound.json        # 北向资金
    └── *.csv                   # 导出文件
```

---

## 🚀 快速开始

### 1. 获取股票排行

```bash
cd /home/admin/.openclaw/workspace/stocks

# 综合 Top10
python3 local_crawler.py --query top10

# 主力活跃 Top20
python3 local_crawler.py --query main --top 20

# 成交量 Top20
python3 local_crawler.py --query volume --top 20
```

### 2. 获取 K 线数据

```bash
# 日线 60 条
python3 kline.py sh600000 --count 60

# 周线
python3 kline.py sh600519 --period week

# 导出 CSV
python3 kline.py sz000001 --export
```

### 3. 微信推送

```bash
# 推送综合 Top10
python3 auto_push.py

# 推送主力 Top20
python3 auto_push.py --type main --top 20
```

---

## 📊 功能列表

| 功能 | 命令 | 说明 |
|------|------|------|
| **实时行情** | `--query top10` | 获取股票实时数据排行 |
| **主力排行** | `fund_flow.py --top 10` | 主力净流入排行（腾讯估算） |
| **主力排行 (真实)** | `akshare_flow.py --top 10` | 同花顺真实数据 ⭐ |
| **成交量排行** | `--query volume` | 按成交量排序 |
| **涨跌幅排行** | `--query change` | 按涨跌幅排序 |
| **K 线数据** | `kline.py <代码>` | 获取日线/周线/月线 |
| **技术指标** | 自动计算 | MA/MACD/KDJ |
| **板块资金流** | `--query sector` | 概念/行业板块 |
| **北向资金** | `--query north` | 沪股通 + 深股通 |
| **数据导出** | `--export csv` | 导出 CSV/JSON |
| **微信推送** | `auto_push.py` | 企业微信推送 |
| **Tushare 集成** | `tushare_flow.py` | 真实主力数据（需 Token） |
| **AKShare 集成** | `akshare_flow.py` | 同花顺真实数据 ⭐ |

---

## 📈 数据源

| 数据源 | 数据类型 | 状态 |
|--------|---------|------|
| **腾讯财经** | 实时行情、成交量 | ✅ 稳定 |
| **东方财富** | K 线、板块、北向资金 | ⚠️ 网络受限 |
| **百度股市通** | 排行榜 | ✅ 可用 |

---

## ⚠️ 数据政策

### 核心原则

**所有股票交易数据必须来自真实市场，严禁使用模拟数据。**

此要求适用于：
- ✅ 所有使用场景
- ✅ 所有时间
- ✅ 所有功能
- ✅ 测试和调试

### 失败处理

当数据源不可用时：
1. 返回空数据
2. 明确提示用户
3. 建议稍后重试
4. **绝不生成模拟数据**

详见：[DATA_POLICY.md](DATA_POLICY.md)

---

## 📁 缓存管理

```bash
# 刷新缓存（删除所有）
python3 local_crawler.py --refresh

# 不使用缓存
python3 local_crawler.py --query top10 --no-cache

# K 线缓存位置
cache/kline_sh600000_day.json

# 行情缓存位置
cache/stocks_cache.json
```

**缓存有效期：**
- 实时行情：10 分钟
- K 线数据：60 分钟
- 板块数据：30 分钟
- 北向资金：30 分钟

---

## 🔧 定时任务

```bash
crontab -e

# 9:00 开盘前抓取
0 9 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 local_crawler.py --crawl

# 11:30 午间推送
30 11 * * 1-5 python3 /home/admin/.openclaw/workspace/stocks/auto_push.py

# 15:30 收盘推送
30 15 * * 1-5 python3 /home/admin/.openclaw/workspace/stocks/auto_push.py --type main
```

---

## 📤 导出格式

### CSV 字段（行情）
```
symbol, name, price, change_pct, volume, amount_wan, main_force_est, score
```

### CSV 字段（K 线）
```
date, open, high, low, close, volume, amount,
ma5, ma10, ma20, ma60, dif, dea, macd, k, d, j
```

---

## 🐛 故障排除

### K 线获取失败

```
⚠️  所有数据源获取失败，返回空数据（不使用模拟数据）
```

**原因：** 东方财富/腾讯 API 网络不稳定

**解决：**
1. 稍后重试
2. 检查网络连接
3. 使用缓存数据（如果未过期）

### 推送失败

检查 Webhook 地址是否正确：
```bash
python3 auto_push.py --webhook "https://qyapi.weixin.qq.com/..."
```

---

## 📄 相关文档

- [DATA_POLICY.md](DATA_POLICY.md) - ⚠️ 数据使用政策（必读）
- [README_v2.md](README_v2.md) - v2.0 功能详解
- [LOCAL_CRAWLER.md](LOCAL_CRAWLER.md) - v1.0 文档

---

## ⚖️ 免责声明

1. 本工具所有数据来自公开数据源，仅供参考
2. 不构成任何投资建议
3. 交易决策请基于官方交易所数据
4. 数据可能有延迟，请以实时行情为准
5. **本工具不使用模拟数据，所有数据均为真实市场数据**

---

**最后更新：2026-03-17**

**版本：v2.1**
