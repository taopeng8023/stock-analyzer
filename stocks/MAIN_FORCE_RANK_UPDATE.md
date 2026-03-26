# 📊 主力排名功能 - 更新报告

**更新时间**: 2026-03-20 18:14  
**版本**: v3.2

---

## 🎯 修改内容

将"主流排名"修改为"**主力排名**"，核心功能变更：

| 项目 | 修改前 | 修改后 |
|------|--------|--------|
| 排名类型 | 成交额排名 | 主力净流入排名 |
| 数据源 | 腾讯财经成交额 | 百度股市通主力净流入 |
| 字段名 | `is_popular` | `is_main_force_top` |
| 字段名 | `mainstream_rank` | `main_force_rank` |
| 字段名 | `mainstream_score` | `main_force_score` |
| 推送显示 | 热门股 | 主力排名 TopX |

---

## 📁 修改文件

### 1. data_sources.py

**MainstreamRank 类** → 核心功能改为获取主力净流入排名

```python
class MainstreamRank:
    def get_main_force_rank(top_n=100) -> List[Dict]
    # 优先使用百度股市通真实主力数据
    # 备用方案：腾讯成交额排名
```

**返回数据**:
```python
{
    'rank': 1,
    'symbol': 'sh600000',
    'name': '浦发银行',
    'main_net': 500000000,  # 主力净流入 (元)
    'main_force_rank': 1,   # 主力排名
    'main_force_score': 99, # 主力分数
    'source': 'baidu_main_force'
}
```

---

### 2. run_workflow.py

**增强方法**:
```python
_enhance_with_mainstream_rank(stocks)
# 添加主力排名信息
# 添加主力净流入数据
```

**字段变更**:
```python
# 修改前
stock['is_popular'] = rank <= 50
stock['mainstream_rank'] = rank

# 修改后
stock['is_main_force_top'] = rank <= 50
stock['main_force_rank'] = rank
stock['main_net'] = main_net_amount
```

**评分调整**:
```python
# 主力前 50 加分更高
if is_main_force_top:
    score += 0.3

# 主力净流入加分
if main_net > 1 亿:
    score += 0.2
elif main_net > 5000 万:
    score += 0.1
```

**理由生成**:
```python
if is_main_force_top:
    reasons.append(f'主力排名 Top{rank}')

if main_net > 1 亿:
    reasons.append(f'主力净流入{main_net/1e8:.2f}亿')
```

---

### 3. workflow_push.py

**推送格式更新**:
```
💰 主力排名：Top15
```

---

## 📊 决策增强逻辑

### 评分规则

| 条件 | 加分 |
|------|------|
| 主力排名前 50 | +0.3 |
| 主力净流入 >1 亿 | +0.2 |
| 主力净流入 >5000 万 | +0.1 |
| 资金流 5 日连续 | +0.3 |
| 资金流 3-4 日连续 | +0.2 |

### 评级升级

```python
if 主力前 50 and 资金流连续性 >= 70:
    推荐 → 强烈推荐 (置信度 +10%)
    谨慎推荐 → 推荐 (置信度 +10%)
```

---

## 🚀 使用示例

### 工作流输出

```
🎯 生成最终决策...

[增强 1/2] 获取主力净流入排名...
[主力排名] 获取主力净流入排行...
[百度主力排名] 获取 200 条

[增强 2/2] 分析多日主力资金流入...

✅ 最终决策：从 23 只主板股票中选出 Top10
   筛选条件：综合评分排序 (成交额 + 涨幅 + 成交量 + 主力排名 + 多日资金流)
```

### 推送效果

```
### 🎯 工作流最终决策 Top10

━━━ ⭐⭐⭐ 强烈推荐 (2 只) ━━━

1. 📈 **浦发银行** (sh600000) ⭐⭐⭐
   现价：¥10.32 | 涨跌：+6.87% | 成交：45.2 亿
   🎯 置信度：90% | 命中 3 策略
   💰 主力排名：Top5
   📈 止盈：¥11.35 | 🛑 止损：¥9.29
   💡 理由：主力排名 Top5 | 主力净流入 5.2 亿 | 5 日 4 日净流入 | 资金流改善

━━━ ⭐⭐ 推荐 (3 只) ━━━
...
```

---

## 📋 字段对照表

| 旧字段名 | 新字段名 | 说明 |
|---------|---------|------|
| `is_popular` | `is_main_force_top` | 是否主力前 50 |
| `mainstream_rank` | `main_force_rank` | 主力排名 |
| `mainstream_score` | `main_force_score` | 主力分数 |
| - | `main_net` | 主力净流入 (元) |

---

## ✅ 测试验证

```bash
cd /home/admin/.openclaw/workspace/stocks

# 运行工作流
python3 run_workflow.py --strategy all --top 10 --push --record
```

**预期输出**:
- [增强 1/2] 获取主力净流入排名...
- [主力排名] 获取主力净流入排行...
- 推送中包含"主力排名 TopX"信息

---

**修改完成!** 现在使用主力净流入排名代替成交额排名。
