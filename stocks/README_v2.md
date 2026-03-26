# 🕷️ 本地股票数据爬虫 v2.0

**完整版** - 多数据源、多功能、支持导出

---

## 📦 新功能

### v2.0 新增

- ✅ **多数据源支持** - 腾讯财经、百度股市通、东方财富
- ✅ **板块资金流** - 概念/行业/地区板块
- ✅ **北向资金监控** - 沪股通 + 深股通
- ✅ **数据导出** - CSV / JSON 格式
- ✅ **缓存优化** - 自动过期管理
- ✅ **综合评分** - 主力 + 涨幅 + 成交量加权

---

## 🚀 快速开始

### 1. 抓取数据

```bash
cd /home/admin/.openclaw/workspace/stocks

# 抓取全部数据源
python3 local_crawler.py --crawl

# 只抓取腾讯财经
python3 local_crawler.py --crawl --source tencent

# 只抓取东方财富（板块 + 北向）
python3 local_crawler.py --crawl --source eastmoney
```

### 2. 查询排行

```bash
# 综合 Top10
python3 local_crawler.py --query top10

# 综合 Top50
python3 local_crawler.py --query top50

# 主力活跃 Top20
python3 local_crawler.py --query main --top 20

# 成交量 Top20
python3 local_crawler.py --query volume --top 20

# 涨跌幅 Top20
python3 local_crawler.py --query change --top 20

# 概念板块资金流
python3 local_crawler.py --query sector --sector-type concept

# 行业板块资金流
python3 local_crawler.py --query sector --sector-type industry

# 北向资金
python3 local_crawler.py --query north
```

### 3. 导出数据

```bash
# 导出 CSV
python3 local_crawler.py --query main --top 50 --export csv

# 导出 JSON
python3 local_crawler.py --query top10 --export json

# 导出文件位置：cache/stock_*.csv 或 cache/stock_*.json
```

### 4. 缓存管理

```bash
# 刷新缓存（删除所有缓存）
python3 local_crawler.py --refresh

# 不使用缓存（强制重新抓取）
python3 local_crawler.py --query top10 --no-cache
```

---

## 📊 数据源对比

| 数据源 | 数据类型 | 主力数据 | 速度 | 稳定性 |
|--------|---------|---------|------|--------|
| **腾讯财经** | 实时行情 | ⚠️ 估算 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 百度股市通 | 排行榜 | ❌ 无 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 东方财富 | 板块/北向 | ✅ 真实 | ⭐⭐⭐ | ⚠️ 网络受限 |

---

## 📁 文件结构

```
stocks/
├── local_crawler.py      # 主爬虫脚本 v2.0
├── auto_push.py          # 自动推送脚本
├── capital_flow.py       # 主力资金排行
├── top_volume.py         # 成交量排行
├── sina_stock.py         # 个股行情查询
├── wechat_push.py        # 微信推送模块
├── push_daily.py         # 每日推送配置
├── README_v2.md          # 本文档
├── LOCAL_CRAWLER.md      # v1.0 文档
└── cache/                # 缓存目录
    ├── stocks_cache.json       # 股票行情缓存
    ├── baidu_rank.json         # 百度排行缓存
    ├── sector_concept.json     # 概念板块缓存
    ├── north_bound.json        # 北向资金缓存
    └── stock_*.csv/json        # 导出文件
```

---

## 📈 排行榜说明

### 综合评分算法

```
综合评分 = 主力得分 × 50% + 涨幅得分 × 30% + 成交量得分 × 20%

主力得分 = min(100, 主力估算 / 1亿 × 100)
涨幅得分 = min(100, max(0, 涨跌幅 + 50))
成交量得分 = min(100, 成交量 / 1000 万 × 10)
```

### 字段说明

| 字段 | 说明 | 单位 |
|------|------|------|
| symbol | 股票代码 | - |
| name | 股票名称 | - |
| price | 当前价格 | 元 |
| change_pct | 涨跌幅 | % |
| volume | 成交量 | 手 |
| amount_wan | 成交额 | 万元 |
| main_force_est | 主力估算 | 元 |
| score | 综合评分 | 0-100 |

---

## 🔄 定时任务

### 完整方案

```bash
crontab -e

# 9:00 开盘前抓取
0 9 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 local_crawler.py --crawl --source tencent

# 9:30 开盘推送
30 9 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 auto_push.py --type change --top 10

# 11:30 午间推送
30 11 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 auto_push.py --top 10

# 15:00 收盘抓取
0 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 local_crawler.py --crawl --refresh

# 15:30 收盘推送（主力排行）
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 auto_push.py --type main --top 10

# 16:00 导出日报
0 16 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 local_crawler.py --query top50 --export csv
```

---

## 🛠️ Python API 使用

```python
from local_crawler import StockCrawler

# 初始化
crawler = StockCrawler()

# 抓取数据
stocks = crawler.crawl_tencent()

# 获取排行榜
top10 = crawler.get_ranking(rank_by='score', top_n=10)
top_main = crawler.get_ranking(rank_by='main_force', top_n=20)

# 获取板块
sectors = crawler.get_sector_ranking(sector_type='concept', top_n=10)

# 获取北向资金
north = crawler.crawl_north_bound()

# 导出
crawler.export_csv(top10, 'top10.csv')
crawler.export_json(top10, 'top10.json')

# 打印
crawler.print_ranking(top10, "我的自选股")
crawler.print_sector_ranking(sectors, "热门概念")
crawler.print_north_bound(north)
```

---

## ⚠️ 注意事项

1. **请求频率** - 已内置延迟，不要手动加快
2. **数据准确性** - 主力数据为估算值，仅供参考
3. **网络依赖** - 需要访问外部服务器
4. **缓存时间** - 默认 10-30 分钟过期
5. **内存占用** - 全量抓取约 500-1000 只股票

---

## 🐛 故障排除

### 抓取失败

```bash
# 检查网络
curl https://qt.gtimg.cn/q=sh600000

# 检查 Python 版本
python3 --version  # 需要 3.6+

# 检查依赖
pip3 install requests
```

### 缓存问题

```bash
# 查看缓存
ls -la cache/

# 删除缓存
python3 local_crawler.py --refresh

# 查看缓存内容
cat cache/stocks_cache.json | head -50
```

### 导出问题

```bash
# CSV 乱码 - 使用 Excel 打开时选择 UTF-8 编码
# JSON 格式 - 使用 jq 工具查看
cat cache/stock_*.json | jq '.[0]'
```

---

## 📊 示例输出

### 综合排行

```
==============================================================================================================
📊 股票 top10 榜 Top10
==============================================================================================================
排名   代码         名称         现价       涨跌幅        成交量          成交额        评分    
--------------------------------------------------------------------------------------------------------------
1    sh600108   亚盛集团       ¥ 5.76 + 118.17%  3,163,669  149.34亿  80.6
2    sh601218   吉鑫科技       ¥ 7.16 +  64.13%  2,283,347  117.24亿  80.5
3    sz000875   电投绿能       ¥ 7.21 +  55.84%  1,251,900   52.88亿  80.3
...
```

### 板块资金流

```
====================================================================================================
📊 concept 板块资金流 Top10
====================================================================================================
排名   代码     名称              主力净流入        涨跌幅        超大单      
----------------------------------------------------------------------------------------------------
1    BK0982  人工智能          125.67 亿      + 5.23%    89.45 万
2    BK0912  新能源车           98.45 亿      + 3.12%    67.23 万
...
```

---

## 📄 更新日志

### v2.0 (2026-03-17)

- ✅ 添加多数据源支持
- ✅ 添加板块资金流
- ✅ 添加北向资金监控
- ✅ 添加 CSV/JSON 导出
- ✅ 优化缓存管理
- ✅ 改进综合评分算法

### v1.0 (2026-03-17)

- ✅ 初始版本
- ✅ 腾讯财经数据源
- ✅ 本地缓存
- ✅ 微信推送

---

## 📄 许可证

本脚本仅供学习研究使用，请勿用于商业目的。

数据版权归各自数据源所有。
