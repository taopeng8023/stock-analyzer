# 🤖 自动选股推送系统 - 配置指南

## 功能说明

**每日 14:20 自动执行**:
1. ✅ 获取主力资金流 TOP 100
2. ✅ 获取板块排名 TOP 10
3. ✅ 分析筛选买入信号 TOP 5
4. ✅ 企业微信推送

**防反爬机制**:
- ✅ 随机延迟
- ✅ 自动重试
- ✅ 请求头伪装
- ✅ 分批次获取

---

## 🚀 快速开始

### 1. 测试流程（用 3 月 26 日数据）

```bash
cd /home/admin/.openclaw/workspace/stocks

# 测试模式
python3 auto_daily_push.py --test
```

### 2. 设置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加任务（交易日 14:20）
20 14 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 auto_daily_push.py
```

### 3. 查看执行日志

```bash
# 查看今日日志
cat /home/admin/.openclaw/workspace/stocks/cache/auto_select/auto_select_20260326.log

# 查看推送历史
cat /home/admin/.openclaw/workspace/stocks/cache/auto_select/push_history.json
```

---

## 📊 推送效果

您会在企业微信收到：

```
🎯 今日选股信号 TOP 5

分析时间：2026-03-26 14:20
数据来源：主力资金流 + 综合评分

### 买入信号

1. 紫金矿业 (601899)
- 综合评分：77.4 分
- 现价：¥32.09 (+1.25%)
- 主力：12.50 亿 (8.50%)
- 建议：仓位 20-30%
- 止损：-8%
- 止盈：+25%

2. 华电新能 (600930)
- 综合评分：74.2 分
- 现价：¥6.95 (+4.35%)
- 主力：8.20 亿 (6.20%)
- 建议：仓位 20-30%
- 止损：-8%
- 止盈：+25%

3. 璞泰来 (603659)
- 综合评分：71.5 分
- 现价：¥31.43 (+2.10%)
- 主力：5.80 亿 (5.80%)
- 建议：仓位 20-30%
- 止损：-8%
- 止盈：+25%

4. ...

5. ...

---
### 💡 操作建议
- 分批建仓，首笔 30%
- 严格执行止损
- 持有周期：5-10 天

### ⚠️ 风险提示
股市有风险，投资需谨慎

---
选股系统 v3.0
生成时间：2026-03-26 14:20:00
```

---

## ⚙️ 配置说明

### 推送配置

编辑 `push_config.json`:

```json
{
    "wecom": {
        "enabled": true,
        "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5"
    },
    "push_settings": {
        "daily_report_time": "14:20",
        "min_score_to_push": 70,
        "push_top_n": 5
    }
}
```

### 定时任务配置

```bash
# 编辑 crontab
crontab -e

# 添加以下任务
```

#### 必选任务

```bash
# 每日 14:20 推送选股信号（交易日）
20 14 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 auto_daily_push.py
```

#### 可选任务

```bash
# 早盘推送主力排名（08:30）
30 8 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 push_to_wecom.py --top 10

# 盘后推送板块排名（15:30）
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 push_to_wecom.py --sector

# 清理 7 天前缓存（每天 02:00）
0 2 * * * find /home/admin/.openclaw/workspace/stocks/cache/auto_select -name "*.json" -mtime +7 -delete
```

---

## 🔧 防反爬机制

### 已实现功能

1. **随机延迟**
   - 请求间延迟：0.5-3 秒随机
   - 重试延迟：2-5 秒随机

2. **自动重试**
   - 失败自动重试 3 次
   - 指数退避策略

3. **请求头伪装**
   - User-Agent 伪装
   - Referer 设置
   - Accept 设置

4. **分批次获取**
   - 每页 20 条
   - 避免单次大量请求

### 优化建议

如果仍然被限制：

1. **增加延迟**
   ```python
   # 修改 auto_daily_push.py
   time.sleep(random.uniform(2, 5))  # 增加延迟
   ```

2. **使用代理**
   ```python
   # 添加代理配置
   proxies = {
       'http': 'http://proxy.example.com:8080',
       'https': 'http://proxy.example.com:8080',
   }
   ```

3. **降低频率**
   - 改为每日 1 次
   - 避开高峰期

---

## 📁 文件说明

### 核心文件

| 文件 | 功能 | 位置 |
|------|------|------|
| `auto_daily_push.py` | 自动选股主程序 | stocks/ |
| `push_to_wecom.py` | 企业微信推送 | stocks/ |
| `push_config.json` | 推送配置 | stocks/ |

### 数据文件

| 文件 | 说明 | 位置 |
|------|------|------|
| `data_YYYYMMDD_HHMM.json` | 每日数据 | cache/auto_select/ |
| `push_history.json` | 推送历史 | cache/auto_select/ |
| `auto_select_YYYYMMDD.log` | 执行日志 | cache/auto_select/ |

---

## 📊 数据流程

```
14:20 定时触发
    ↓
获取主力 TOP 100 (带防爬)
    ↓
获取板块 TOP 10 (带防爬)
    ↓
分析每只股票 (快速评分)
    ↓
筛选评分≥70 的股票
    ↓
按评分排序取 TOP 5
    ↓
生成推送消息
    ↓
发送到企业微信
    ↓
保存数据和日志
```

---

## 🧪 测试流程

### 使用 3 月 26 日数据测试

```bash
cd /home/admin/.openclaw/workspace/stocks

# 测试模式
python3 auto_daily_push.py --test
```

### 预期输出

```
============================================================
🚀 开始执行自动选股流程
============================================================
[2026-03-26 14:20:00] 📊 获取主力资金流 TOP 100...
[2026-03-26 14:20:05] 已获取第 1 页，共 20 条
[2026-03-26 14:20:10] 已获取第 2 页，共 40 条
...
[2026-03-26 14:22:00] ✅ 获取主力数据成功，共 100 只股票
[2026-03-26 14:22:00] 🏭 获取行业板块 TOP 10...
[2026-03-26 14:22:05] ✅ 获取板块数据成功，共 10 个板块
[2026-03-26 14:22:05] 🔍 开始分析股票...
[2026-03-26 14:22:10] [1/100] 分析 紫金矿业 (601899)
[2026-03-26 14:22:11] ✅ 紫金矿业 评分 77.4，达到买入标准
...
[2026-03-26 14:25:00] 分析完成，发现 15 个买入信号
[2026-03-26 14:25:00] 📱 准备推送 TOP 5 买入信号...
[2026-03-26 14:25:05] ✅ 推送成功
[2026-03-26 14:25:05] 推送记录已保存
============================================================
✅ 流程执行完成，耗时 305.3 秒
============================================================
```

---

## ⚠️ 常见问题

### Q1: 推送失败？

**检查**:
1. webhook 是否正确
2. 网络是否通畅
3. 企业微信机器人是否启用

**解决**:
```bash
# 测试 webhook
curl -X POST "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5" \
  -H "Content-Type: application/json" \
  -d '{"msgtype":"text","text":{"content":"测试"}}'
```

### Q2: 数据获取失败？

**检查**:
1. 网络连接
2. API 是否正常
3. 是否被反爬

**解决**:
- 增加延迟时间
- 减少请求频率
- 使用代理 IP

### Q3: 定时任务不执行？

**检查**:
```bash
# 查看 crontab
crontab -l

# 查看 cron 服务
systemctl status cron

# 查看日志
tail -f /var/log/syslog | grep cron
```

### Q4: 如何查看推送历史？

```bash
# 查看推送历史
cat /home/admin/.openclaw/workspace/stocks/cache/auto_select/push_history.json

# 查看执行日志
cat /home/admin/.openclaw/workspace/stocks/cache/auto_select/auto_select_20260326.log
```

---

## 📈 优化建议

### 1. 评分系统优化

当前使用快速评分，可以优化为：

```python
# 使用完整分析（更准确但更慢）
from stock_analyzer.stock_analyzer_v2 import EnhancedStockAnalyzer
analyzer = EnhancedStockAnalyzer()
report = analyzer.analyze(code)
score = report['scores']['total']
```

### 2. 股票池优化

可以添加过滤条件：

```python
# 过滤 ST 股票
if 'ST' in name:
    continue

# 过滤股价过高/过低
if price > 200 or price < 3:
    continue

# 过滤市值过小
if market_cap < 5000000000:
    continue
```

### 3. 推送时间优化

根据市场情况调整：

- **早盘前** (08:30): 隔夜消息 + 主力排名
- **午盘后** (14:20): 选股信号 TOP 5
- **收盘后** (15:30): 板块排名 + 总结

---

## ✅ 配置完成检查

```bash
# 1. 检查配置文件
cat /home/admin/.openclaw/workspace/stocks/push_config.json

# 2. 测试推送
python3 /home/admin/.openclaw/workspace/stocks/push_to_wecom.py --top 10

# 3. 测试完整流程
python3 /home/admin/.openclaw/workspace/stocks/auto_daily_push.py --test

# 4. 设置定时任务
crontab -e

# 5. 查看日志
tail -f /home/admin/.openclaw/workspace/stocks/cache/auto_select/auto_select_20260326.log
```

---

**选股系统 v3.0** - 自动推送配置完成

**下一步**: 测试流程 → 设置定时任务 → 每日自动推送
