# AKShare 东财个股接口使用指南

**Python**: 3.11.13  
**AKShare**: 1.18.47  
**更新日期**: 2026-03-27

---

## 📦 安装

```bash
# 使用 Python 3.11
pip3.11 install akshare --upgrade
```

---

## 🔧 东财个股接口

### 1. 个股历史行情

```python
import akshare as ak

# 获取个股历史行情
stock_data = ak.stock_zh_a_hist(
    symbol='600152',        # 股票代码
    period='daily',         # 周期：daily/weekly/monthly
    start_date='20260301',  # 开始日期 YYYYMMDD
    end_date='20260327',    # 结束日期 YYYYMMDD
    adjust='qfq'            # 复权：qfq(前复权)/hfq(后复权)/none(不复权)
)

print(stock_data)
```

**返回字段**:
| 字段 | 说明 |
|------|------|
| 日期 | 交易日期 |
| 股票代码 | 6 位代码 |
| 开盘 | 开盘价 |
| 收盘 | 收盘价 |
| 最高 | 最高价 |
| 最低 | 最低价 |
| 成交量 | 成交量 (手) |
| 成交额 | 成交额 (元) |
| 振幅 | 振幅 (%) |
| 涨跌幅 | 涨跌幅 (%) |
| 涨跌额 | 涨跌额 (元) |
| 换手率 | 换手率 (%) |

---

### 2. 实时行情

```python
# 获取 A 股实时行情
spot_data = ak.stock_zh_a_spot_em()

# 获取 ETF 实时行情
etf_data = ak.fund_etf_spot_em()
```

---

### 3. 资金流

```python
# 个股资金流
fund_flow = ak.stock_individual_fund_flow(
    symbol='600152',  # 股票代码
    market='sh'       # 市场：sh/sz
)

# 板块资金流
sector_flow = ak.stock_board_industry_name_em()
```

---

## ⚠️ 反爬限制处理

东方财富接口有反爬限制，建议：

### 1. 添加重试机制

```python
import time
from akshare import stock_zh_a_hist

def get_stock_with_retry(symbol, start_date, end_date, max_retries=3):
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = 3 * attempt
                print(f'重试 {attempt}/{max_retries} (等待{delay}秒)...')
                time.sleep(delay)
            
            data = stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust='qfq'
            )
            return data
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            continue
    
    return None
```

### 2. 添加请求间隔

```python
symbols = ['600152', '600089', '002475']

for symbol in symbols:
    data = get_stock_with_retry(symbol, '20260101', '20260327')
    time.sleep(2)  # 每只股票间隔 2 秒
```

### 3. 使用备用接口

如果东财接口失败，可以使用：

```python
# 新浪财经（如果可用）
import sina_stock

# 腾讯财经（如果可用）
import tencent_stock

# 本地缓存数据
import json
with open('cache/stock_data.json') as f:
    data = json.load(f)
```

---

## 📊 当前接口状态

| 接口 | 状态 | 说明 |
|------|------|------|
| `stock_zh_a_hist()` | ⚠️ 限流 | 需要重试机制 |
| `stock_zh_a_spot_em()` | ⚠️ 限流 | 实时行情 |
| `fund_etf_spot_em()` | ⚠️ 限流 | ETF 行情 |
| `stock_individual_fund_flow()` | ⚠️ 限流 | 个股资金流 |
| `stock_board_industry_name_em()` | ⚠️ 限流 | 行业板块 |
| `macro_cnbs()` | ✅ 正常 | 宏观数据 |

---

## 🔄 替代方案

### 方案 1: 使用本地缓存

```python
# 从本地缓存读取
import json

with open('backtest_data/600152_kline.json') as f:
    data = json.load(f)
```

### 方案 2: 使用腾讯财经接口

```python
# 已在 local_crawler.py 中实现
from local_crawler import StockCrawler

crawler = StockCrawler()
data = crawler.crawl_tencent(symbols=['sh600152'])
```

### 方案 3: 使用新浪财经接口

```python
# 已在系统中实现
url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sz000815'
```

---

## 💡 最佳实践

1. **添加重试机制** - 至少重试 3 次
2. **添加延迟** - 每次请求间隔 2-3 秒
3. **使用缓存** - 避免重复请求
4. **批量获取** - 一次获取多只股票数据
5. **错误处理** - 捕获异常并记录

---

## 📝 示例代码

完整示例见 `akshare_demo.py`

```bash
python3.11 akshare_demo.py
```

---

## 🔗 相关文档

- [AKShare 官方文档](https://akshare.akfamily.xyz/)
- [东方财富网](https://www.eastmoney.com/)
- [本地爬虫文档](LOCAL_CRAWLER.md)

---

**最后更新**: 2026-03-27  
**状态**: ⚠️ 东财接口限流中，建议使用缓存或重试机制
