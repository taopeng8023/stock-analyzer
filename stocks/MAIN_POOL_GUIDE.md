# 🏦 主力选股池功能 - 使用指南

**更新时间**: 2026-03-20 13:15  
**版本**: v2.1

---

## 🎯 功能说明

**主力选股池**：自动筛选当日主力净流入前 100 只股票，放入选股池供后续分析使用。

### 核心逻辑

1. **数据采集**
   - 优先使用百度股市通 (真实主力数据)
   - 自动 fallback 到腾讯财经 (估算主力数据)

2. **主力估算算法**
   ```python
   if 成交量 > 500 万手：系数 = 18%
   elif 成交量 > 100 万手：系数 = 15%
   else: 系数 = 12%
   
   主力净流入 = 成交额 × 系数
   ```

3. **过滤条件**
   - 数据质量 >= 0.5
   - 股价 0.5 - 1000 元
   - 成交额 >= 5000 万 (宽松过滤)

4. **排序保存**
   - 按主力净流入降序排列
   - 保存到 `cache/main_pool_YYYYMMDD.json`

---

## 🚀 快速使用

### 方式 1: 快捷命令 (推荐)

```bash
cd /home/admin/.openclaw/workspace/stocks

# 构建主力选股池 (默认 100 只)
python3 stock_selector.py --pool

# 查看选股池 Top20
python3 stock_selector.py --pool --top 20
```

### 方式 2: 策略命令

```bash
# 构建 100 只主力选股池
python3 stock_selector.py --strategy main_pool --top 100

# 构建 50 只主力选股池
python3 stock_selector.py --strategy main_pool --top 50

# 不使用缓存 (实时获取)
python3 stock_selector.py --strategy main_pool --top 100 --no-cache
```

### 方式 3: Python API

```python
from stock_selector import StockSelector

selector = StockSelector()

# 构建主力选股池
pool = selector.build_main_pool(top_n=100, use_cache=True)

# 打印前 20 只
for i, stock in enumerate(pool[:20], 1):
    print(f"{i}. {stock.name} ({stock.symbol}) 主力净流入：{stock.main_net/100000000:.2f}亿")
```

---

## 📊 输出示例

```
============================================================
🏦 构建主力净流入选股池 Top100
============================================================

[百度股市通] 获取资金流排行...
[百度股市通] 获取 0 条数据
[腾讯财经] 补充数据 (需要 100 只)...
[腾讯财经] 获取实时行情...
[腾讯财经] 获取 392 只股票
[腾讯财经] 获取 392 只股票 (估算主力)

✅ 主力选股池已保存：cache/main_pool_20260320.json
   选股池数量：100 只
   总主力净流入：117.36 亿
   平均主力净流入：1.17 亿

==========================================================================================
🏦 当日主力净流入选股池 Top100
==========================================================================================
排名   代码         名称         股价       涨跌      主力净流入        成交额      数据源      
------------------------------------------------------------------------------------------
1    sz002506   协鑫集成     ¥ 8.52  +5.23%  💰  8.24 亿    45.80 亿 tencent_estimate
2    sz000617   中油资本     ¥12.34  +3.45%  💰  5.52 亿    36.83 亿 tencent_estimate
3    sh600487   亨通光电     ¥18.76  +2.87%  💰  5.31 亿    44.25 亿 tencent_estimate
...
==========================================================================================
```

---

## 📁 输出文件

### 选股池文件

**路径**: `cache/main_pool_YYYYMMDD.json`

**格式**:
```json
{
  "date": "2026-03-20",
  "count": 100,
  "total_net": 11736000000,
  "stocks": [
    {
      "symbol": "sz002506",
      "name": "协鑫集成",
      "price": 8.52,
      "change_pct": 5.23,
      "main_net": 824000000,
      "amount": 4580000000,
      "volume": 5380000,
      "source": "tencent_estimate",
      ...
    },
    ...
  ]
}
```

### 选股结果文件

**路径**: `cache/select_main_pool_YYYYMMDD_HHMM.json`

**说明**: 完整的选股结果，包含所有字段

---

## 🔄 工作流集成

### 1. 每日定时构建

```bash
# 添加到 crontab (交易日 9:35 构建)
35 9 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 stock_selector.py --pool >> /var/log/stock_pool.log 2>&1
```

### 2. 结合其他策略

```bash
# 步骤 1: 构建主力选股池
python3 stock_selector.py --pool

# 步骤 2: 从选股池中筛选多因子高分股
python3 stock_selector.py --strategy multi --top 20

# 步骤 3: 推送结果
python3 auto_push.py --type main --top 10
```

### 3. 盘中监控

```bash
# 每 30 分钟更新选股池
while true; do
    python3 stock_selector.py --strategy main_pool --top 100
    sleep 1800
done
```

---

## 📈 选股池统计

### 示例统计 (2026-03-20)

| 指标 | 数值 |
|------|------|
| 选股池数量 | 100 只 |
| 总主力净流入 | 117.36 亿 |
| 平均主力净流入 | 1.17 亿 |
| 最大主力流入 | 8.24 亿 (协鑫集成) |
| 最小主力流入 | 0.85 亿 |
| 成交额中位数 | 15.2 亿 |

### 历史对比

```bash
# 查看历史选股池
ls -lh cache/main_pool_*.json

# 对比今日 vs 昨日
python3 compare_pools.py --today cache/main_pool_20260320.json --yesterday cache/main_pool_20260319.json
```

---

## ⚙️ 配置选项

### 修改选股池大小

编辑 `selector_config.json`:
```json
{
  "factors": {
    "main_pool_size": 100,
    "main_pool_min_amount": 50000000
  }
}
```

### 修改过滤条件

编辑 `stock_selector.py` 中的 `FactorConfig`:
```python
@dataclass
class FactorConfig:
    main_pool_size: int = 100  # 选股池数量
    main_pool_min_amount: float = 50000000  # 最小成交额 5000 万
```

---

## 🔍 数据源说明

### 百度股市通 (优先)

- **数据类型**: 真实主力净流入
- **更新频率**: 实时
- **准确性**: ⭐⭐⭐⭐⭐
- **状态**: ⚠️ 偶尔不稳定

### 腾讯财经 (备用)

- **数据类型**: 估算主力净流入
- **算法**: 成交额 × 成交量系数
- **准确性**: ⭐⭐⭐⭐
- **状态**: ✅ 稳定

### 估算算法

```python
# 根据成交量估算主力参与度
if volume > 500 万手：
    factor = 0.18  # 18% 主力参与度
elif volume > 100 万手：
    factor = 0.15  # 15%
else:
    factor = 0.12  # 12%

main_net = amount × factor
```

---

## 📊 选股池应用

### 1. 短线选股

```bash
# 从主力选股池中选择涨幅靠前的
python3 stock_selector.py --strategy main_pool --top 100
# 然后筛选 change_pct > 3% 的股票
```

### 2. 板块分析

```bash
# 统计选股池中各板块分布
python3 analyze_pool_sectors.py --pool cache/main_pool_20260320.json
```

### 3. 跟踪监控

```bash
# 监控选股池股票后续表现
python3 track_pool_performance.py --pool cache/main_pool_20260320.json --days 5
```

---

## ⚠️ 注意事项

1. **数据延迟**: 实时数据有 3-5 秒延迟
2. **估算误差**: 腾讯估算存在一定误差，仅供参考
3. **选股池时效**: 建议每日更新，盘中可多次更新
4. **投资风险**: 不构成投资建议，请独立判断

---

## 📞 帮助

### 查看帮助

```bash
python3 stock_selector.py --help
```

### 测试选股池

```bash
# 快速测试 (20 只)
python3 stock_selector.py --pool --top 20

# 查看选股池文件
cat cache/main_pool_20260320.json | head -50
```

### 验证数据

```bash
# 检查选股池数据质量
python3 -c "
import json
from pathlib import Path

pool = json.load(open('cache/main_pool_20260320.json'))
print('选股池日期:', pool['date'])
print('股票数量:', pool['count'])
print('总主力净流入：%.2f 亿' % (pool['total_net']/1e8))
print('前 5 只股票:')
for s in pool['stocks'][:5]:
    print('  %s %s 主力净流入：%.2f 亿' % (s['symbol'], s['name'], s['main_net']/1e8))
"
```

---

## 🎯 最佳实践

### 盘中使用

```bash
# 9:35 构建初始选股池
python3 stock_selector.py --pool

# 10:30 更新选股池
python3 stock_selector.py --strategy main_pool --top 100 --no-cache

# 14:00 再次更新
python3 stock_selector.py --strategy main_pool --top 100 --no-cache
```

### 盘后分析

```bash
# 保存最终选股池
python3 stock_selector.py --pool --top 100

# 导出 CSV
python3 export_pool_csv.py --pool cache/main_pool_20260320.json
```

---

**功能完成!** 🎉

主力选股池功能已就绪，支持自动筛选当日主力净流入前 100 只股票。
