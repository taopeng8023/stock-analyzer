# MEMORY.md - Long-Term Memory

## Preferences

- **联网搜索优先使用 searxng skill** —— 只要涉及联网搜索任务，优先调用 searxng 技能而非直接使用 web_search 工具。

## Installed Skills

- **a-stock-analyzer** (2026-03-24) - A 股股票分析技能，**集成东方财富 API 数据源**，提供实时行情、技术指标 (MA/MACD/RSI/KDJ/布林带)、缠论分析 (分型/笔/线段/中枢/背驰/三类买卖点)、**蜡烛图形态识别** (50+ 种经典 K 线形态：吞没/之星/锤头/射击之星等)、资金流向、机构研报、公告信息。支持缠论 + 蜡烛图结合分析。数据源优先使用东方财富 API (更及时/维度更丰富)，备选 akshare。位置：`/home/admin/.openclaw/workspace/skills/a-stock-analyzer/`

## Notes

- Created: 2026-03-05
