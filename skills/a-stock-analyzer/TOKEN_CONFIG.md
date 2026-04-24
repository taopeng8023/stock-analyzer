# Tushare Token 配置说明

## 获取 Token

1. 访问 https://tushare.pro/user/token
2. 登录/注册 Tushare 账号
3. 复制你的 Token

## 配置方式

### 方式一：环境变量 (推荐)

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
export TS_TOKEN="你的 tushare token"

# 或临时设置
export TS_TOKEN="你的 tushare token"
python scripts/fetch_history_data.py
```

### 方式二：命令行参数

```bash
python scripts/fetch_history_data.py --token "你的 tushare token"
```

### 方式三：修改脚本

编辑 `scripts/fetch_history_data.py`，修改第 19 行：

```python
TS_TOKEN = '你的 tushare token'
```

## 权限要求

Tushare 基础接口 (daily) 需要：
- 注册并登录
- 积分 >= 0 (免费注册即可获得)

## 使用示例

```bash
# 获取默认股票列表 (2025-03-27 ~ 2026-03-27)
python scripts/fetch_history_data.py

# 获取单只股票
python scripts/fetch_history_data.py --stock 000001.SZ --token "your_token"

# 自定义日期范围
python scripts/fetch_history_data.py --start 20240101 --end 20260327

# 从文件读取股票列表
python scripts/fetch_history_data.py --stock-list stocks.txt
```

## 默认股票列表

脚本内置了 30 只主要 A 股股票：
- 上证指数成分股：贵州茅台、中国平安、招商银行等
- 深证成指成分股：平安银行、万科 A、美的集团等
- 创业板：东方财富、宁德时代、迈瑞医疗等

## 数据保存位置

`/home/admin/.openclaw/workspace/skills/a-stock-analyzer/data/`

文件格式：`{股票代码}.csv` (如：`000001_SZ.csv`)
