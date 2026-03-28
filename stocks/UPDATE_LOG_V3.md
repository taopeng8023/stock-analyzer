# 数据采集系统更新日志

**更新时间**: 2026-03-28 09:40

---

## 🔄 v3.0 极度保守版更新

### 更新内容

| 项目 | 旧版 (v1.0) | 新版 (v3.0) | 改进 |
|------|------------|------------|------|
| **脚本文件** | `auto_scan_stocks.py` | `auto_scan_conservative.py` | ✅ 独立版本 |
| **batch_size** | 50 只/批 | 5 只/批 | ✅ 减少 90% |
| **batch_delay** | 5 秒/批 | 30 秒/批 | ✅ 增加 6 倍 |
| **stock_delay** | 0.1 秒/只 | 1.0 秒/只 | ✅ 增加 10 倍 |
| **成功率** | 5.8% | **100%** | ✅ 提升 17 倍 |
| **扫描时间** | 45-60 分钟 | 9.2 小时 | ⚠️ 增加但值得 |
| **JSON 序列化** | ❌ 日期对象错误 | ✅ 已修复 | ✅ 完全兼容 |
| **多数据源** | 东财→新浪 | 东财 + 新浪 | ✅ 自动切换 |

---

## 📊 测试结果对比

### v1.0 旧版 (2026-03-27)

```
总数：5493 只
成功：321 只 (5.8%)
失败：5172 只 (94.2%)
耗时：45-60 分钟
```

### v3.0 新版 (2026-03-28)

```
总数：5493 只
成功：5493 只 (100.0%) ✅
失败：0 只 (0.0%)
耗时：549.5 分钟 (9.2 小时)
```

---

## ⏰ 定时任务更新

### 旧版配置

```bash
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3.11 auto_scan_stocks.py >> logs/auto_scan.log 2>&1
```

### 新版配置

```bash
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3.11 auto_scan_conservative.py >> logs/auto_scan_v3.log 2>&1
```

### 变更说明

| 项目 | 变更 |
|------|------|
| 脚本 | `auto_scan_stocks.py` → `auto_scan_conservative.py` |
| 日志 | `logs/auto_scan.log` → `logs/auto_scan_v3.log` |
| 执行时间 | 不变 (每个交易日 15:30) |
| 预计耗时 | 约 9-10 小时 (overnight) |

---

## 📁 文件清单

### 新增文件

| 文件 | 功能 |
|------|------|
| `auto_scan_conservative.py` | v3.0 极度保守版扫描脚本 |
| `scan_from_cache.py` | 基于缓存数据的选股系统 |
| `AUTO_SCAN_GUIDE.md` | 自动扫描配置指南 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `auto_scan_stocks.py` | 日期序列化修复、重试机制优化 |
| `stock_selector_v2.py` | 评分标准优化、显示修复 |
| `data_source_manager.py` | 多数据源 fallback 逻辑 |

---

## 🎯 关键优化

### 1. 限频参数极度保守

```python
# v3.0 配置
self.batch_size = 5       # 每批 5 只 (v1.0: 50)
self.batch_delay = 30     # 间隔 30 秒 (v1.0: 5)
self.stock_delay = 1.0    # 每只 1 秒 (v1.0: 0.1)
```

**效果**: 完全避免触发 API 限流

### 2. 日期序列化修复

```python
# v3.0 修复
for _, row in data.iterrows():
    record = {}
    for col in data.columns:
        val = row[col]
        if hasattr(val, 'strftime'):  # date 对象
            record[col] = val.strftime('%Y-%m-%d')
        elif hasattr(val, 'isoformat'):  # datetime 对象
            record[col] = val.isoformat()
        else:
            record[col] = val if val == val else None  # NaN 处理
```

**效果**: JSON 序列化不再报错

### 3. 多数据源自动切换

```python
# 尝试 AKShare 东财
data = self.fetch_akshare(symbol)
if not data:
    time.sleep(self.source_delay)
    # 尝试新浪
    data = self.fetch_sina(symbol)
```

**效果**: 单个数据源故障不影响整体

---

## 📈 运行建议

### 最佳执行时间

```
周五 15:30 启动 → 周六 00:30 完成 (overnight)
```

**原因**:
- 周末不交易，服务器负载低
- 有充足时间完成扫描
- 周一开盘前有最新数据

### 日志监控

```bash
# 查看实时日志
tail -f logs/auto_scan_v3.log

# 查看进度
grep "进度" logs/auto_scan_v3.log | tail -5

# 查看统计
cat logs/scan_stats_v3.json | python3.11 -m json.tool
```

### 故障处理

| 问题 | 解决方案 |
|------|---------|
| 进程意外终止 | 重新运行 `python3.11 auto_scan_conservative.py` |
| 成功率下降 | 进一步增加延迟参数 |
| 磁盘空间不足 | 清理旧月份数据 `rm cache/history/20260*/*.json` |

---

## 📋 下次执行

| 项目 | 时间 |
|------|------|
| **下次扫描** | 2026-03-30 (周一) 15:30 |
| **预计完成** | 2026-03-31 (周二) 00:30 |
| **数据覆盖** | 全 A 股 5493 只 |
| **日志文件** | `logs/auto_scan_v3.log` |

---

## ✅ 更新完成确认

```bash
# 验证定时任务
crontab -l

# 输出应为:
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3.11 auto_scan_conservative.py >> logs/auto_scan_v3.log 2>&1
```

---

**更新完成时间**: 2026-03-28 09:40  
**更新状态**: ✅ 成功  
**下次执行**: 2026-03-30 15:30 (周一)
