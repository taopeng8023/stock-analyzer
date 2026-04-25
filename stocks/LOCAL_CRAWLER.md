# 🕷️ 本地股票数据爬虫

本地部署的股票数据爬虫，不依赖外部 API Key，直接从公开数据源抓取数据。

---

## 📦 功能特性

- ✅ **无需 API Key** - 直接抓取公开数据
- ✅ **多数据源** - 腾讯财经、百度股市通
- ✅ **本地缓存** - 减少重复请求，提高速度
- ✅ **多种排行** - 综合、主力、成交量、涨跌幅
- ✅ **可扩展** - 轻松添加新数据源

---

## 🚀 快速开始

### 1. 抓取数据

```bash
cd /home/admin/.openclaw/workspace/stocks

# 抓取最新数据
python3 local_crawler.py --crawl
```

### 2. 查询排行

```bash
# 综合排行 Top10
python3 local_crawler.py --query top10

# 综合排行 Top50
python3 local_crawler.py --query top50

# 主力净流入排行
python3 local_crawler.py --query main --top 20

# 成交量排行
python3 local_crawler.py --query volume --top 20

# 涨跌幅排行
python3 local_crawler.py --query change --top 20
```

### 3. 刷新缓存

```bash
# 删除缓存，强制重新抓取
python3 local_crawler.py --refresh
```

---

## 📊 数据源说明

### 腾讯财经（主要数据源）

| 数据项 | 字段 | 说明 |
|--------|------|------|
| 股票代码 | f12 | sh/sz + 6 位数字 |
| 股票名称 | f14 | 中文名称 |
| 当前价格 | f3 | 元 |
| 涨跌幅 | f39 | % |
| 成交量 | f6 | 手 |
| 成交额 | f7 | 万元 |
| 主力估算 | - | 成交额 × 10-15% |

**优点：**
- 免费公开，无需认证
- 数据实时更新
- 覆盖沪深 A 股

**缺点：**
- 主力数据为估算值
- 无历史 K 线数据

---

### 百度股市通（辅助数据源）

| 数据项 | 说明 |
|--------|------|
| 涨跌幅排行 | 实时涨跌榜 |
| 成交额排行 | 成交活跃榜 |
| 成交量排行 | 量能榜 |

**优点：**
- 官方数据
- 多种排行

**缺点：**
- 数据结构复杂
- 需要解析 HTML/JSON

---

## 📁 文件结构

```
stocks/
├── local_crawler.py    # 主爬虫脚本
├── cache/              # 缓存目录
│   └── stocks_cache.json
├── LOCAL_CRAWLER.md    # 本文档
├── sina_stock.py       # 新浪/腾讯行情查询
├── wechat_push.py      # 微信推送
├── capital_flow.py     # 主力资金排行
└── top_volume.py       # 成交量排行
```

---

## ⏰ 定时任务

### 方案 1：cron 定时

```bash
crontab -e

# 每个交易日 9:25（开盘前）抓取数据
25 9 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 local_crawler.py --crawl

# 每个交易日 15:30（收盘后）推送排行
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 capital_flow.py --top 10 --push
```

### 方案 2：systemd 定时

创建服务文件 `/etc/systemd/system/stock-crawler.service`:

```ini
[Unit]
Description=Stock Data Crawler
After=network.target

[Service]
Type=oneshot
User=admin
WorkingDirectory=/home/admin/.openclaw/workspace/stocks
ExecStart=/usr/bin/python3 /home/admin/.openclaw/workspace/stocks/local_crawler.py --crawl
```

创建定时器 `/etc/systemd/system/stock-crawler.timer`:

```ini
[Unit]
Description=Run Stock Crawler every 30 minutes during trading hours

[Timer]
OnCalendar=*-*-* 9-15/1:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

启用：
```bash
sudo systemctl enable stock-crawler.timer
sudo systemctl start stock-crawler.timer
```

---

## 🔧 高级配置

### 自定义抓取范围

编辑 `local_crawler.py`，修改 `crawl_tencent` 方法：

```python
# 只抓取特定板块
symbols = []

# 只抓取沪市
for i in range(100, 600):
    symbols.append(f"sh600{i%1000:03d}")

# 只抓取创业板
for i in range(0, 200):
    symbols.append(f"sz300{i:03d}")
```

### 添加新数据源

实现新的 crawl 方法：

```python
def crawl_new_source(self):
    """从新数据源抓取"""
    url = "https://api.example.com/stocks"
    resp = requests.get(url)
    data = resp.json()
    
    stocks = []
    for item in data:
        stocks.append({
            'symbol': item['code'],
            'name': item['name'],
            'price': item['price'],
            # ...
        })
    
    return stocks
```

### 导出数据

```python
# 导出为 CSV
import csv

data = crawler.get_ranking(top_n=100)

with open('stocks_top100.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=['symbol', 'name', 'price', 'change_pct', 'volume', 'amount_wan'])
    writer.writeheader()
    writer.writerows(data)
```

---

## ⚠️ 注意事项

1. **请求频率** - 每批请求间隔 0.2 秒，避免被封 IP
2. **数据准确性** - 主力数据为估算值，仅供参考
3. **网络依赖** - 需要访问腾讯/百度服务器
4. **缓存时间** - 默认 10 分钟过期，可调整

---

## 🐛 故障排除

### 问题：抓取失败

```bash
# 检查网络连接
curl https://qt.gtimg.cn/q=sh600000

# 检查 Python 版本
python3 --version  # 需要 3.6+

# 检查依赖
pip3 install requests
```

### 问题：缓存异常

```bash
# 删除缓存
python3 local_crawler.py --refresh

# 检查缓存目录
ls -la cache/
```

### 问题：数据不准确

- 检查数据源是否可用
- 确认缓存是否过期
- 手动刷新重新抓取

---

## 📈 后续优化

- [ ] 添加东方财富网页爬取（Selenium）
- [ ] 支持历史 K 线数据
- [ ] 添加技术指标计算
- [ ] 支持 WebSocket 实时推送
- [ ] 添加数据可视化

---

## 📄 许可证

本脚本仅供学习研究使用，请勿用于商业目的。
