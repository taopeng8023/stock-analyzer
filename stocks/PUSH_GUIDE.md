# 📤 工作流推送功能 - 使用指南

**更新时间**: 2026-03-20 15:11  
**版本**: v1.0

---

## 🎯 功能说明

将选股结果自动推送到企业微信，支持：
- ✅ 多因子选股结果推送
- ✅ 主力选股池推送
- ✅ 自定义策略推送
- ✅ 工作流集成推送

---

## 🚀 快速使用

### 方式 1: 独立推送模块 (推荐)

```bash
cd /home/admin/.openclaw/workspace/stocks

# 多因子选股推送
python3 workflow_push.py --strategy multi --top 10

# 主力选股池推送
python3 workflow_push.py --pool --top 100

# 主力策略推送
python3 workflow_push.py --strategy main --top 20

# 自定义 Webhook
python3 workflow_push.py --strategy multi --top 10 --webhook "YOUR_WEBHOOK"
```

### 方式 2: 工作流集成推送

```bash
# 工作流 + 推送
python3 run_workflow.py --strategy all --top 20 --push

# 工作流 + 推送 + 自定义 Webhook
python3 run_workflow.py --strategy all --top 20 --push --webhook "YOUR_WEBHOOK"
```

---

## 📊 推送效果

### 多因子选股推送示例

```
### 📊 多因子选股 Top10

_更新时间：03-20 15:11_
_数据来源：真实市场数据 (严禁估算)_

1. 📈 **光库科技** (sz300620)
   现价：¥163.80 | 涨跌：+9.21%
   成交：61.60 亿

2. 📈 **富临精工** (sz300432)
   现价：¥21.23 | 涨跌：+7.28%
   成交：40.34 亿

3. 📈 **唯科科技** (sz301196)
   现价：¥92.48 | 涨跌：+6.83%
   成交：10.23 亿

... 共 10 只股票

---
_💰 = 真实主力数据 | 📊 = 真实成交额数据_
_⚠️ 严禁使用模拟/估算数据_
```

### 主力选股池推送示例

```
### 🏦 主力选股池 Top100

_选股池数量：100 只_
_真实主力数据：0 只_
_更新时间：03-20 15:11_

⚠️ _无真实主力数据时按成交额排序 (严禁估算)_

1. 📗 **工业富联** (sh601138)
   现价：¥50.87 | 涨跌：+0.81%
   📊64.31 亿

2. 📈 **卓胜微** (sz300782)
   现价：¥92.64 | 涨跌：+16.82%
   📊56.57 亿

3. 📗 **亨通光电** (sh600487)
   现价：¥43.65 | 涨跌：+1.25%
   📊49.56 亿

... 共 100 只股票

---
_💰 = 真实主力数据 | 📊 = 真实成交额数据_
_⚠️ 严禁使用模拟/估算数据_
```

---

## ⚙️ 配置说明

### 企业微信 Webhook

**默认 Webhook**:
```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5
```

**自定义 Webhook**:
```bash
python3 workflow_push.py --strategy multi --webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
```

### 推送参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--strategy` | 选股策略 | multi |
| `--top` | 推送数量 | 10 |
| `--pool` | 主力选股池模式 | false |
| `--webhook` | 企业微信地址 | 默认地址 |
| `--no-cache` | 不使用缓存 | false |

---

## 📁 输出文件

### 推送记录

| 文件 | 说明 |
|------|------|
| `cache/push_multi_YYYYMMDD_HHMM.json` | 多因子推送记录 |
| `cache/push_pool_YYYYMMDD_HHMM.json` | 选股池推送记录 |

### 文件格式

```json
{
  "strategy": "multi",
  "pool_mode": false,
  "push_time": "2026-03-20T15:11:00",
  "count": 10,
  "stocks": [...]
}
```

---

## 🔄 定时推送

### Crontab 配置

```bash
# 每个交易日 9:35 推送选股池
35 9 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 workflow_push.py --pool --top 100

# 每个交易日 10:30 推送多因子选股
30 10 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 workflow_push.py --strategy multi --top 20

# 每个交易日 14:00 推送下午选股
0 14 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 workflow_push.py --strategy multi --top 20
```

### 系统服务

```bash
# 创建 systemd 服务
sudo tee /etc/systemd/system/stock-push.service > /dev/null <<'EOF'
[Unit]
Description=Stock Selection Push Service
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/admin/.openclaw/workspace/stocks/workflow_push.py --pool --top 100
WorkingDirectory=/home/admin/.openclaw/workspace/stocks
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

# 创建定时器
sudo tee /etc/systemd/system/stock-push.timer > /dev/null <<'EOF'
[Unit]
Description=Run Stock Push Every Trading Day

[Timer]
OnCalendar=*-*-* 09:35:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable stock-push.timer
sudo systemctl start stock-push.timer
```

---

## 💡 使用场景

### 场景 1: 早盘选股

```bash
# 9:35 推送主力选股池
python3 workflow_push.py --pool --top 100
```

### 场景 2: 盘中监控

```bash
# 10:30 推送多因子选股
python3 workflow_push.py --strategy multi --top 20
```

### 场景 3: 尾盘总结

```bash
# 14:30 推送最终选股
python3 workflow_push.py --strategy multi --top 20
```

### 场景 4: 工作流集成

```bash
# 完整工作流 + 推送
python3 run_workflow.py --strategy all --push
```

---

## 📊 推送策略对比

| 策略 | 适用场景 | 推荐数量 |
|------|---------|---------|
| `multi` | 综合选股 | 10-20 只 |
| `main` | 主力追踪 | 20-30 只 |
| `main_pool` | 股票池监控 | 50-100 只 |
| `volume` | 活跃度监控 | 20-30 只 |
| `change` | 强势股追踪 | 10-20 只 |

---

## ⚠️ 注意事项

### 1. 数据政策

- ✅ 所有推送数据来自真实市场
- ❌ 严禁使用估算/模拟数据
- 📊 无主力数据时降级为成交额排序

### 2. 推送频率

- 盘中建议 <= 5 次/天
- 避免频繁推送打扰用户
- 可使用交易时间判断

### 3. 消息长度

- 企业微信限制 4096 字符
- 建议推送 Top10-20
- 选股池模式支持更多

### 4. Webhook 安全

- 不要泄露 Webhook 地址
- 定期更换 Key
- 使用企业微信白名单

---

## 🔍 故障排查

### 推送失败

```bash
# 1. 检查网络连接
curl https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY

# 2. 测试推送
python3 workflow_push.py --strategy multi --top 5

# 3. 查看错误日志
python3 workflow_push.py --strategy multi --top 10 2>&1 | tee push.log
```

### 数据为空

```bash
# 1. 检查数据源
python3 stock_selector.py --strategy multi --top 5 --no-cache

# 2. 检查缓存
ls -lh cache/

# 3. 清除缓存重试
rm cache/*.json && python3 workflow_push.py --strategy multi --top 10
```

---

## 📞 帮助

### 查看帮助

```bash
python3 workflow_push.py --help
python3 run_workflow.py --help
```

### 测试推送

```bash
# 测试推送 (5 只)
python3 workflow_push.py --strategy multi --top 5

# 测试选股池
python3 workflow_push.py --pool --top 20
```

### 查看推送记录

```bash
ls -lh cache/push_*.json
cat cache/push_multi_*.json | head -30
```

---

## 🎯 最佳实践

### 推送模板

```bash
# 早盘推送 (9:35)
python3 workflow_push.py --pool --top 100

# 盘中推送 (10:30, 14:00)
python3 workflow_push.py --strategy multi --top 20

# 收盘推送 (15:05)
python3 workflow_push.py --strategy multi --top 20 --no-cache
```

### 推送内容优化

- 显示前 15 只股票详情
- 添加数据来源说明
- 标注真实/估算数据
- 添加风险提示

---

**功能完成!** 🎉

工作流推送模块已就绪，支持企业微信自动推送选股结果。
