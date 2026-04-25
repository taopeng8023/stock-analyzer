# 🎓 个人股票研究系统 - 完整指南

**⚠️ 仅用于个人研究学习，不得用于真实交易**

---

## ✅ 系统已就绪

你的个人股票研究系统已经搭建完成！

---

## 📁 文件清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `research_db.py` | SQLite 数据库管理 | ✅ 完成 |
| `research_import.py` | 数据导入工具 | ✅ 完成 |
| `research_simple.py` | 简易分析工具 | ✅ 完成 |
| `research.db` | SQLite 数据库 | ✅ 已创建 |
| `RESEARCH_GUIDE.md` | 详细使用指南 | ✅ 完成 |

---

## 🚀 快速开始

### 1. 查看数据库状态

```bash
python3 research_simple.py
```

### 2. 分析股票

```bash
# 演示分析（使用数据库中的股票）
python3 research_simple.py --demo

# 分析指定股票
python3 research_simple.py --code 600000.SH
```

### 3. 导入更多数据

```bash
# 生成示例数据（学习用）
python3 research_import.py --sample --days 250

# 从 Tushare 导入真实数据（需要 Token）
python3 research_import.py --code 600000.SH
```

---

## 📊 当前系统功能

### ✅ 已实现

1. **数据管理**
   - SQLite 本地存储
   - 日线行情数据
   - 资金流数据
   - 股票基本信息

2. **数据分析**
   - 价格趋势分析
   - 均线计算（MA5/MA20）
   - 资金流统计
   - 收益率计算

3. **数据导入**
   - 示例数据生成
   - Tushare 接口（需 Token）
   - CSV 文件导入

### ⏳ 可扩展

1. **技术指标**
   - MACD
   - KDJ
   - RSI
   - 布林带

2. **策略回测**
   - 均线策略
   - 动量策略
   - 均值回归

3. **可视化**
   - K 线图
   - 成交量图
   - 资金流图

---

## 📈 示例输出

```
======================================================================
📈 600000.SH 简易分析
======================================================================

价格统计:
  期间：2026-01-16 ~ 2026-03-16
  起始价：¥12.98
  结束价：¥12.18
  总收益：-6.16%

均线分析:
  当前价格：¥12.18
  MA5: ¥12.27 ↓
  MA20: ¥11.82 ↑

资金流统计 (近 30 日):
  累计净流入：7230.84 万
  净流入天数：19/30
======================================================================
```

---

## 🎯 学习路径

### 初级：熟悉系统

```bash
# 1. 查看数据库
python3 research_simple.py

# 2. 生成示例数据
python3 research_import.py --sample --days 60

# 3. 分析股票
python3 research_simple.py --demo
```

### 中级：数据分析

学习使用 Python 分析数据：

```python
from research_db import ResearchDatabase

db = ResearchDatabase()

# 查询数据
data = db.query_daily('600000.SH', limit=60)

# 计算指标
prices = [d['close'] for d in data]
ma5 = sum(prices[-5:]) / 5

# 分析趋势
```

### 高级：策略回测

实现自己的交易策略：

```python
def backtest_strategy(data):
    """回测交易策略"""
    capital = 100000  # 初始资金
    position = 0
    
    for i, bar in enumerate(data):
        # 你的策略逻辑
        if should_buy(bar, data[:i]):
            position = bar['close']
        elif should_sell(bar, data[:i]) and position > 0:
            profit = bar['close'] - position
            capital += profit
            position = 0
    
    return capital
```

---

## 📚 学习资源

### 书籍

- 《Python 编程：从入门到实践》
- 《利用 Python 进行数据分析》
- 《量化交易：如何建立自己的算法交易业务》

### 在线平台

- 聚宽：https://www.joinquant.com
- 优矿：https://uqer.datayes.com
- 米筐：https://www.ricequant.com

### 数据源

- Tushare：https://tushare.pro（需要 120 积分）
- 腾讯财经：免费实时行情
- 新浪财经：免费历史数据

---

## ⚠️ 重要声明

### 合法用途

✅ **允许：**
- 个人学习研究
- 数据分析练习
- 策略回测测试
- 教学演示

❌ **禁止：**
- 用于真实交易决策
- 向他人展示为真实业绩
- 误导性宣传
- 任何欺诈用途

### 数据说明

1. **示例数据** - 随机生成，仅用于学习
2. **Tushare 数据** - 真实市场数据，可用于研究
3. **所有分析结果** - 仅供参考，不构成投资建议

### 风险提示

- 本研究系统**仅供学习**
- **不构成**任何投资建议
- 回测结果**不代表**实际交易收益
- 实盘交易存在**亏损风险**

---

## 🔧 技术栈

- **语言：** Python 3.6+
- **数据库：** SQLite3
- **依赖：** 标准库（无需额外安装）
- **可选：** pandas（用于高级分析）

---

## 📝 下一步

### 1. 学习数据库操作

```bash
# 查询数据
python3 research_db.py --query 600000.SH

# 导出数据
python3 research_db.py --export 600000.SH
```

### 2. 导入真实数据

```bash
# 配置 Tushare Token
python3 tushare_flow.py --config <your_token>

# 导入数据
python3 research_import.py --code 600000.SH
```

### 3. 学习分析

阅读 `RESEARCH_GUIDE.md` 了解详细分析方法

---

## 📞 帮助

查看详细文档：
- `RESEARCH_GUIDE.md` - 完整使用指南
- `TUSHARE_SETUP.md` - Tushare 配置指南
- `CURRENT_STATUS.md` - 当前系统状态

---

**创建时间：2026-03-17**

**版本：v1.0**

**⚠️ 仅用于个人研究学习，不得用于真实交易**

祝你学习愉快！📚📈
