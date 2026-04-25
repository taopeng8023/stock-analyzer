# 📊 东方财富多日资金流集成

**更新时间**: 2026-03-20 18:40  
**状态**: ⚠️ 部分完成

---

## 🎯 实现内容

已集成东方财富多日主力资金流数据源：

### 数据源优先级

```
1. 东方财富 - 真实主力净流入数据 (优先)
2. 本地缓存 K 线 - 估算数据 (备用)
```

---

## 📁 修改文件

### fund_flow.py

**新增方法**:
```python
def _get_em_multi_day_flow(symbol, days) -> List[Dict]
def _get_multi_day_flow_from_cache(symbol, days) -> List[Dict]
def get_multi_day_flow(symbol, days) -> List[Dict]
```

**返回数据**:
```python
{
    'date': '2026-03-20',
    'main_net': 500000000,  # 主力净流入 (元)
    'super_net': 200000000, # 超大单 (元)
    'big_net': 300000000,   # 大单 (元)
    'is_real': True,        # 真实数据标记
}
```

---

## 📊 API 说明

### 东方财富资金流 API

```
URL: http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get

参数:
- secid: 市场代码。股票代码 (1.sh600000 或 0.sz000001)
- lmt: 获取天数
- klt: K 线类型 (1=日线)
- fields1: 字段 1
- fields2: 字段 2

返回格式:
klines: [
  "2026-03-20,9950.90,3200.50,6750.40,...",
  "2026-03-19,..."
]
```

---

## ⚠️ 当前状态

### 已实现

- ✅ 东方财富 API 接口
- ✅ 数据解析逻辑
- ✅ 单位转换 (万→元)
- ✅ 异常值处理
- ✅ 真实数据标记

### 存在问题

- ⚠️ API 只返回 1 天数据 (可能需调整参数)
- ⚠️ 需要进一步测试

### 备用方案

东方财富失败时自动降级到本地缓存估算：
```python
def get_multi_day_flow(symbol, days):
    em_data = _get_em_multi_day_flow(symbol, days)
    if em_data:
        return em_data  # 真实数据
    
    return _get_multi_day_flow_from_cache(symbol, days)  # 估算数据
```

---

## 🚀 使用

```python
from fund_flow import FundFlowFetcher

fetcher = FundFlowFetcher()

# 获取多日资金流 (自动选择数据源)
result = fetcher.get_multi_day_flow('sh600000', days=5)

# 分析
analysis = fetcher.analyze_multi_day_flow('sh600000', days=5)

print(f"数据源：{analysis['data_source']}")  # eastmoney / estimate
print(f"是否真实：{analysis['is_real_data']}")
```

---

## 📈 分析增强

**真实数据加分**:
```python
# 综合评分 = 连续性×0.6 + 强度×0.4 + 数据源加分
if is_real_data:
    composite_score += 10  # 真实数据额外加 10 分
```

**推送显示**:
```
💡 理由：5 日 5 日连续净流入 (真实数据)
```

---

## 📝 下一步

### 短期

- [ ] 修复东方财富 API 参数 (获取多日数据)
- [ ] 测试更多股票
- [ ] 添加缓存机制

### 中期

- [ ] 添加更多东方财富数据字段
- [ ] 板块资金流
- [ ] 行业资金流

---

**状态**: ⚠️ 部分完成，需要进一步调试东方财富 API 参数。
