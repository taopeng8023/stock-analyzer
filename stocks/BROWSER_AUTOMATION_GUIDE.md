# 🌐 浏览器自动化获取数据指南

## 为什么使用浏览器自动化？

**问题**: 直接 API 请求被反爬虫机制拦截，返回 HTML 页面

**解决**: 使用真实浏览器模拟用户访问，绕过反爬虫

---

## 方案对比

### 方案 1: Selenium（推荐 ⭐⭐⭐⭐⭐）

**优点**:
- ✅ 功能强大，支持所有浏览器操作
- ✅ 社区活跃，文档完善
- ✅ 支持 Chrome、Firefox 等

**缺点**:
- ⚠️ 需要安装 ChromeDriver
- ⚠️ 资源占用较大

**安装**:
```bash
pip install selenium webdriver-manager
```

**使用**:
```bash
cd /home/admin/.openclaw/workspace/stocks
python3 browser_automation.py
```

---

### 方案 2: Pyppeteer（轻量 ⭐⭐⭐⭐）

**优点**:
- ✅ 轻量级，基于 Puppeteer
- ✅ 无需额外驱动
- ✅ 适合服务器环境

**缺点**:
- ⚠️ 配置相对复杂
- ⚠️ 中文文档较少

**安装**:
```bash
pip install pyppeteer asyncio
```

**使用**:
```bash
python3 pyppeteer_automation.py
```

---

## 🚀 快速开始

### 1. 安装 Selenium（推荐）

```bash
# 安装依赖
pip install selenium webdriver-manager

# 验证安装
python3 -c "from selenium import webdriver; print('✅ Selenium 已安装')"
```

### 2. 运行测试

```bash
cd /home/admin/.openclaw/workspace/stocks

# 测试浏览器自动化
python3 browser_automation.py
```

### 3. 预期输出

```
✅ 浏览器初始化成功
📊 访问东方财富资金流向页面...
✅ 页面加载完成，开始提取数据...
✅ 成功获取 20 条数据

📊 主力资金流 TOP 10:

 1. 紫金矿业 (601899) ¥32.09 (+1.25%) 主力:12.50 亿
 2. 华电新能 (600930) ¥6.95 (+4.35%) 主力:8.20 亿
 ...

📁 数据已缓存：/home/admin/.openclaw/workspace/stocks/cache/browser/main_force_20260327_002500.json

✅ 测试成功！获取到 20 条数据
```

---

## 📁 文件说明

| 文件 | 功能 | 大小 |
|------|------|------|
| `browser_automation.py` | Selenium 浏览器自动化 | 7.7KB |
| `pyppeteer_automation.py` | Pyppeteer 自动化 | 5.3KB |
| `BROWSER_AUTOMATION_GUIDE.md` | 本文档 | - |

---

## 🔧 配置选项

### Selenium 配置

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()

# 无头模式（后台运行）
chrome_options.add_argument("--headless")

# 优化配置
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# 设置 User-Agent
chrome_options.add_argument("--user-agent=Mozilla/5.0...")

# 禁用图片（加速）
chrome_options.add_experimental_option("prefs", {
    "profile.managed_default_content_settings.images": 2,
})

# 启动浏览器
driver = webdriver.Chrome(options=chrome_options)
```

### Pyppeteer 配置

```python
from pyppeteer import launch

browser = await launch(
    headless=True,
    args=['--no-sandbox', '--disable-setuid-sandbox']
)
page = await browser.newPage()
await page.setUserAgent('Mozilla/5.0...')
```

---

## 💡 优化技巧

### 1. 加速加载

```python
# 禁用图片、CSS
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.default_content_setting_values.stylesheets": 2,
}
chrome_options.add_experimental_option("prefs", prefs)
```

### 2. 缓存数据

```python
# 保存到缓存
browser.save_to_cache(stocks, 'main_force_20260327.json')

# 下次优先读取缓存
if os.path.exists(cache_file):
    with open(cache_file) as f:
        data = json.load(f)
```

### 3. 错误处理

```python
try:
    stocks = browser.get_main_force_rank()
except Exception as e:
    print(f"获取失败：{e}")
    # 使用缓存数据
    stocks = load_from_cache()
```

---

## ⚠️ 常见问题

### Q1: ChromeDriver 安装失败？

**解决**:
```bash
# 自动安装（推荐）
pip install webdriver-manager

# 手动下载
# 访问 https://chromedriver.chromium.org/downloads
# 下载对应版本，放到 PATH 目录
```

### Q2: 浏览器启动失败？

**解决**:
```bash
# 安装 Chrome
apt-get update
apt-get install -y chromium-browser

# 或下载 Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i google-chrome-stable_current_amd64.deb
```

### Q3: 内存占用过高？

**解决**:
```python
# 使用无头模式
chrome_options.add_argument("--headless")

# 限制窗口大小
chrome_options.add_argument("--window-size=1280,720")

# 禁用 GPU
chrome_options.add_argument("--disable-gpu")

# 定期清理
browser.quit()  # 完全退出
```

### Q4: 数据提取失败？

**解决**:
```python
# 增加等待时间
WebDriverWait(driver, 30).until(...)

# 检查选择器
rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
print(f"找到 {len(rows)} 行")

# 如果为 0，说明页面结构变化
```

---

## 📊 数据流程

```
启动浏览器（无头模式）
    ↓
访问东方财富页面
    ↓
等待页面加载完成
    ↓
执行 JavaScript 提取数据
    ↓
解析股票数据
    ↓
保存到缓存
    ↓
关闭浏览器
```

---

## 🎯 集成到自动选股系统

修改 `auto_daily_push.py`:

```python
# 导入浏览器自动化
from browser_automation import EastmoneyBrowser

# 获取数据
browser = EastmoneyBrowser(headless=True)
try:
    main_force = browser.get_main_force_rank(page=1, page_size=100)
    browser.save_to_cache(main_force)
finally:
    browser.close()

# 后续分析...
```

---

## 📈 性能对比

| 方式 | 速度 | 稳定性 | 资源占用 |
|------|------|--------|---------|
| 直接 API | ⚡ 快 | ❌ 被拦截 | 低 |
| Selenium | 🐢 中 | ✅ 稳定 | 中 |
| Pyppeteer | 🐢 中 | ✅ 稳定 | 低 |

---

## ✅ 推荐方案

**生产环境**:
1. 使用 Selenium（稳定）
2. 开启无头模式
3. 缓存每日数据
4. 设置失败重试

**开发测试**:
1. 关闭无头模式（可见浏览器）
2. 调试数据提取
3. 验证数据准确性

---

**选股系统 v3.0** - 浏览器自动化方案

**下一步**: 安装 Selenium → 测试 → 集成到自动推送
