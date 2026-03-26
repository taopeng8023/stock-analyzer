# 📊 同花顺数据使用指南

**⚠️ 仅用于个人研究学习，不得用于商业用途**

---

## 📋 同花顺数据概况

### 数据源信息

| 项目 | 说明 |
|------|------|
| **官网** | http://www.10jqka.com.cn |
| **数据质量** | ⭐⭐⭐⭐⭐ 准确、及时 |
| **访问方式** | 网页爬虫（无官方 API） |
| **使用门槛** | 免费，但需处理反爬 |
| **法律风险** | ⚠️ 仅限个人学习 |

---

## ✅ 可用数据

### 1. 个股资金流

**URL:** `http://data.10jqka.com.cn/stock/zjlx/`

**数据字段:**
- 股票代码/名称
- 主力净流入
- 超大单净流入
- 大单净流入
- 中单净流入
- 小单净流入

### 2. 板块资金流

**URL:** `http://data.10jqka.com.cn/industry/zjlx/`

**数据字段:**
- 板块名称
- 主力净流入
- 涨跌幅
- 领涨股

### 3. 行情数据

**URL:** `http://q.10jqka.com.cn/`

**数据字段:**
- 实时价格
- 涨跌幅
- 成交量/成交额
- 换手率

---

## ⚠️ 使用要求

### 1. 技术要求

**反爬机制:**
- ✅ User-Agent 验证
- ✅ Referer 验证
- ✅ 访问频率限制
- ⚠️ 可能需要 Cookie
- ⚠️ 可能有 IP 限制

**解决方案:**
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://www.10jqka.com.cn/',
    'Cookie': 'your_cookie_here',  # 可能需要
}
```

### 2. 法律要求

**允许用途:**
- ✅ 个人学习研究
- ✅ 数据分析练习
- ✅ 非商业目的

**禁止用途:**
- ❌ 商业用途
- ❌ 数据转售
- ❌ 大规模爬取
- ❌ 实时行情服务

### 3. 使用规范

**访问频率:**
```python
# ✅ 推荐：每次请求间隔 1-2 秒
import time
time.sleep(1)

# ❌ 禁止：高频请求
# 可能被 IP 封禁
```

**数据量:**
- 建议单次不超过 100 条
- 每日不超过 1000 次请求
- 避免同时多线程访问

---

## 🔧 技术实现

### 方案 1：简单爬虫

```python
import requests
from bs4 import BeautifulSoup

def get_ths_moneyflow():
    """获取同花顺资金流数据"""
    
    url = "http://data.10jqka.com.cn/stock/zjlx/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://data.10jqka.com.cn/',
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        
        # 解析 HTML
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 提取数据
        # ...
        
        return data
    except Exception as e:
        print(f"获取失败：{e}")
        return None
```

### 方案 2：使用现成库

**AKShare** (推荐):
```python
import akshare as ak

# 个股资金流
data = ak.stock_individual_fund_flow(symbol="浦发银行", market="沪")
print(data)

# 行业资金流
data = ak.stock_fund_flow_industry(symbol="今日")
print(data)
```

**安装:**
```bash
pip install akshare
```

---

## 📊 与 Tushare 对比

| 特性 | 同花顺 | Tushare |
|------|--------|---------|
| **数据质量** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **获取难度** | ⭐⭐⭐ (需爬虫) | ⭐⭐⭐⭐⭐ (API) |
| **稳定性** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **文档** | ❌ 无官方文档 | ✅ 完整文档 |
| **授权** | ⚠️ 模糊 | ✅ 明确授权 |
| **成本** | 免费 | 免费 (基础) |
| **推荐度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🎯 推荐使用场景

### ✅ 适合使用同花顺

1. **Tushare 权限不足**
   - 积分不够
   - 接口未审批

2. **临时数据需求**
   - 快速获取少量数据
   - 一次性分析

3. **学习爬虫技术**
   - 练习网页解析
   - 数据处理练习

### ❌ 不适合使用同花顺

1. **长期项目**
   - 需要稳定数据源
   - 建议用 Tushare

2. **商业用途**
   - 法律风险高
   - 建议购买授权

3. **大规模数据**
   - 可能被反爬
   - 建议用专业数据服务

---

## 💡 最佳实践

### 1. 优先顺序

```
1. Tushare Pro ⭐⭐⭐⭐⭐
   - 有明确授权
   - 稳定的 API
   - 完整文档

2. 腾讯财经 ⭐⭐⭐⭐
   - 真实数据
   - 稳定性好
   - 已集成

3. 同花顺 ⭐⭐⭐
   - 数据准确
   - 需处理反爬
   - 法律风险

4. 其他数据源 ⭐⭐
   - 谨慎使用
```

### 2. 使用建议

```python
# ✅ 正确做法
def get_data():
    # 1. 优先 Tushare
    data = fetch_from_tushare()
    if data:
        return data
    
    # 2. 备用腾讯
    data = fetch_from_tencent()
    if data:
        return data
    
    # 3. 最后考虑同花顺
    data = fetch_from_ths()
    return data

# ❌ 错误做法
def get_data():
    # 直接爬同花顺，不考虑其他数据源
    return fetch_from_ths()
```

### 3. 频率控制

```python
import time
import random

def fetch_with_delay(urls):
    """带延迟的爬取"""
    for url in urls:
        try:
            data = fetch(url)
            yield data
            
            # 随机延迟 1-2 秒
            time.sleep(1 + random.random())
        except Exception as e:
            print(f"获取失败：{e}")
```

---

## ⚖️ 法律风险提示

### 风险等级

| 行为 | 风险等级 | 说明 |
|------|---------|------|
| 个人学习 | ⚠️ 低 | 合理使用 |
| 少量爬取 | ⚠️ 低 | 控制频率 |
| 大量爬取 | ⚠️ 中 | 可能被封 IP |
| 商业用途 | ❌ 高 | 可能被告 |
| 数据转售 | ❌ 极高 | 违法 |

### 免责建议

1. **明确用途**
   - 仅用于个人学习
   - 不对外公开
   - 不用于商业

2. **控制频率**
   - 遵守 robots.txt
   - 低频访问
   - 避免高峰时段

3. **标注来源**
   - 注明数据来源
   - 不声称自有
   - 不修改版权信息

4. **及时删除**
   - 研究完成后删除
   - 不长期存储
   - 不建立数据库

---

## 📞 替代方案

### 如果同花顺不可用

**方案 1：Tushare（推荐）**
```bash
# 等待权限审批
python3 tushare_flow.py --check
```

**方案 2：腾讯财经**
```bash
# 真实成交额估算
python3 fund_flow.py --top 20
```

**方案 3：AKShare**
```bash
# 安装
pip install akshare

# 使用
python3 -c "import akshare as ak; print(ak.stock_individual_fund_flow(symbol='浦发银行', market='沪'))"
```

---

## 📚 相关文档

- `DATA_POLICY.md` - 总数据政策
- `TUSHARE_SETUP.md` - Tushare 配置
- `CURRENT_STATUS_FINAL.md` - 当前状态

---

**最后更新：2026-03-17 23:50**

**⚠️ 仅用于个人研究学习，不得用于商业用途**
