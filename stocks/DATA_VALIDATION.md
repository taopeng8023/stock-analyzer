# 📊 数据获取验证机制

## 核心原则

**⚠️ 数据优先原则**: 所有操作的前提是必须获取到真实数据，数据获取失败不做推送！

---

## 数据验证流程

### 1. 主力数据获取（必需）

**要求**:
- ✅ 获取数量 ≥ 50 条
- ✅ 有效数据 ≥ 30 条（主力净流入非空）
- ✅ 数据格式正确

**验证**:
```python
# 数量验证
if not main_force or len(main_force) < 50:
    log("❌ 主力数据获取失败，终止流程")
    return

# 质量验证
valid_count = sum(1 for s in main_force if s['f4001'] != 0)
if valid_count < 30:
    log("❌ 数据质量不达标，终止流程")
    return
```

**失败处理**:
- ❌ 取消推送
- 🚨 发送失败告警
- 📝 记录失败日志

---

### 2. 板块数据获取（重要）

**要求**:
- ✅ 获取数量 ≥ 5 条
- ✅ 数据格式正确

**验证**:
```python
if not sectors or len(sectors) < 5:
    log("⚠️ 板块数据不足，继续但不包含板块分析")
    sectors = []
```

**失败处理**:
- ⚠️ 继续执行
- ⚠️ 不包含板块分析
- 📝 记录警告日志

---

### 3. 买入信号验证（必需）

**要求**:
- ✅ 至少 1 只股票评分 ≥ 70
- ✅ 数据真实有效

**验证**:
```python
if not buy_signals or len(buy_signals) < 1:
    log("⚠️ 无符合条件的买入信号，不做推送")
    return

# 验证最高评分
if buy_signals[0]['score'] < 70:
    log("⚠️ 最高评分 < 70，不做推送")
    return
```

**失败处理**:
- ❌ 取消推送
- 📝 记录日志

---

## 防反爬机制

### 已实现功能

1. **随机延迟**
   - 请求间延迟：0.5-3 秒
   - 重试延迟：2-5 秒
   - 分页延迟：1-3 秒

2. **自动重试**
   - 失败自动重试 3 次
   - 指数退避策略
   - 记录重试日志

3. **请求头伪装**
   ```python
   headers = {
       'User-Agent': 'Mozilla/5.0...',
       'Accept': 'application/json...',
       'Referer': 'http://data.eastmoney.com/',
   }
   ```

4. **分批次获取**
   - 每页 20 条
   - 最多 5 页
   - 避免单次大量请求

---

## 数据质量检查

### 检查项

| 检查项 | 标准 | 处理 |
|--------|------|------|
| 数据完整性 | 字段齐全 | 失败则丢弃 |
| 数据有效性 | 主力净流入非空 | <30 条则终止 |
| 数据时效性 | 当日数据 | 过期则警告 |
| 数据一致性 | 代码 + 名称匹配 | 不匹配则丢弃 |

### 验证代码

```python
def validate_stock_data(self, stock: dict) -> bool:
    """验证单条股票数据"""
    # 必需字段
    required_fields = ['f12', 'f14', 'f2', 'f4001']
    for field in required_fields:
        if field not in stock:
            return False
    
    # 代码格式
    code = stock.get('f12', '')
    if not code or len(code) != 6:
        return False
    
    # 价格有效性
    price = stock.get('f2', 0)
    if not price or price <= 0:
        return False
    
    return True
```

---

## 失败告警机制

### 告警类型

**1. 数据获取失败**
```
🚨 数据获取失败告警

时间：2026-03-27 14:20:00
失败原因：主力数据获取失败

已执行操作:
- ❌ 选股推送已取消
- ⚠️ 请检查网络或 API 状态

建议:
1. 检查网络连接
2. 查看 API 是否正常
3. 稍后重试
```

**2. 数据质量不达标**
```
🚨 数据质量告警

时间：2026-03-27 14:20:00
失败原因：主力数据质量不达标
有效数据：15 条（要求≥30 条）

已执行操作:
- ❌ 选股推送已取消
```

**3. 无符合条件股票**
```
⚠️ 无买入信号

时间：2026-03-27 14:20:00
最高评分：65.3 分（要求≥70 分）

已执行操作:
- ❌ 选股推送已取消
```

---

## 日志记录

### 日志文件

**位置**: `/home/admin/.openclaw/workspace/stocks/cache/auto_select/auto_select_YYYYMMDD.log`

**格式**:
```
[2026-03-27 14:20:00] 📊 获取主力资金流 TOP 100...
[2026-03-27 14:20:05] 已获取第 1 页，共 20 条
[2026-03-27 14:20:10] 已获取第 2 页，共 40 条
[2026-03-27 14:20:15] 已获取第 3 页，共 60 条
[2026-03-27 14:20:20] ✅ 获取主力数据成功，共 100 只股票
[2026-03-27 14:20:20] 🔍 开始分析股票...
[2026-03-27 14:20:25] [1/100] 分析 紫金矿业 (601899)
[2026-03-27 14:20:26] ✅ 紫金矿业 评分 77.4，达到买入标准
...
[2026-03-27 14:25:00] ✅ 推送成功
```

### 查看日志

```bash
# 查看今日日志
cat /home/admin/.openclaw/workspace/stocks/cache/auto_select/auto_select_20260327.log

# 实时查看
tail -f /home/admin/.openclaw/workspace/stocks/cache/auto_select/auto_select_20260327.log

# 查看失败记录
grep "❌" /home/admin/.openclaw/workspace/stocks/cache/auto_select/auto_select_20260327.log
```

---

## 数据保存

### 保存内容

**文件**: `data_YYYYMMDD_HHMM.json`

**结构**:
```json
{
  "date": "2026-03-27",
  "time": "14:20:00",
  "main_force": [...],  // 主力 TOP 100
  "sectors": [...],     // 板块 TOP 10
  "signals": [...],     // 买入信号 TOP 5
  "status": "success"   // 或 "failed"
}
```

### 查看数据

```bash
# 查看最新数据
ls -lt /home/admin/.openclaw/workspace/stocks/cache/auto_select/data_*.json | head -1

# 查看数据内容
cat /home/admin/.openclaw/workspace/stocks/cache/auto_select/data_20260327_1420.json | jq '.status'
```

---

## 重试机制

### 重试策略

**最大重试次数**: 3 次

**重试延迟**:
- 第 1 次重试：延迟 2-3 秒
- 第 2 次重试：延迟 3-5 秒
- 第 3 次重试：延迟 5-8 秒

**代码实现**:
```python
for i in range(max_retries):
    try:
        if i > 0:
            delay = random.uniform(2 + i, 5 + i)
            log(f"重试第{i+1}次，延迟{delay:.1f}秒")
            time.sleep(delay)
        
        result = func(*args, **kwargs)
        time.sleep(random.uniform(0.5, 1.5))
        return result
    
    except Exception as e:
        log(f"请求失败：{e}")
        if i >= max_retries - 1:
            log("达到最大重试次数")
            return None
```

---

## 监控与告警

### 监控指标

| 指标 | 阈值 | 告警 |
|------|------|------|
| 数据获取成功率 | <90% | ⚠️ 警告 |
| 数据获取失败 | 连续 3 次 | 🚨 严重 |
| 推送失败 | 1 次 | ⚠️ 警告 |
| 无买入信号 | 连续 5 天 | ⚠️ 关注 |

### 告警方式

1. **企业微信推送**
   - 数据获取失败
   - 推送失败

2. **日志记录**
   - 所有操作
   - 详细错误信息

3. **邮件告警**（可选）
   - 连续失败
   - 严重错误

---

## 故障排查

### 常见问题

**Q1: 数据获取失败？**

```bash
# 1. 检查网络
curl -I http://data.eastmoney.com/

# 2. 测试 API
python3 -c "from stocks.eastmoney_money_flow import EastmoneyMoneyFlow; print(EastmoneyMoneyFlow().get_main_force_rank(page=1, page_size=20))"

# 3. 查看日志
tail -100 /home/admin/.openclaw/workspace/stocks/cache/auto_select/auto_select_20260327.log
```

**Q2: 数据质量不达标？**

```bash
# 检查数据
cat /home/admin/.openclaw/workspace/stocks/cache/auto_select/data_20260327_1420.json | jq '.main_force | length'

# 验证有效性
cat /home/admin/.openclaw/workspace/stocks/cache/auto_select/data_20260327_1420.json | jq '.main_force[] | select(.f4001 != 0) | .f12'
```

**Q3: 推送失败？**

```bash
# 测试 webhook
curl -X POST "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5" \
  -H "Content-Type: application/json" \
  -d '{"msgtype":"text","text":{"content":"测试"}}'
```

---

## 最佳实践

### 1. 数据获取时间

**推荐时间**:
- 早盘前：08:00-09:00（数据较新）
- 午盘后：14:20-14:30（主力流向明确）
- 收盘后：15:30-16:00（全天数据）

**避免时间**:
- 开盘时：09:30-10:00（数据波动大）
- 午休时：11:30-13:00（数据更新慢）

### 2. 数据备份

```bash
# 每日备份
cp /home/admin/.openclaw/workspace/stocks/cache/auto_select/data_*.json /backup/

# 每周清理 7 天前数据
find /home/admin/.openclaw/workspace/stocks/cache/auto_select -name "*.json" -mtime +7 -delete
```

### 3. 性能优化

- 使用缓存（减少 API 调用）
- 并发获取（提高速度）
- 数据压缩（节省空间）

---

**选股系统 v3.0** - 数据验证机制完善

**核心原则**: 数据获取失败，坚决不推送！
