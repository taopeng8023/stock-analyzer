# A 股股票分析 - 安装与使用指南

## 环境要求

- **Python**: 3.8+ (推荐 3.9+)
- **必需库**: akshare, pandas

## 安装步骤

### 1. 检查 Python 版本

```bash
python3 --version
```

如果版本低于 3.8，建议升级 Python 或使用虚拟环境。

### 2. 安装依赖

```bash
pip3 install akshare pandas
```

或使用国内镜像加速：

```bash
pip3 install akshare pandas -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 验证安装

```bash
python3 -c "import akshare; print('akshare version:', akshare.__version__)"
```

## 使用方法

### 基础分析

```bash
cd /home/admin/.openclaw/workspace/skills/a-stock-analyzer
python3 scripts/analyze_stock.py 000001
```

### JSON 输出

```bash
python3 scripts/analyze_stock.py 000001 --json
```

### 包含历史数据

```bash
python3 scripts/analyze_stock.py 000001 --history --json
```

## 常见股票代码

| 代码 | 名称 | 板块 |
|------|------|------|
| 000001 | 平安银行 | 深市主板 |
| 000002 | 万科 A | 深市主板 |
| 000858 | 五粮液 | 深市主板 |
| 002594 | 比亚迪 | 深市中小板 |
| 300750 | 宁德时代 | 创业板 |
| 600000 | 浦发银行 | 沪市主板 |
| 600036 | 招商银行 | 沪市主板 |
| 600519 | 贵州茅台 | 沪市主板 |
| 601318 | 中国平安 | 沪市主板 |
| 688981 | 中芯国际 | 科创板 |

## 替代方案

如果无法安装 akshare，可考虑以下替代数据源：

### 方案 1: 使用 tushare

```bash
pip3 install tushare
```

需要注册获取 API key：https://tushare.pro

### 方案 2: 使用 baostock

```bash
pip3 install baostock
```

免费免注册，但数据可能有延迟。

### 方案 3: 使用 yfinance (美股/港股)

```bash
pip3 install yfinance
```

适合分析美股和港股。

## 在 OpenClaw 中使用

技能安装后，你可以直接问我：

- "分析一下贵州茅台 (600519) 的买卖信号"
- "平安银行现在能买入吗？"
- "宁德时代的技术指标怎么样？"
- "帮我看看 000001 的 MACD 和 KDJ"

我会调用这个技能为你生成详细的分析报告。

## 故障排查

### 问题 1: 导入 akshare 失败

```
ModuleNotFoundError: No module named 'akshare'
```

**解决**: 重新安装 akshare
```bash
pip3 install --upgrade akshare
```

### 问题 2: 数据获取失败

```
Error: 未找到股票 XXXXXX
```

**可能原因**:
- 股票代码错误
- 交易所休市
- 网络问题

**解决**: 检查代码格式 (6 位数字)，确认交易时间

### 问题 3: Python 版本过低

```
TypeError: 'type' object is not subscriptable
```

**解决**: 升级到 Python 3.9+，或使用虚拟环境：
```bash
python3.9 -m venv venv
source venv/bin/activate
pip install akshare pandas
```

## 免责声明

⚠️ **重要提示**:

1. 本工具提供的分析仅供参考，不构成投资建议
2. 股市有风险，投资需谨慎
3. 技术指标存在滞后性，需结合基本面、消息面综合判断
4. 请自行评估风险，独立做出投资决策
5. 过往表现不代表未来收益
