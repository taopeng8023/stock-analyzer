# 股票数据 API 数据源汇总

## 免费可用的股票数据 API

### 1. 腾讯财经 API ✅ (已使用)
- **实时行情**: `http://qt.gtimg.cn/q=sh600000`
- **历史数据**: `http://data.gtimg.cn/flashdata/hushen/minute/sh600000.js`
- **优点**: 免费、无需 key、数据准确
- **缺点**: 有反爬限制、需要控制请求频率
- **状态**: ⚠️ 历史数据 API 可能不稳定

### 2. 新浪财经 API ✅ (已使用)
- **实时行情**: `http://hq.sinajs.cn/list=sh600000`
- **历史 K 线**: `http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData`
- **优点**: 免费、数据完整
- **缺点**: IP 限制严格、容易 456 错误
- **状态**: ❌ 当前被限制

### 3. 东方财富 API
- **股票列表**: `http://nufm.dfcfw.com/EM_Fund2099/QF_StockStock/GetStockList`
- **实时行情**: `http://push2.eastmoney.com/api/qt/stock/get`
- **优点**: 数据全面、更新及时
- **缺点**: 需要解析复杂 JSON、有反爬
- **状态**: ⚠️ 需要测试

### 4. 网易财经 API
- **实时行情**: `http://quotes.money.163.com/service/stockquote.html`
- **历史数据**: `http://quotes.money.163.com/service/chddata.html`
- **优点**: 免费、提供 CSV 格式
- **缺点**: 文档少、需要摸索
- **状态**: 📝 待测试

### 5. 百度财经 API
- **实时行情**: `https://finance.baidu.com/quote/`
- **优点**: 大厂稳定
- **缺点**: 需要逆向分析
- **状态**: 📝 待测试

### 6. 同花顺 API
- **实时行情**: `http://d.10jqka.com.cn/`
- **优点**: 数据准确
- **缺点**: 反爬严格
- **状态**: 📝 待测试

### 7. 雪球 API
- **实时行情**: `https://stock.xueqiu.com/v5/stock/quote.json`
- **优点**: 数据丰富
- **缺点**: 需要登录、有 token
- **状态**: ⚠️ 需要认证

### 8. 优矿/米筐 (需要注册)
- **API**: `https://api.myquant.cn/`
- **优点**: 专业量化平台、数据完整
- **缺点**: 需要注册、有调用限制
- **状态**: 📝 需要注册

### 9. Tushare Pro (需要 token)
- **API**: `https://api.tushare.pro/`
- **优点**: 专业金融数据、文档完善
- **缺点**: 需要积分、部分数据收费
- **状态**: 📝 需要 token

### 10. AKShare (开源库)
- **GitHub**: `https://github.com/akfamily/akshare`
- **优点**: 开源免费、数据源多
- **缺点**: 需要安装 Python 库
- **状态**: ✅ 推荐使用

---

## 推荐方案

### 方案 1: 多数据源轮询 (推荐)
```python
# 依次尝试不同数据源，避免单点故障
sources = [
    'tencent',  # 腾讯
    'netease',  # 网易
    'eastmoney', # 东方财富
    'akshare',  # AKShare
]

for source in sources:
    data = get_data(source, code)
    if data:
        break
```

### 方案 2: 使用 AKShare 库
```bash
pip install akshare
```

```python
import akshare as ak

# 获取 A 股实时行情
stock_info = ak.stock_zh_a_spot_em()

# 获取历史数据
stock_history = ak.stock_zh_a_hist(symbol="601857", period="daily")
```

### 方案 3: 本地缓存 + 增量更新
```python
# 减少 API 调用
cache = load_cache()
for stock in all_stocks:
    if stock in cache and not is_expired(cache[stock]):
        continue
    data = fetch_from_api(stock)
    cache[stock] = data
save_cache(cache)
```

---

## 实施建议

1. **优先使用 AKShare** - 开源免费、维护活跃
2. **多数据源备份** - 腾讯 + 网易 + 东方财富轮询
3. **添加缓存机制** - 减少 API 调用频率
4. **控制请求频率** - 每请求间隔 50-100ms
5. **使用代理 IP** - 避免 IP 被封

---

## 下一步行动

1. 安装 AKShare: `pip install akshare`
2. 测试 AKShare 数据获取
3. 实现多数据源轮询机制
4. 添加本地缓存
5. 重新运行全市场筛选
