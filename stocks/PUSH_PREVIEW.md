# 📱 鹏总选股信号推送预览

**时间**: 2026-03-26 23:50  
**状态**: 待配置企业微信 webhook

---

## 🎯 推送配置步骤

### 1️⃣ 获取企业微信 Webhook

1. 打开企业微信 → 选择一个群
2. 群设置 → 群机器人 → 添加
3. 选择"自定义机器人"
4. 命名：鹏总选股助手
5. **复制 webhook 地址**

### 2️⃣ 修改配置文件

编辑：`/home/admin/.openclaw/workspace/stocks/push_config.json`

```json
{
    "wecom": {
        "enabled": true,
        "webhook": "https://qyapi.weixin.qq.com/cgi/webhook/send?key=你的 KEY"
    }
}
```

**替换**: `你的 KEY` 为实际 webhook 中的 key

### 3️⃣ 测试推送

```bash
cd /home/admin/.openclaw/workspace/stocks
python3 push_to_wecom.py --stock 601899
```

---

## 📊 推送效果预览

### 选股信号推送示例

```
🟢 选股信号：紫金矿业 (601899)

📊 分析结果
- 现价：¥32.09 (+1.25%)
- 综合评分：77.4 分
  - 技术面：75
  - 基本面：82
  - 资金面：73

💡 操作建议
- 建议：🟢 推荐买入
- 仓位：25-35%

📈 收益预测
- 10 日预期：+9.7%
- 成功概率：71.2% (较高)
- 目标价：¥35.20 (+9.7%)
- 止损价：¥29.52 (-8%)

📋 交易策略
- 分批建仓，首笔 30%
- 止损位：-8%
- 止盈位：+25%
- 持有周期：5-10 天

---
生成时间：2026-03-26 23:50:00
鹏总选股系统 v3.0
```

### 主力排名推送示例

```
📊 主力净流入 TOP 10

更新时间：2026-03-26 15:30:00

💰 主力排名

1. 紫金矿业 (601899)
- 价格：¥32.09 (+1.25%)
- 主力：12.50 亿 (8.50%)

2. 华电新能 (600930)
- 价格：¥6.95 (+4.35%)
- 主力：8.20 亿 (6.20%)

3. 璞泰来 (603659)
- 价格：¥31.43 (+2.10%)
- 主力：5.80 亿 (5.80%)

---
数据来源：东方财富
鹏总选股系统 v3.0
```

### 板块排名推送示例

```
🏭 行业板块资金流向 TOP 10

更新时间：2026-03-26 15:30:00

🔥 热门板块

1. 半导体
- 最新价：1250.50 (+3.25%)
- 主力：125.50 亿 (8.50%)

2. 电子设备
- 最新价：980.20 (+2.80%)
- 主力：85.20 亿 (6.20%)

3. 通信设备
- 最新价：750.30 (+1.95%)
- 主力：65.30 亿 (5.80%)

---
数据来源：东方财富
鹏总选股系统 v3.0
```

---

## ⚙️ 自动化推送设置

### 定时任务

```bash
crontab -e

# 早盘推送主力 TOP 10 (交易日 08:30)
30 8 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 push_to_wecom.py --top 10

# 盘后推送板块排名 (交易日 15:30)
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 push_to_wecom.py --sector

# 监控股票池 (每 30 分钟)
*/30 9-15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 auto_monitor_wecom.py
```

### 监控股票池

创建 `auto_monitor_wecom.py`:

```python
#!/usr/bin/env python3
from push_to_wecom import push_stock_signal

# 监控的股票池
WATCH_LIST = [
    '601899',  # 紫金矿业
    '600930',  # 华电新能
    '603659',  # 璞泰来
    '000962',  # 东方钽业
    '600089',  # 特变电工
]

for code in WATCH_LIST:
    push_stock_signal(code)
```

---

## 📱 推送条件

### 自动推送阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `min_score_to_push` | 70 | 最低推送评分 |
| `push_top_n` | 10 | 推送 TOP N |
| `emergency_push` | true | 紧急推送 |

### 推送触发条件

**选股信号**:
- ✅ 综合评分 ≥ 70
- ✅ 建议为"推荐买入"或"强烈推荐买入"

**主力排名**:
- ✅ 每日盘后推送
- ✅ 主力净流入 TOP 10

**板块排名**:
- ✅ 每日盘后推送
- ✅ 行业板块 TOP 10

**紧急预警**:
- ✅ 触及止损线 (-8%)
- ✅ 达到目标价 (+25%)

---

## 🔧 快速测试

### 方法 1: 命令行推送

```bash
cd /home/admin/.openclaw/workspace/stocks

# 推送个股
python3 push_to_wecom.py --stock 601899

# 推送主力排名
python3 push_to_wecom.py --top 10

# 推送板块排名
python3 push_to_wecom.py --sector
```

### 方法 2: Python 调用

```python
from push_to_wecom import push_stock_signal

# 推送选股信号
push_stock_signal('601899')
```

### 方法 3: 查看推送历史

```bash
cat /home/admin/.openclaw/workspace/stocks/cache/push_signals.json
```

---

## ⚠️ 当前状态

### ✅ 已完成
- 推送脚本已就绪
- 配置文件已创建
- 推送格式已定义

### ⏳ 待完成
- **配置企业微信 webhook** ← 需要鹏总操作
- **测试推送** ← 配置后测试
- **设置定时任务** ← 测试后设置

---

## 📖 完整文档

**配置指南**: `/home/admin/.openclaw/workspace/stocks/WECOM_PUSH_SETUP.md`

**推送脚本**: `/home/admin/.openclaw/workspace/stocks/push_to_wecom.py`

**配置文件**: `/home/admin/.openclaw/workspace/stocks/push_config.json`

---

## 🚀 下一步

**鹏总，请**:

1. **获取企业微信 webhook**
   - 群设置 → 群机器人 → 添加
   - 复制 webhook 地址

2. **修改配置文件**
   ```bash
   vi /home/admin/.openclaw/workspace/stocks/push_config.json
   ```
   替换 webhook 地址

3. **测试推送**
   ```bash
   cd /home/admin/.openclaw/workspace/stocks
   python3 push_to_wecom.py --stock 601899
   ```

**配置完成后，选股信号会自动推送到您的企业微信！** 📱

需要我帮您测试推送吗？🚀
