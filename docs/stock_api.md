# 股票实时行情 API 集成指南

## 📋 概述

提供新浪财经、东方财富的实时行情接口封装，支持：
- ✅ 实时股价查询
- ✅ K 线数据获取
- ✅ 资金流数据
- ✅ 技术指标计算
- ✅ 批量查询

---

## 🔧 API 接口说明

### 1. 实时行情（新浪财经）

**接口：** `http://hq.sinajs.cn/list={market}{code}`

**参数：**
- `market`: `sh`（沪市）或 `sz`（深市）
- `code`: 6 位股票代码

**返回字段：**
```python
{
    'code': '002475',
    'name': '立讯精密',
    'price': 50.97,       # 当前价
    'open': 47.38,        # 开盘价
    'high': 50.97,        # 最高价
    'low': 47.00,         # 最低价
    'close': 46.34,       # 昨收
    'volume': 2567600,    # 成交量（手）
    'amount': 12834000000,# 成交额（元）
    'change': 4.63,       # 涨跌额
    'change_percent': 9.99,# 涨跌幅%
    'bid': 50.96,         # 买一价
    'ask': 50.97,         # 卖一价
    'date': '2026-03-25',
    'time': '14:20:18'
}
```

**使用示例：**
```python
from scripts.stock_api import StockAPI

api = StockAPI()

# 获取单只股票行情
quote = api.get_quote_sina('002475')
print(f"{quote['name']} 现价：{quote['price']} 涨幅：{quote['change_percent']}%")

# 批量获取行情
quotes = api.get_batch_quotes(['002475', '300308', '601138'])
for q in quotes:
    print(f"{q['code']} {q['price']} ({q['change_percent']}%)")
```

---

### 2. K 线数据（新浪财经）

**接口：** `http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData`

**参数：**
- `symbol`: `sh600152` 或 `sz002475`
- `scale`: `day`/`week`/`month`/`minute`
- `datalen`: 数据条数（最多 1024）

**返回格式：**
```python
[
    {
        'day': '2026-03-25',
        'open': 47.38,
        'high': 50.97,
        'low': 47.00,
        'close': 50.97,
        'volume': 2567600
    },
    ...
]
```

**使用示例：**
```python
# 获取 60 日 K 线
kline = api.get_kline_sina('002475', period='day', days=60)

# 计算技术指标
from scripts.stock_api import calculate_indicators
indicators = calculate_indicators(kline)

print(f"MACD: DIF={indicators['macd']['dif']:.4f} 趋势={indicators['macd']['trend']}")
print(f"KDJ: K={indicators['kdj']['k']:.2f} 位置={indicators['kdj']['position']}")
```

---

### 3. 资金流数据（东方财富）

**接口：** `https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get`

**参数：**
- `secid`: `0.002475`（深市）或 `1.600152`（沪市）
- `fields1`: `f1,f2,f3,f7`
- `fields2`: `f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65`

**返回字段：**
```python
{
    'code': '002475',
    'name': '立讯精密',
    'date': '2026-03-25',
    'main_net_inflow': 296900,      # 主力净流入（万元）
    'main_ratio': 22.76,            # 主力占比%
    'super_large_ratio': 27.70,     # 超大单占比%
    'large_ratio': -4.94,           # 大单占比%
    'medium_ratio': -13.38,         # 中单占比%
    'small_ratio': -9.39            # 小单占比%
}
```

**使用示例：**
```python
# 获取资金流
fund_flow = api.get_fund_flow('002475')

print(f"主力净流入：{fund_flow['main_net_inflow']:,.0f}万")
print(f"主力占比：{fund_flow['main_ratio']:.2f}%")
print(f"超大单占比：{fund_flow['super_large_ratio']:.2f}%")
```

---

## 📊 技术指标计算

### 内置指标

`calculate_indicators(kline_data)` 自动计算：

| 指标 | 说明 | 返回字段 |
|------|------|----------|
| **MACD** | 平滑异同移动平均线 | `dif`, `dea`, `bar`, `trend` |
| **KDJ** | 随机指标 | `k`, `d`, `j`, `position` |
| **RSI** | 相对强弱指标 | `rsi6`, `rsi12`, `rsi24` |
| **均线** | 移动平均线 | `ma5`, `ma10`, `ma20`, `ma60` |
| **成交量** | 量比/换手 | `volume_ratio`, `turnover_rate` |

**使用示例：**
```python
kline = api.get_kline_sina('002475', days=60)
indicators = calculate_indicators(kline)

# MACD
print(f"DIF: {indicators['macd']['dif']:.4f}")
print(f"DEA: {indicators['macd']['dea']:.4f}")
print(f"趋势：{indicators['macd']['trend']}")

# KDJ
print(f"K: {indicators['kdj']['k']:.2f}")
print(f"D: {indicators['kdj']['d']:.2f}")
print(f"位置：{indicators['kdj']['position']}")

# RSI
print(f"RSI6: {indicators['rsi']['rsi6']:.2f}")
print(f"RSI12: {indicators['rsi']['rsi12']:.2f}")
```

---

## 🔗 集成到推荐系统

### 完整流程示例

```python
from scripts.stock_api import StockAPI, calculate_indicators
from scripts.stock_visualizer_html import create_html_chart
from scripts.stock_recommender_v3 import calculate_comprehensive_score_v3

# 初始化 API
api = StockAPI()

# 1. 获取实时行情
quote = api.get_quote_sina('002475')

# 2. 获取 K 线数据
kline = api.get_kline_sina('002475', days=60)

# 3. 计算技术指标
indicators = calculate_indicators(kline)

# 4. 获取资金流
fund_flow = api.get_fund_flow('002475')

# 5. 构建股票数据
stock_data = {
    'code': '002475',
    'name': '立讯精密',
    'price': quote['price'],
    'price_change': quote['change_percent'],
    'volume_ratio': indicators['volume']['volume_ratio'],
    'turnover_rate': indicators['volume']['turnover_rate'],
    
    # 技术指标
    'macd_dif': indicators['macd']['dif'],
    'macd_dea': indicators['macd']['dea'],
    'macd_hist': indicators['macd']['bar'],
    'macd_trend': indicators['macd']['trend'],
    'kdj_k': indicators['kdj']['k'],
    'kdj_d': indicators['kdj']['d'],
    'kdj_j': indicators['kdj']['j'],
    'kdj_position': indicators['kdj']['position'],
    'rsi6': indicators['rsi']['rsi6'],
    'rsi12': indicators['rsi']['rsi12'],
    'rsi24': indicators['rsi']['rsi24'],
    'ma5': indicators['ma']['ma5'],
    'ma10': indicators['ma']['ma10'],
    'ma20': indicators['ma']['ma20'],
    'ma60': indicators['ma']['ma60'],
    'ma_trend': '多头' if indicators['ma']['ma5'] > indicators['ma']['ma10'] else '空头',
    
    # 资金流
    'main_net_inflow': fund_flow['main_net_inflow'],
    'main_ratio': fund_flow['main_ratio'],
    'super_ratio': fund_flow['super_large_ratio'],
    
    # 其他
    'sector': '苹果链/AI',
    'pe_ttm': 23.49,
    'profit_growth': 25,
    'debt_ratio': 45,
    'position_52w': 71,
    'is_loss': False,
    'is_hot_concept': True,
}

# 6. 计算综合评分
result = calculate_comprehensive_score_v3(stock_data)

# 7. 生成可视化图表
create_html_chart(
    code='002475',
    name='立讯精密',
    stock_info=result,
    save_path='/path/to/chart.html'
)

print(f"综合评分：{result['total_score']:.1f}")
print(f"盈利概率：{result['win_probability']}%")
```

---

## ⚠️ 注意事项

### 1. 网络访问限制

当前环境可能无法直接访问外部 API，解决方案：

**方案 A：使用浏览器自动化**
```python
from scripts.stock_funds_browser import fetch_funds_browser
# 通过浏览器获取东方财富数据
```

**方案 B：本地部署数据源**
- 使用 Tushare Pro（需注册）
- 使用 AkShare（开源）
- 本地数据库缓存

### 2. 请求频率限制

- 新浪财经：单 IP 约 60 次/分钟
- 东方财富：单 IP 约 30 次/分钟

**建议：**
```python
# 批量查询时使用延迟
import time

codes = ['002475', '300308', '300394']
for code in codes:
    data = api.get_fund_flow(code)
    time.sleep(0.5)  # 500ms 延迟
```

### 3. 数据缓存

```python
import pickle
from datetime import datetime, timedelta

# 缓存数据
def get_cached_data(code, cache_dir='/tmp/stock_cache'):
    cache_file = f"{cache_dir}/{code}.pkl"
    
    # 检查缓存是否有效（5 分钟内）
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        if datetime.now() - data['timestamp'] < timedelta(minutes=5):
            return data['content']
    
    # 获取新数据
    data = api.get_quote_sina(code)
    
    # 保存缓存
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_file, 'wb') as f:
        pickle.dump({'content': data, 'timestamp': datetime.now()}, f)
    
    return data
```

---

## 📁 文件结构

```
/home/admin/.openclaw/workspace/
├── scripts/
│   ├── stock_api.py                  # 实时行情 API
│   ├── stock_recommender_v3.py       # 推荐系统
│   ├── stock_visualizer_html.py      # HTML 可视化
│   └── stock_funds_browser.py        # 浏览器获取资金流
├── data/
│   └── charts/
│       └── dashboard_002475.html     # 生成的图表
└── docs/
    ├── stock_api.md                  # 本文档
    └── stock_visualizer.md           # 可视化文档
```

---

## 🔍 故障排查

### 问题 1：403 Forbidden

**原因：** 请求头不完整或频率过高

**解决：**
```python
# 添加完整请求头
headers = {
    'User-Agent': 'Mozilla/5.0...',
    'Accept': 'text/html...',
    'Referer': 'http://finance.sina.com.cn/'
}
```

### 问题 2：Connection aborted

**原因：** 网络不稳定或 API 限流

**解决：**
```python
# 添加重试机制
for attempt in range(3):
    try:
        data = api.get_fund_flow(code)
        if data:
            break
    except:
        time.sleep(1)
```

### 问题 3：数据解析失败

**原因：** API 返回格式变化

**解决：**
```python
# 添加数据验证
if not data or len(data) < 32:
    print("数据格式异常")
    return None
```

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-03-25 | 初始版本，支持新浪财经/东方财富 API |
| v1.1 | 2026-03-25 | 添加技术指标计算、批量查询 |

---

*最后更新：2026-03-25*
