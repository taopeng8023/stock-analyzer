# A 股历史行情自动轮询配置指南

**创建时间**: 2026-03-27  
**版本**: v1.0

---

## 📋 功能说明

自动轮询脚本 (`auto_scan_stocks.py`) 可以：

1. **收盘后自动获取**全 A 股历史行情
2. **批量获取**并缓存到本地
3. **增量更新** (只获取新数据)
4. **支持定时任务** (cron) 执行

---

## 🚀 使用方法

### 1. 手动执行

```bash
cd /home/admin/.openclaw/workspace/stocks

# 全量扫描 (使用缓存)
python3.11 auto_scan_stocks.py

# 强制更新 (忽略缓存)
python3.11 auto_scan_stocks.py --force

# 测试模式 (只扫描前 50 只)
python3.11 auto_scan_stocks.py --max 50
```

### 2. 设置定时任务 (cron)

**编辑 crontab**:
```bash
crontab -e
```

**添加以下行** (每个交易日 15:30 执行):
```bash
# A 股历史行情自动轮询 (周一至周五 15:30)
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3.11 auto_scan_stocks.py >> logs/auto_scan.log 2>&1
```

**其他时间选项**:
```bash
# 每天 16:00 执行
0 16 * * * cd /home/admin/.openclaw/workspace/stocks && python3.11 auto_scan_stocks.py >> logs/auto_scan.log 2>&1

# 每个交易日 15:15 执行 (收盘后 15 分钟)
15 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3.11 auto_scan_stocks.py >> logs/auto_scan.log 2>&1

# 每小时执行一次 (用于测试)
0 * * * * cd /home/admin/.openclaw/workspace/stocks && python3.11 auto_scan_stocks.py --max 100 >> logs/auto_scan.log 2>&1
```

### 3. 查看执行日志

```bash
# 查看最新日志
tail -f logs/auto_scan.log

# 查看历史统计
cat logs/scan_stats.json
```

---

## 📁 文件结构

```
stocks/
├── auto_scan_stocks.py          # 自动轮询脚本
├── cache/
│   └── history/
│       ├── 202603/              # 按月分组
│       │   ├── 600000.json      # 浦发银行
│       │   ├── 600001.json      # 宝钢股份
│       │   └── ...
├── logs/
│   ├── auto_scan.log            # 执行日志
│   └── scan_stats.json          # 统计信息
```

---

## ⚙️ 配置选项

### 限频配置

在 `auto_scan_stocks.py` 中修改：

```python
# 每批获取 50 只股票
self.batch_size = 50

# 每批间隔 5 秒
self.batch_delay = 5

# 每只股票间隔 0.1 秒
self.stock_delay = 0.1
```

**建议配置**:
| 配置 | 保守 | 标准 | 激进 |
|------|------|------|------|
| batch_size | 20 | 50 | 100 |
| batch_delay | 10 秒 | 5 秒 | 2 秒 |
| stock_delay | 0.2 秒 | 0.1 秒 | 0.05 秒 |

### 缓存配置

```python
# 缓存有效期 (小时)
max_age_hours = 24  # 默认 24 小时
```

---

## 📊 数据源

### 优先级

1. **AKShare 东财接口** (主要)
   - 数据最全
   - 支持复权
   - 限流较严

2. **新浪财经接口** (备用)
   - 稳定不限流
   - 数据格式简单
   - 无复权数据

### 自动 fallback

```python
# 执行逻辑:
# 1. 先尝试 AKShare 东财
# 2. 失败则尝试新浪
# 3. 都失败则标记为失败
```

---

## 📈 统计信息

### 查看扫描统计

```bash
cat logs/scan_stats.json | python3.11 -m json.tool
```

### 统计字段

```json
{
  "total": 5000,           // 总股票数
  "success": 4500,         // 成功数
  "failed": 500,           // 失败数
  "start_time": "2026-03-27T15:30:00",
  "end_time": "2026-03-27T16:00:00",
  "duration": 1800         // 耗时 (秒)
}
```

---

## ⚠️ 注意事项

### 1. 限流问题

- 东财接口限流较严
- 建议 batch_size 不超过 50
- batch_delay 不少于 5 秒

### 2. 磁盘空间

- 每只股票约 50-100KB
- 5000 只股票约 250-500MB/月
- 建议定期清理旧数据

### 3. 网络问题

- 需要稳定的网络连接
- 建议在服务器执行
- 失败股票会自动跳过

### 4. 执行时间

- 全量扫描约 30-60 分钟
- 建议在收盘后执行
- 避免交易时间执行

---

## 🔧 故障排除

### 问题 1: 大量股票获取失败

**原因**: 接口限流

**解决**:
```python
# 增加延迟
self.batch_delay = 10  # 增加到 10 秒
self.stock_delay = 0.2  # 增加到 0.2 秒
```

### 问题 2: 内存不足

**原因**: 一次性加载太多数据

**解决**:
```python
# 减少批量大小
self.batch_size = 20  # 减少到 20 只
```

### 问题 3: cron 不执行

**检查**:
```bash
# 查看 cron 状态
systemctl status cron

# 查看 cron 日志
grep CRON /var/log/syslog

# 测试 cron 执行
crontab -l
```

---

## 📋 最佳实践

### 1. 首次执行

```bash
# 测试模式 (前 50 只)
python3.11 auto_scan_stocks.py --max 50

# 确认正常后全量执行
python3.11 auto_scan_stocks.py
```

### 2. 日常执行

```bash
# 设置 cron 自动执行
crontab -e
# 添加：30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3.11 auto_scan_stocks.py >> logs/auto_scan.log 2>&1
```

### 3. 定期检查

```bash
# 每周查看统计
cat logs/scan_stats.json | python3.11 -m json.tool | tail -50

# 清理旧数据 (保留最近 3 个月)
find cache/history -type d -mtime +90 -exec rm -rf {} \;
```

---

## 📞 相关文档

| 文档 | 说明 |
|------|------|
| `auto_scan_stocks.py` | 轮询脚本 |
| `AKSHARE_INTEGRATION_STATUS.md` | AKShare 接口状态 |
| `stock_selector_v2.py` | 选股系统 |

---

**最后更新**: 2026-03-27  
**状态**: ✅ 已完成
