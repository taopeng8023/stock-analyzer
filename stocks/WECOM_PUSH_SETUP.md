# 📱 企业微信推送配置指南

## 鹏总选股系统 - 选股信号推送到企业微信

---

## 🚀 快速开始

### 1. 获取企业微信 Webhook

#### 方法一：群机器人（推荐）

1. **打开企业微信群**
   - 选择一个群（或新建群）

2. **添加群机器人**
   - 群设置 → 群机器人 → 添加
   - 选择"自定义机器人"

3. **配置机器人**
   - 名称：鹏总选股助手
   - 头像：可选
   - 点击"添加"

4. **复制 Webhook**
   - 添加成功后，复制 webhook 地址
   - 格式：`https://qyapi.weixin.qq.com/cgi/webhook/send?key=xxxxxxxx`

#### 方法二：企业微信应用

1. 登录企业微信管理后台
2. 应用管理 → 自建应用
3. 创建应用
4. 获取 CorpID、AgentID、Secret

---

### 2. 配置文件

编辑 `/home/admin/.openclaw/workspace/stocks/push_config.json`：

```json
{
    "wecom": {
        "enabled": true,
        "webhook": "https://qyapi.weixin.qq.com/cgi/webhook/send?key=YOUR_KEY_HERE"
    },
    "wechat": {
        "enabled": false,
        "corp_id": "",
        "agent_id": "",
        "corp_secret": ""
    },
    "dingtalk": {
        "enabled": false,
        "webhook": "",
        "secret": ""
    },
    "email": {
        "enabled": false
    },
    "push_settings": {
        "daily_report_time": "08:30",
        "after_market_time": "15:30",
        "emergency_push": true,
        "push_top_n": 10,
        "min_score_to_push": 70
    }
}
```

**重点修改**:
- `wecom.webhook`: 填入你的 webhook 地址
- `wecom.enabled`: 设为 `true`
- `min_score_to_push`: 推送阈值（默认 70 分）

---

### 3. 测试推送

```bash
cd /home/admin/.openclaw/workspace/stocks

# 测试推送（会发送测试消息）
python3 push_to_wecom.py

# 推送个股信号
python3 push_to_wecom.py --stock 601899

# 推送主力 TOP 10
python3 push_to_wecom.py --top 10

# 推送板块排名
python3 push_to_wecom.py --sector
```

---

## 📊 推送效果

### 选股信号推送

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
生成时间：2026-03-26 23:45:00
鹏总选股系统 v3.0
```

### 主力排名推送

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

...

---
数据来源：东方财富
鹏总选股系统 v3.0
```

### 板块排名推送

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

...

---
数据来源：东方财富
鹏总选股系统 v3.0
```

---

## ⚙️ 自动化推送

### 设置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加以下任务

# 早盘推送 (交易日 08:30)
30 8 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 push_to_wecom.py --top 10

# 盘后推送 (交易日 15:30)
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 push_to_wecom.py --sector

# 实时监控 (每 30 分钟)
*/30 9-15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 auto_monitor_wecom.py
```

### 自动监控脚本

创建 `auto_monitor_wecom.py`：

```python
#!/usr/bin/env python3
"""
自动监控选股信号并推送
"""

from push_to_wecom import push_stock_signal
import json
import os

# 监控的股票池
WATCH_LIST = [
    '601899',  # 紫金矿业
    '600930',  # 华电新能
    '603659',  # 璞泰来
    '000962',  # 东方钽业
    '600089',  # 特变电工
]

# 推送阈值
MIN_SCORE = 70

def main():
    """主函数"""
    print("🔍 开始监控选股信号...")
    
    for code in WATCH_LIST:
        # 分析股票
        result = analyze_and_push(code, MIN_SCORE)
        
        if result:
            print(f"✅ {code} 已推送")
        else:
            print(f"⚪ {code} 未达推送标准")
    
    print("✅ 监控完成")

def analyze_and_push(code, min_score):
    """分析并推送"""
    try:
        from stock_analyzer.stock_analyzer_v2 import EnhancedStockAnalyzer
        
        analyzer = EnhancedStockAnalyzer()
        report = analyzer.analyze(code)
        
        if 'error' in report:
            return False
        
        score = report['scores']['total']
        
        if score >= min_score:
            # 推送
            from push_to_wecom import push_stock_signal
            push_stock_signal(code)
            return True
        
        return False
    
    except Exception as e:
        print(f"❌ 分析失败：{e}")
        return False

if __name__ == "__main__":
    main()
```

---

## 🔧 常见问题

### Q1: 推送失败？

**检查**:
1. webhook 地址是否正确
2. 网络是否通畅
3. 企业微信机器人是否启用

**解决**:
```bash
# 测试 webhook
curl -X POST "https://qyapi.weixin.qq.com/cgi/webhook/send?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"msgtype":"text","text":{"content":"测试"}}'
```

### Q2: 消息格式错误？

**检查**:
- Markdown 语法是否正确
- 特殊字符是否转义

### Q3: 推送太频繁被限制？

**解决**:
- 降低推送频率
- 设置推送时间间隔
- 使用企业微信应用推送（限额更高）

### Q4: 如何查看推送历史？

**查看**:
```bash
cat /home/admin/.openclaw/workspace/stocks/cache/push_signals.json
```

---

## 📈 推送记录

推送历史保存在：
```
/home/admin/.openclaw/workspace/stocks/cache/push_signals.json
```

**格式**:
```json
[
  {
    "timestamp": "2026-03-26 23:45:00",
    "stock_code": "601899",
    "stock_name": "紫金矿业",
    "score": 77.4,
    "action": "推荐买入",
    "success": true
  }
]
```

---

## 🎯 推送策略

### 推荐配置

| 参数 | 值 | 说明 |
|------|-----|------|
| min_score_to_push | 70 | 推送阈值 |
| push_top_n | 10 | 推送 TOP N |
| daily_report_time | 08:30 | 早盘推送 |
| after_market_time | 15:30 | 盘后推送 |
| emergency_push | true | 紧急推送 |

### 推送条件

**选股信号推送**:
- 综合评分 ≥ 70
- 建议为"推荐买入"或"强烈推荐买入"

**主力排名推送**:
- 每日盘后推送
- 主力净流入 TOP 10

**板块排名推送**:
- 每日盘后推送
- 行业板块 TOP 10

**紧急推送**:
- 止损预警
- 止盈提醒
- 重大利好/利空

---

## ✅ 配置完成检查

```bash
cd /home/admin/.openclaw/workspace/stocks

# 1. 检查配置文件
cat push_config.json

# 2. 测试推送
python3 push_to_wecom.py --stock 601899

# 3. 查看推送历史
cat cache/push_signals.json

# 4. 检查企业微信是否收到
```

---

**鹏总，配置完成后，选股信号会自动推送到企业微信！** 📱

**下一步**:
1. 获取企业微信 webhook
2. 修改 push_config.json
3. 测试推送
4. 设置定时任务

需要我帮您测试推送吗？🚀
