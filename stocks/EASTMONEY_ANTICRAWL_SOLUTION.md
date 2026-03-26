# 东方财富反爬解决方案

**问题**：东方财富 API 返回 `rc=102` 或连接被重置

**原因**：
1. IP 频率限制
2. 请求头不完整
3. 缺少 Cookie
4. 数据中心风控升级

---

## ✅ 已实施的解决方案

### 1. 完整请求头
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://data.eastmoney.com/zjlx/',
}
```

### 2. 随机延迟
```python
time.sleep(2 + random.uniform(0, 2))  # 2-4 秒随机延迟
```

### 3. 多 API 端点轮换
```python
api_urls = [
    'https://push2.eastmoney.com/api/qt/clist/get',
    'https://push2his.eastmoney.com/api/qt/clist/get',
]
```

### 4. 重试机制
```python
max_retries = 3  # 最多重试 3 次
```

---

## 🔧 进阶解决方案（如需更高稳定性）

### 方案 1：使用代理 IP（推荐）

**适用场景**：高频抓取、生产环境

**服务商推荐**：
| 服务商 | 价格 | 说明 |
|--------|------|------|
| 快代理 | ¥100/月 | https://www.kuaidaili.com |
| 讯代理 | ¥50/月 | https://www.xdaili.cn |
| 芝麻代理 | ¥80/月 | https://www.zhimadaili.com |

**代码集成**：
```python
# 安装：pip install requests
proxies = {
    'http': 'http://username:password@proxy_ip:port',
    'https': 'http://username:password@proxy_ip:port',
}

resp = requests.get(url, params=params, proxies=proxies, timeout=15)
```

---

### 方案 2：使用 Playwright 浏览器自动化

**适用场景**：API 完全无法访问时

**安装**：
```bash
pip install playwright
playwright install
```

**代码示例**：
```python
from playwright.sync_api import sync_playwright

def crawl_with_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto('https://data.eastmoney.com/zjlx/', wait_until='networkidle')
        page.wait_for_timeout(5000)  # 等待 5 秒
        
        # 截取页面（可选）
        page.screenshot(path='eastmoney.png')
        
        # 获取数据（需要分析页面结构）
        data = page.evaluate('() => { /* JS 代码 */ }')
        
        browser.close()
        return data
```

---

### 方案 3：更换数据源

**如果东方财富持续不可用，考虑以下替代方案**：

#### 3.1 腾讯财经（已集成）
```python
crawler.crawl_tencent()  # 实时行情、成交额
```

#### 3.2 新浪财经
```python
# 接口：http://hq.sinajs.cn/list=s_sh600000
url = "http://hq.sinajs.cn/list=s_sh600000"
```

#### 3.3 百度股市通（已集成，但有时不稳定）
```python
crawler.crawl_baidu_rank('change')
```

#### 3.4 AKShare（开源财经数据接口）
```bash
pip install akshare
```

```python
import akshare as ak

# 个股资金流
stock_individual_fund_flow(symbol="600000", period="5 日")
```

---

## 📋 当前工作流策略

由于东方财富反爬严格，当前工作流采用以下策略：

```
1. 优先尝试东方财富（3 次重试）
2. 如果失败，使用腾讯财经数据替代
3. 腾讯财经数据足够支持主力分析（成交额排行）
```

**影响评估**：
- 东方财富主要提供"板块资金流"数据
- 个股分析主要依赖腾讯财经的成交额、涨跌幅数据
- 当前策略下，工作流仍可正常运行

---

## 🚀 长期建议

### 1. 多数据源冗余
```
腾讯财经 (主) + 新浪财经 (备) + AKShare(备)
```

### 2. 请求频率控制
```
单 IP 每分钟不超过 5 次请求
每次请求间隔 2-5 秒随机
```

### 3. 缓存策略
```
同一数据 5 分钟内不重复抓取
使用本地缓存减少 API 调用
```

### 4. 监控告警
```
数据源失败时发送告警
自动切换到备用数据源
```

---

## 📞 如问题持续

如果东方财富持续无法访问，建议：

1. **检查 IP 是否被封锁**：
   ```bash
   curl -I https://data.eastmoney.com
   ```

2. **更换网络环境**：
   - 切换 WiFi/4G/5G
   - 使用云服务器（不同地域）

3. **联系数据源方**：
   - 东方财富开放平台：https://open.eastmoney.com
   - 申请正式 API 权限

---

**更新时间**：2026-03-23  
**状态**：腾讯财经可用，东方财富间歇性失败
