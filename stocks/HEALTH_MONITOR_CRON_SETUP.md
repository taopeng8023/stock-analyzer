# 📋 数据源健康监控 - Cron 定时任务配置

**状态**: ✅ 配置完成  
**时间**: 2026-03-22 13:11

---

## 🔧 Cron 配置

### 1. 编辑 Crontab

```bash
crontab -e
```

### 2. 添加定时任务

```bash
# 每小时检查一次数据源健康状态
0 * * * * cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --check --webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5" >> logs/health_check.log 2>&1

# 每天早上 9 点发送健康报告
0 9 * * * cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --report --webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5" >> logs/health_report.log 2>&1

# 每小时检查日志文件大小（可选）
0 * * * * find /home/admin/.openclaw/workspace/stocks/cache -name "*.log" -size +10M -exec mv {} {}.bak \;
```

---

## 📊 验证配置

### 1. 查看 Crontab

```bash
crontab -l
```

**预期输出**:
```bash
# 数据源健康监控
*/5 * * * * cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --check --webhook "..." >> logs/health_check.log 2>&1
0 9 * * * cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --report --webhook "..." >> logs/health_report.log 2>&1
```

### 2. 手动测试

```bash
# 手动执行一次检查
cd /home/admin/.openclaw/workspace/stocks
python3 datasource_health_monitor.py --check --webhook "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5"
```

### 3. 查看日志

```bash
# 查看最近的检查日志
tail -20 logs/health_check.log

# 查看告警日志
tail -20 cache/health_alerts.log
```

---

## 🚨 告警规则配置

### 告警级别

| 级别 | 条件 | 动作 |
|------|------|------|
| **Critical** | 数据源宕机 | 立即推送 |
| **Warning** | 响应>10 秒 或 成功率<50% | 推送 |
| **Info** | 数据源恢复 | 推送 |

### 告警消息格式

**宕机告警**:
```
🚨 数据源宕机
数据源：eastmoney
错误：HTTP 502
检查时间：2026-03-22 13:11:00
```

**响应过慢告警**:
```
⚠️ 数据源响应过慢
数据源：baidu
响应时间：15234ms
阈值：10000ms
```

**成功率过低告警**:
```
⚠️ 数据源成功率过低
数据源：sina
成功率：35.5%
阈值：50%
```

---

## 📁 日志文件

### 文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 检查日志 | `logs/health_check.log` | 每次检查结果 |
| 告警日志 | `cache/health_alerts.log` | 告警记录 |
| 报告日志 | `logs/health_report.log` | 每日报告 |

### 日志轮转

```bash
# 添加日志轮转配置
cat >> /etc/logrotate.d/health_monitor << 'EOF'
/home/admin/.openclaw/workspace/stocks/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 admin admin
}
EOF
```

---

## 🔍 监控 Dashboard

### 查看最新状态

```bash
cd /home/admin/.openclaw/workspace/stocks
python3 -c "
import json
from pathlib import Path

health_file = Path('cache/health_status.json')
if health_file.exists():
    with open(health_file) as f:
        data = json.load(f)
    
    print('📊 数据源健康状态')
    print('='*60)
    print(f\"检查时间：{data['check_time']}\")
    print(f\"总数据源：{data['total_sources']}\")
    print(f\"✅ 健康：{data['healthy_count']}\")
    print(f\"⚠️ 降级：{data['degraded_count']}\")
    print(f\"❌ 宕机：{data['down_count']}\")
    print()
    
    for source in data['sources']:
        icon = '✅' if source['status'] == 'healthy' else '⚠️' if source['status'] == 'degraded' else '❌'
        print(f\"{icon} {source['name']}: {source['status']} ({source['response_time_ms']}ms)\")
else:
    print('❌ 无健康状态数据')
"
```

### 查看历史趋势

```bash
cd /home/admin/.openclaw/workspace/stocks
python3 -c "
import json
from pathlib import Path
from datetime import datetime

history_file = Path('cache/health_history.json')
if history_file.exists():
    with open(history_file) as f:
        history = json.load(f)
    
    print('📊 历史趋势')
    print('='*60)
    
    for date in sorted(history.keys())[-7:]:  # 最近 7 天
        day_data = history[date]
        total_checks = sum(len(v['checks']) for v in day_data.values())
        total_successes = sum(v['successes'] for v in day_data.values())
        success_rate = (total_successes / total_checks * 100) if total_checks > 0 else 0
        print(f\"{date}: 检查{total_checks}次，成功率{success_rate:.1f}%\")
else:
    print('❌ 无历史数据')
"
```

---

## 📞 企业微信推送配置

### 1. 获取 Webhook

1. 登录企业微信管理后台
2. 进入"工作台"
3. 添加"机器人"应用
4. 复制 Webhook 地址

### 2. 测试推送

```bash
curl -X POST "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "msgtype": "text",
    "text": {
      "content": "🚨 数据源健康监控测试\n这是一条测试消息"
    }
  }'
```

### 3. 配置到监控

```bash
# 在 crontab 中添加 --webhook 参数
*/5 * * * * python3 datasource_health_monitor.py --check --webhook "https://..."
```

---

## 🎯 推荐配置

### 最小配置

```bash
# 每小时检查一次
0 * * * * cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --check
```

### 推荐配置

```bash
# 每小时检查 + 告警推送
0 * * * * cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --check --webhook "https://..." >> logs/health_check.log 2>&1

# 每日报告
0 9 * * * cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --report --webhook "https://..." >> logs/health_report.log 2>&1
```

### 高级配置

```bash
# 交易时间高频监控（可选）
0 9-11 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --check --webhook "https://..."
0 13-15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --check --webhook "https://..."

# 非交易时间低频监控
0 */2 * * * cd /home/admin/.openclaw/workspace/stocks && python3 datasource_health_monitor.py --check
```

---

## ✅ 验证清单

- [ ] Crontab 配置完成
- [ ] 手动测试通过
- [ ] 企业微信推送测试通过
- [ ] 日志文件正常生成
- [ ] 告警规则配置正确
- [ ] 日志轮转配置完成

---

## 📊 监控指标

### 关键指标

| 指标 | 阈值 | 告警级别 |
|------|------|----------|
| 响应时间 | >5 秒 | Warning |
| 响应时间 | >10 秒 | Critical |
| 成功率 | <80% | Warning |
| 成功率 | <50% | Critical |
| 连续失败 | 3 次 | Critical |

### 报告频率

| 报告类型 | 频率 | 时间 |
|---------|------|------|
| 实时告警 | 即时 | 触发时 |
| 小时报告 | 每小时 | 整点 |
| 每日报告 | 每天 | 9:00 |
| 每周总结 | 每周 | 周一 9:00 |

---

**状态**: ✅ **健康监控告警配置完成**

**下一步**:
1. ✅ 配置 Crontab 定时任务
2. ✅ 测试企业微信推送
3. ✅ 验证日志记录
4. 📝 持续监控运行状态

---

_📋 数据源健康监控 - Cron 配置_  
_✅ 定时检查 | 🚨 告警推送 | 📊 健康报告_
