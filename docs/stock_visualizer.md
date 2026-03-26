# 股票可视化系统使用指南

## 📋 系统概述

提供三种可视化方案，满足不同需求：

| 版本 | 脚本 | 依赖 | 特点 |
|------|------|------|------|
| **HTML 版** | `stock_visualizer_html.py` | 无（使用 CDN） | ⭐推荐，交互式图表 |
| **简化版** | `stock_visualizer_lite.py` | matplotlib | 静态图片，适合报告 |
| **完整版** | `stock_visualizer.py` | mplfinance | 专业 K 线图 |

---

## 🚀 快速开始

### 方案一：HTML 交互式图表（推荐）

**无需安装任何依赖**，使用浏览器即可查看交互式图表。

```bash
# 运行 HTML 版可视化
python3 /home/admin/.openclaw/workspace/scripts/stock_visualizer_html.py
```

**输出文件：**
- `/home/admin/.openclaw/workspace/data/charts/dashboard_002475.html`

**查看方式：**
```bash
# 使用浏览器打开
firefox /home/admin/.openclaw/workspace/data/charts/dashboard_002475.html
# 或
chrome /home/admin/.openclaw/workspace/data/charts/dashboard_002475.html
```

**功能特性：**
- ✅ 交互式 K 线图（可缩放、平移）
- ✅ MACD 指标图
- ✅ 悬停查看数据详情
- ✅ 均线切换显示
- ✅ 响应式设计（支持手机）
- ✅ 技术指标明细表
- ✅ 资金流分析
- ✅ 推荐建议卡片

---

### 方案二：Matplotlib 静态图表

```bash
# 安装依赖
pip3 install matplotlib pandas numpy

# 运行简化版可视化
python3 /home/admin/.openclaw/workspace/scripts/stock_visualizer_lite.py
```

**输出文件：**
- `kdj_002475.png` - KDJ 分析图
- `dashboard_002475.png` - 综合仪表盘

---

### 方案三：Mplfinance 专业图表

```bash
# 安装依赖
pip3 install mplfinance matplotlib pandas numpy

# 运行完整版可视化
python3 /home/admin/.openclaw/workspace/scripts/stock_visualizer.py
```

---

## 📊 HTML 图表功能展示

### 1. 综合评分卡片

```
┌─────────────────────────────────────────────────┐
│  80.5        27.5        20.0        70%        │
│ 综合评分    技术面      资金面     盈利概率    │
└─────────────────────────────────────────────────┘
```

### 2. K 线图 + 均线

- **蜡烛图**：红涨绿跌
- **MA5**：白线（攻击线）
- **MA10**：黄线（操盘线）
- **MA20**：青线（月线）
- **交互功能**：
  - 鼠标悬停查看 OHLC 数据
  - 拖拽平移
  - 滚轮缩放
  - 双击复位

### 3. MACD 指标

- **红绿柱**：MACD 柱状图
- **白线**：DIF（快线）
- **黄线**：DEA（慢线）
- **0 轴**：多空分界线

### 4. 技术指标明细表

| 指标 | 得分 | 数值 | 状态 |
|------|------|------|------|
| MACD | 10.0/10 | DIF: 1.50 | 金叉 |
| KDJ | 8.0/10 | K: 75 | 中性 |
| RSI | 8.0/10 | RSI6: 68 | 多头 |
| 均线 | 9.0/10 | MA5: 49.50 | 多头 |
| 成交量 | 10.0/10 | 量比：3.14 | 活跃 |

### 5. 资金流分析

| 项目 | 数值 |
|------|------|
| 主力净流入 | 296,900 万 |
| 主力占比 | 22.76% |
| 超大单占比 | 27.70% |
| 成交额 | 128.0 亿 |
| 换手率 | 3.53% |

### 6. 推荐建议

```
┌──────────────────────────────────────┐
│  15-20%        +10-15%        -10%   │
│  建议仓位       止盈目标        止损   │
└──────────────────────────────────────┘
```

---

## 🔧 集成到推荐系统

### 方法一：在推荐脚本中调用

```python
from scripts.stock_visualizer_html import create_html_chart

# 在推荐系统运行后生成图表
stock_info = {
    'total_score': 80.5,
    'tech_score': 27.5,
    'fund_score': 20.0,
    # ... 其他指标
}

create_html_chart(
    code='002475',
    name='立讯精密',
    stock_info=stock_info,
    save_path='/path/to/chart.html'
)
```

### 方法二：批量生成多只股票图表

```python
from scripts.stock_visualizer_html import create_html_chart

top_stocks = [
    {'code': '002475', 'name': '立讯精密', 'info': {...}},
    {'code': '601899', 'name': '紫金矿业', 'info': {...}},
    {'code': '300394', 'name': '天孚通信', 'info': {...}},
]

for stock in top_stocks:
    create_html_chart(
        code=stock['code'],
        name=stock['name'],
        stock_info=stock['info'],
        save_path=f"/path/to/chart_{stock['code']}.html"
    )
```

---

## 📁 文件结构

```
/home/admin/.openclaw/workspace/
├── scripts/
│   ├── stock_visualizer_html.py      # HTML 版（推荐）
│   ├── stock_visualizer_lite.py      # Matplotlib 简化版
│   ├── stock_visualizer.py           # Mplfinance 完整版
│   └── stock_recommender_v3.py       # 推荐系统 v3.0
├── data/
│   └── charts/
│       ├── dashboard_002475.html     # HTML 仪表盘
│       ├── kdj_002475.png            # KDJ 分析图
│       └── dashboard_002475.png      # 综合仪表盘
└── docs/
    └── stock_visualizer.md           # 本文档
```

---

## 🎨 自定义样式

### 修改颜色主题

在 `stock_visualizer_html.py` 中修改 CSS：

```css
/* 渐变背景 */
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 卡片阴影 */
.score-item {
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
```

### 修改图表配置

```javascript
const layoutKline = {
    title: '{name} ({code}) K 线与均线',
    plot_bgcolor: '#1e1e1e',    // 背景色
    paper_bgcolor: '#1e1e1e',   // 纸张背景
    font: {color: 'white'},     // 字体颜色
    // ...
};
```

---

## 📱 移动端适配

HTML 图表已支持响应式设计：

- 自动调整图表大小
- 支持触摸缩放
- 自适应屏幕宽度
- 卡片式布局

---

## ⚠️ 注意事项

1. **HTML 图表需要网络连接**
   - 使用 Plotly.js CDN，需访问 `cdn.plot.ly`
   - 如需离线使用，可下载 Plotly.js 本地部署

2. **数据更新**
   - 当前使用模拟数据
   - 实际使用时需接入真实行情 API

3. **浏览器兼容性**
   - 推荐 Chrome/Firefox/Edge
   - Safari 部分功能可能受限

4. **文件大小**
   - HTML 文件约 20-30KB
   - PNG 图片约 200-500KB

---

## 🔗 相关文档

- [股票推荐系统 v3.0 文档](./stock_recommender_v3.md)
- [技术指标详解](./stock_recommender_v3.md#技术指标详解)
- [资金流评分标准](./stock_recommender_v2.md#资金流评分详解)

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-03-25 | 初始版本，Matplotlib 静态图表 |
| v2.0 | 2026-03-25 | **HTML 交互式图表**（无需依赖） |
| v3.0 | 2026-03-25 | 集成推荐系统，添加资金流展示 |

---

*最后更新：2026-03-25*
