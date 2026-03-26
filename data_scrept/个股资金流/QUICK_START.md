# 快速开始 - 获取东方财富个股资金流数据

> ✅ **本文档说明如何使用可用脚本获取真实数据**

---

## 🚀 5 分钟快速开始

### 步骤 1: 打开东方财富网页面

```bash
browser open https://data.eastmoney.com/zjlx/detail.html
```

### 步骤 2: 手动完成验证码

在打开的浏览器窗口中，拖动滑块完成拼图验证。

### 步骤 3: 等待数据加载

```bash
# 等待 10 秒让数据加载完成
browser act <targetId> wait --time-ms 10000
```

### 步骤 4: 滚动页面触发数据加载

```bash
# 滚动到页面底部
browser act <targetId> evaluate --fn "() => { window.scrollTo(0, document.body.scrollHeight); }"

# 再等待 5 秒
browser act <targetId> wait --time-ms 5000
```

### 步骤 5: 提取数据

```javascript
// 使用以下 JS 代码提取前 100 名数据
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
  return JSON.stringify({count: data.length, data: data});
}
```

执行命令：
```bash
browser act <targetId> evaluate --fn "<上面的 JS 代码>"
```

### 步骤 6: 保存并处理数据

将返回的 JSON 数据保存为文件，例如 `data.json`，然后：

```bash
# 处理数据并保存
python3 /home/admin/.openclaw/workspace/data_scrept/process_data.py data.json 100
```

### 步骤 7: 查看结果

```bash
# 查看生成的文件
ls -la /home/admin/.openclaw/workspace/data_files/

# 查看 JSON 内容
cat /home/admin/.openclaw/workspace/data_files/capital_flow_*.json

# 查看 CSV 内容（前 20 行）
head -20 /home/admin/.openclaw/workspace/data_files/capital_flow_*.csv
```

---

## 📁 输出文件

每次处理会生成两个文件：

| 文件 | 格式 | 说明 |
|------|------|------|
| `capital_flow_YYYYMMDD_HHMMSS.json` | JSON | 完整数据，可用于程序处理 |
| `capital_flow_YYYYMMDD_HHMMSS.csv` | CSV | 表格数据，可用 Excel 打开 |

---

## 📊 数据字段

| 字段 | 说明 |
|------|------|
| 排名 | 主力净流入排名 |
| 代码 | 股票代码 |
| 名称 | 股票名称 |
| 最新价 | 当前股价 |
| 涨跌幅 | 今日涨跌幅 |
| 主力净流入 | 主力资金净流入金额 |
| 主力净占比 | 主力净流入占成交额比例 |

---

## ⚠️ 常见问题

### Q: 看不到数据表格？
**A**: 确保已完成验证码，并等待足够时间（至少 10 秒）。

### Q: 提取的数据为空？
**A**: 尝试滚动页面后再提取，或刷新页面重新操作。

### Q: 如何处理已保存的 JSON 文件？
**A**: 使用 `process_data.py` 脚本处理：
```bash
python3 /home/admin/.openclaw/workspace/data_scrept/process_data.py your_file.json 100
```

---

## 📖 更多文档

- **可用脚本说明**: `AVAILABLE_SCRIPTS.md`
- **完整文档**: `README.md`

---

## 📝 示例输出

```
排名，代码，名称，最新价，涨跌幅，主力净流入，主力净占比
1,601669，中国电建，7.19,+9.94%,20.61 亿，16.13%
2,300502，新易盛，394.03,+4.03%,16.04 亿，10.08%
3,601611，中国核建，19.21,+10.02%,13.17 亿，23.00%
```
