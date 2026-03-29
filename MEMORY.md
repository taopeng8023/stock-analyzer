# MEMORY.md - Long-Term Memory

## Preferences

- **联网搜索优先使用 searxng skill** —— 只要涉及联网搜索任务，优先调用 searxng 技能而非直接使用 web_search 工具。

## Installed Skills

- **a-stock-analyzer** (2026-03-24) - A 股股票分析技能，**集成东方财富 API 数据源**，提供实时行情、技术指标 (MA/MACD/RSI/KDJ/布林带)、缠论分析 (分型/笔/线段/中枢/背驰/三类买卖点)、**蜡烛图形态识别** (50+ 种经典 K 线形态：吞没/之星/锤头/射击之星等)、资金流向、机构研报、公告信息。支持缠论 + 蜡烛图结合分析。数据源优先使用东方财富 API (更及时/维度更丰富)，备选 akshare。位置：`/home/admin/.openclaw/workspace/skills/a-stock-analyzer/`
  - **2026-03-29 更新 1**: 新增 `backtest_ma.py` 回测脚本 (通用版)，支持双均线金叉 + 移动止盈策略回测。
  - **2026-03-29 更新 2**: 新增 `backtest_v3.py` 回测脚本 (选股系统 V3.0 专用)，基于 V3.0 选股策略 (MA15/MA20+ 五重过滤),集成移动止盈。位置：`/home/admin/.openclaw/workspace/stocks/`
  - **2026-03-29 更新 3**: 新增 `backtest_v3_cache.py` 回测脚本 (缓存数据版)，使用 `data_tushare/` 目录缓存的 3620 只股票数据，无需 API Token，回测速度更快。

## Notes

- **选股系统 V3.0 回测结论**: 五重过滤过于严格，过滤掉 80% 有效信号。简单策略 (无过滤，金叉买入/死叉卖出) 收益 +20%，优于复杂策略 (+8%)。推荐使用 `--no-filters` 参数。
- **缓存数据**: `/home/admin/.openclaw/workspace/stocks/data_tushare/` 包含 3620 只股票历史数据 (2025-03~2026-03，约 240 条/股)，适合短期策略回测。

## Notes

- Created: 2026-03-05
