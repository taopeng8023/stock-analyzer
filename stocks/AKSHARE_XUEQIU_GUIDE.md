# AKShare 雪球接口配置指南

**Python**: 3.11.13  
**AKShare**: 1.18.47  
**更新日期**: 2026-03-27

---

## 📦 雪球接口说明

雪球接口需要 **Token/Cookie** 认证，因为雪球网站有反爬保护。

### 可用接口

| 接口 | 功能 | 需要 Token |
|------|------|-----------|
| `stock_individual_spot_xq()` | 个股实时行情 | ✅ 需要 |
| `stock_individual_basic_info_xq()` | 个股基本信息 | ✅ 需要 |
| `stock_individual_basic_info_hk_xq()` | 港股基本信息 | ✅ 需要 |
| `stock_individual_basic_info_us_xq()` | 美股基本信息 | ✅ 需要 |

---

## 🔑 获取雪球 Token

### 方法 1: 浏览器获取

1. 打开浏览器访问：https://xueqiu.com/
2. 登录雪球账号
3. 按 F12 打开开发者工具
4. 点击"Network"(网络)标签
5. 刷新页面
6. 找到任意请求，查看 Request Headers
7. 复制 `cookie` 或 `x-token` 值

### 方法 2: 使用代码获取

```python
import requests

# 访问雪球首页获取 cookie
session = requests.Session()
resp = session.get('https://xueqiu.com/')

# 获取 cookie
cookie = session.cookies.get_dict()
print(cookie)
```

---

## 🔧 配置 Token

### 方式 1: 直接传入参数

```python
import akshare as ak

token = 'your_xueqiu_token_here'  # 替换为你的 token

# 获取个股实时行情
data = ak.stock_individual_spot_xq(
    symbol='SH600152',  # 维科技术
    token=token
)

print(data)
```

### 方式 2: 设置环境变量

```bash
# Linux/Mac
export AKSHARE_XUEQIU_TOKEN='your_token_here'

# Windows
set AKSHARE_XUEQIU_TOKEN=your_token_here
```

```python
import akshare as ak
import os

# 从环境变量读取
token = os.getenv('AKSHARE_XUEQIU_TOKEN')

data = ak.stock_individual_spot_xq(
    symbol='SH600152',
    token=token
)
```

### 方式 3: 配置文件

创建 `~/.akshare/xueqiu_token.txt` 文件：

```bash
mkdir -p ~/.akshare
echo 'your_token_here' > ~/.akshare/xueqiu_token.txt
```

```python
import akshare as ak

# AKShare 会自动读取配置文件
data = ak.stock_individual_spot_xq(symbol='SH600152')
```

---

## 📝 使用示例

### 1. 获取个股实时行情

```python
import akshare as ak

token = 'your_token'  # 替换为实际 token

# A 股
data = ak.stock_individual_spot_xq(
    symbol='SH600152',  # 维科技术
    token=token
)

print(data)
```

**返回字段**:
| 字段 | 说明 |
|------|------|
| current | 当前价格 |
| change | 涨跌额 |
| percent | 涨跌幅 |
| volume | 成交量 |
| amount | 成交额 |
| market_cap | 总市值 |
| pe_ttm | 市盈率 (TTM) |
| pb | 市净率 |

### 2. 获取个股基本信息

```python
# 个股基本信息
info = ak.stock_individual_basic_info_xq(
    symbol='SH600152',
    token=token
)

print(info)
```

**返回字段**:
- 股票代码
- 股票名称
- 所属行业
- 总股本
- 流通股本
- 上市日期
- 等

### 3. 批量获取

```python
symbols = ['SH600152', 'SH600089', 'SZ002475', 'SZ000815']

for symbol in symbols:
    try:
        data = ak.stock_individual_spot_xq(
            symbol=symbol,
            token=token
        )
        print(f"{symbol}: ¥{data['current'].iloc[0]} {data['percent'].iloc[0]:+.2f}%")
    except Exception as e:
        print(f"{symbol}: 获取失败 - {e}")
    
    time.sleep(1)  # 避免限流
```

---

## ⚠️ 注意事项

1. **Token 有效期** - 雪球 token 会过期，需要定期更新
2. **请求频率** - 建议每次请求间隔 1-2 秒
3. **账号风险** - 频繁请求可能导致账号被限制
4. **数据准确性** - 雪球数据可能有 15 分钟延迟

---

## 🔄 替代方案

如果雪球接口配置复杂，可以使用：

### 方案 1: 东方财富接口

```python
import akshare as ak

# 东财个股历史行情（无需 token）
data = ak.stock_zh_a_hist(
    symbol='600152',
    period='daily',
    adjust='qfq'
)
```

### 方案 2: 新浪财经接口

```python
# 已在 local_crawler.py 中实现
from local_crawler import StockCrawler

crawler = StockCrawler()
data = crawler.crawl_tencent(symbols=['sh600152'])
```

### 方案 3: 本地缓存

```python
import json

with open('backtest_data/600152_kline.json') as f:
    data = json.load(f)
```

---

## 📊 接口对比

| 数据源 | 优点 | 缺点 | 推荐度 |
|--------|------|------|--------|
| **雪球** | 数据丰富，有社区评论 | 需要 token，配置复杂 | ⭐⭐⭐ |
| **东方财富** | 数据全面，无需认证 | 有反爬限流 | ⭐⭐⭐⭐ |
| **新浪财经** | 稳定，速度快 | 数据字段较少 | ⭐⭐⭐⭐ |
| **腾讯财经** | 稳定，数据全 | 需要解析 | ⭐⭐⭐⭐ |

---

## 🔗 相关文档

- [AKShare 官方文档](https://akshare.akfamily.xyz/)
- [雪球网](https://xueqiu.com/)
- [东方财富接口](AKSHARE_GUIDE.md)

---

**最后更新**: 2026-03-27  
**状态**: ⚠️ 需要配置 Token 才能使用
