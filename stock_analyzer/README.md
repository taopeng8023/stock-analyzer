# 📈 A 股智能选股系统

## 鹏总专用版本 v1.0

### 功能特点

- ✅ 输入股票代码，一键分析
- ✅ 输出能否买入建议
- ✅ 10 日目标收益预测
- ✅ 成功概率评估
- ✅ 技术面 + 基本面 + 资金面三维分析
- ✅ 自动止损止盈建议

---

### 安装依赖

```bash
cd /home/admin/.openclaw/workspace/stock_analyzer
pip install -r requirements.txt
```

---

### 使用方法

#### 方法 1: 命令行

```bash
python analyzer.py 603659
```

#### 方法 2: Python 调用

```python
from analyzer import StockAnalyzer

analyzer = StockAnalyzer()
report = analyzer.analyze("603659")

# 获取关键信息
print(f"能否买入：{report['buy_advice']['action']}")
print(f"10 日目标收益：{report['prediction']['10d_expected_return']}%")
print(f"成功概率：{report['success_probability']['probability']}%")
```

---

### 输出说明

| 字段 | 说明 |
|------|------|
| `buy_advice.action` | 买入建议 (强烈推荐买入/推荐买入/观望/不建议买入) |
| `buy_advice.position` | 建议仓位 |
| `prediction.10d_expected_return` | 10 日预期收益率 |
| `success_probability.probability` | 成功概率 (获得正收益的概率) |
| `target_prices.target_price` | 目标价位 |
| `target_prices.stop_loss` | 止损价位 |

---

### 评分标准

| 综合评分 | 建议 |
|---------|------|
| 85-100 | 强烈推荐买入 🟢 |
| 70-84 | 推荐买入 🟢 |
| 50-69 | 观望 🟡 |
| 0-49 | 不建议买入 🔴 |

---

### 策略逻辑

1. **技术面 (40%)**: 均线、MACD、RSI、KDJ、成交量、趋势
2. **基本面 (35%)**: ROE、成长性、负债率、估值
3. **资金面 (25%)**: 主力流入、成交量变化、北向资金

---

### 风险提示

⚠️ 本系统仅供参考，不构成投资建议
⚠️ 股市有风险，投资需谨慎
⚠️ 历史表现不代表未来收益
⚠️ 建议结合个人风险承受能力决策

---

### 版本历史

- v1.0 (2026-03-26): 初始版本，基础分析功能

---

### 联系

鹏总专用，如有问题请联系凯文优化
