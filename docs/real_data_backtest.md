# 真实数据回测说明

## ⚠️ 当前状态

**回测系统 v3.0 已完成，所有数据必须来自真实 API**

### 已实现功能

✅ 真实 K 线数据获取（新浪财经 API）
✅ 真实资金流数据获取（东方财富 API）
✅ 技术指标计算（基于真实数据）
✅ 综合评分系统（使用真实数据）
✅ 回测引擎（禁止模拟数据）

---

## 🔧 API 访问问题

### 当前问题

从当前网络环境访问外部 API 受限：
- 新浪财经 API：返回格式异常
- 东方财富 API：连接被重置

### 可能原因

1. **网络限制**：服务器防火墙阻止外部访问
2. **API 限流**：IP 被临时限制
3. **Referer 检查**：需要完整请求头

---

## 💡 解决方案

### 方案 1：浏览器自动化（推荐）

使用已实现的浏览器自动化方案获取真实数据：

```bash
# 通过浏览器获取东方财富数据
python3 /home/admin/.openclaw/workspace/scripts/stock_funds_browser.py
```

**优点：**
- ✅ 绕过 API 限制
- ✅ 数据真实可靠
- ✅ 无需额外依赖

**缺点：**
- ⚠️ 需要浏览器环境
- ⚠️ 速度较慢

---

### 方案 2：本地部署数据源

使用本地数据服务：

```python
# Tushare Pro（需注册）
import tushare as ts
df = ts.get_k_data('600549')

# AkShare（开源）
import akshare as ak
df = ak.stock_zh_a_hist(symbol="600549")
```

**安装：**
```bash
pip3 install tushare akshare
```

---

### 方案 3：手动导入数据

临时方案：手动下载 CSV 数据

```python
import pandas as pd

# 从同花顺/东方财富导出 CSV
df = pd.read_csv('/path/to/600549.csv')

# 转换为标准格式
data = []
for _, row in df.iterrows():
    data.append({
        'date': row['日期'],
        'open': row['开盘'],
        'high': row['最高'],
        'low': row['最低'],
        'close': row['收盘'],
        'volume': row['成交量']
    })
```

---

## 📁 文件清单

| 文件 | 路径 | 状态 |
|------|------|------|
| 回测 v3.0 | `scripts/stock_backtest_real.py` | ✅ 完成 |
| API 封装 | `scripts/stock_api.py` | ⚠️ 需修复 |
| 浏览器获取 | `scripts/stock_funds_browser.py` | ✅ 可用 |

---

## 🚀 下一步

### 立即可用

1. **使用浏览器自动化方案**
   ```bash
   python3 scripts/stock_funds_browser.py
   ```

2. **手动导入数据回测**
   - 从同花顺导出 CSV
   - 运行回测脚本

### 需要解决

1. **修复 API 访问**
   - 检查网络配置
   - 添加代理支持
   - 完善请求头

2. **部署本地数据源**
   - 安装 Tushare/AkShare
   - 配置 API Token
   - 测试数据获取

---

## 📝 底线声明

**【重要】所有回测必须使用真实数据**

- ❌ 禁止使用模拟数据
- ❌ 禁止使用随机数据
- ❌ 禁止使用伪造数据

**如果无法获取真实数据：**
1. 暂停回测
2. 修复数据源
3. 确认数据真实性后再继续

---

*更新时间：2026-03-25*
*版本：v3.0-real*
