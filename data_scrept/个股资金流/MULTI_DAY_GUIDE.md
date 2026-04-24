# 东方财富多日排行资金流数据获取指南

> ✅ **本文档说明如何获取今日/3 日/5 日/10 日排行数据**

---

## 📋 排行类型说明

| 排行 | 说明 | 数据字段 |
|------|------|----------|
| **今日排行** | 当日主力净流入排名 | 今日主力净流入、今日涨跌幅 |
| **3 日排行** | 近 3 个交易日累计排名 | 3 日主力净流入、3 日涨跌幅 |
| **5 日排行** | 近 5 个交易日累计排名 | 5 日主力净流入、5 日涨跌幅 |
| **10 日排行** | 近 10 个交易日累计排名 | 10 日主力净流入、10 日涨跌幅 |

---

## 🚀 获取步骤（以 3 日排行为例）

### 步骤 1: 打开页面

```bash
browser open https://data.eastmoney.com/zjlx/detail.html
```

### 步骤 2: 完成验证码

在浏览器中手动拖动滑块完成拼图验证。

### 步骤 3: 切换到 3 日排行

在页面中找到排行选项卡，点击"3 日排行"：

```bash
# 找到并点击 3 日排行按钮（ref 可能变化，需要查看 snapshot）
browser act <targetId> click --ref <3 日排行按钮的 ref>
```

或者使用 evaluate 点击：

```bash
browser act <targetId> evaluate --fn "() => {
  const tabs = document.querySelectorAll('[class*=\\'tab\\'], [role*=\\'tab\\']');
  tabs.forEach(tab => {
    if(tab.textContent.includes('3 日')) tab.click();
  });
}"
```

### 步骤 4: 等待数据加载

```bash
browser act <targetId> wait --time-ms 10000
```

### 步骤 5: 滚动页面

```bash
browser act <targetId> evaluate --fn "() => { window.scrollTo(0, document.body.scrollHeight); }"
browser act <targetId> wait --time-ms 5000
```

### 步骤 6: 提取数据

```javascript
() => {
  const rows = document.querySelectorAll('.dataview-body tbody tr');
  const data = [];
  rows.forEach((row, idx) => {
    if(idx < 100 && row.querySelectorAll('td').length >= 7) {
      const cells = row.querySelectorAll('td');
      data.push({
        rank: cells[0]?.textContent?.trim(),
        code: cells[1]?.textContent?.trim(),
        name: cells[2]?.textContent?.trim(),
        price: cells[4]?.textContent?.trim(),
        changePct: cells[5]?.textContent?.trim(),
        mainInflow: cells[6]?.textContent?.trim(),
        mainRatio: cells[7]?.textContent?.trim()
      });
    }
  });
  return JSON.stringify({count: data.length, data: data, type: '3 日排行'});
}
```

执行命令：

```bash
browser act <targetId> evaluate --fn "<上面的 JS 代码>"
```

### 步骤 7: 保存并处理数据

将返回的 JSON 保存为 `data_3d.json`，然后：

```bash
python3 /home/admin/.openclaw/workspace/data_scrept/process_data.py data_3d.json 100
```

---

## 📊 不同排行的字段差异

### 今日排行
- 主力净流入 = f62
- 主力净占比 = f184
- 涨跌幅 = f3

### 3 日排行
- 主力净流入 = f262
- 主力净占比 = f263
- 涨跌幅 = 3 日累计

### 5 日排行
- 主力净流入 = f362
- 主力净占比 = f363
- 涨跌幅 = 5 日累计

### 10 日排行
- 主力净流入 = f462
- 主力净占比 = f463
- 涨跌幅 = 10 日累计

---

## 🔧 快速获取命令（复制即用）

### 今日排行

```bash
# 打开页面
browser open https://data.eastmoney.com/zjlx/detail.html

# 等待并完成验证码后
browser act <targetId> wait --time-ms 10000
browser act <targetId> evaluate --fn "() => { window.scrollTo(0, document.body.scrollHeight); }"
browser act <targetId> wait --time-ms 5000

# 提取数据
browser act <targetId> evaluate --fn "() => {
  const rows = document.querySelectorAll('.dataview-body tbody tr');
  const data = [];
  rows.forEach((row, idx) => {
    if(idx < 100 && row.querySelectorAll('td').length >= 7) {
      const cells = row.querySelectorAll('td');
      data.push({
        rank: cells[0]?.textContent?.trim(),
        code: cells[1]?.textContent?.trim(),
        name: cells[2]?.textContent?.trim(),
        price: cells[4]?.textContent?.trim(),
        changePct: cells[5]?.textContent?.trim(),
        mainInflow: cells[6]?.textContent?.trim(),
        mainRatio: cells[7]?.textContent?.trim(),
        type: '今日'
      });
    }
  });
  return JSON.stringify({count: data.length, data: data});
}"
```

### 3 日排行

先点击 3 日排行选项卡，然后使用相同的提取命令。

---

## 📁 输出文件命名

| 排行类型 | JSON 文件名 | CSV 文件名 |
|---------|------------|-----------|
| 今日 | `capital_flow_today_YYYYMMDD_HHMMSS.json` | `capital_flow_today_YYYYMMDD_HHMMSS.csv` |
| 3 日 | `capital_flow_3d_YYYYMMDD_HHMMSS.json` | `capital_flow_3d_YYYYMMDD_HHMMSS.csv` |
| 5 日 | `capital_flow_5d_YYYYMMDD_HHMMSS.json` | `capital_flow_5d_YYYYMMDD_HHMMSS.csv` |
| 10 日 | `capital_flow_10d_YYYYMMDD_HHMMSS.json` | `capital_flow_10d_YYYYMMDD_HHMMSS.csv` |

---

## 📝 示例输出

### 今日排行前 5 名

```
排名  代码      名称        最新价   涨跌幅    主力净流入   主力净占比
1     601669   中国电建    7.19    +9.94%   20.61 亿    16.13%
2     300502   新易盛      394.03  +4.03%   16.04 亿    10.08%
3     601611   中国核建    19.21   +10.02%  13.17 亿    23.00%
4     002463   沪电股份    81.18   +6.34%   11.16 亿    10.71%
5     002165   红宝丽      12.76   +10.00%  10.14 亿    42.57%
```

### 3 日排行前 5 名（示例）

```
排名  代码      名称        最新价   涨跌幅    主力净流入   主力净占比
1     XXXXXX   XXXX        XX.XX   +XX.XX%  XX.XX 亿    XX.XX%
...
```

---

## ⚠️ 注意事项

1. **验证码**: 每次打开页面都可能需要完成验证码
2. **排行切换**: 点击不同排行选项卡后需要等待数据加载
3. **数据时效**: 多日排行数据在收盘后更新
4. **保存文件**: 建议为不同排行保存不同的 JSON 文件

---

## 📖 相关文档

- **可用脚本说明**: `AVAILABLE_SCRIPTS.md`
- **快速开始**: `QUICK_START.md`
- **完整文档**: `README.md`

---

## 📊 数据用途

- **今日排行**: 发现当日主力资金关注方向
- **3 日排行**: 识别短期持续流入的个股
- **5 日排行**: 观察一周内资金趋势
- **10 日排行**: 分析中长期资金流向

---

**最后更新**: 2026-03-14
