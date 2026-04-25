# Tushare Pro 配置指南

## 📊 什么是 Tushare？

Tushare Pro 是一个免费、开源的金融数据接口平台，提供：
- ✅ A 股实时行情
- ✅ 主力资金流数据
- ✅ 财务报表
- ✅ 技术指标
- ✅ 更多金融数据

**官网：** https://tushare.pro

---

## 🚀 快速开始

### 1. 注册账号

1. 访问 https://tushare.pro
2. 点击右上角 **注册**
3. 填写邮箱、密码完成注册

### 2. 获取 Token

1. 登录后进入 **个人中心**
2. 找到 **接口 Token** 或 **我的 Token**
3. 复制 Token（一串字母数字组合）

示例 Token 格式：`a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

### 3. 配置 Token

#### 方法 1：命令行配置

```bash
cd /home/admin/.openclaw/workspace/stocks

# 保存 Token
python3 tushare_flow.py --config a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

# 验证 Token
python3 tushare_flow.py --check
```

#### 方法 2：环境变量

```bash
export TUSHARE_TOKEN=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

# 添加到 ~/.bashrc 永久生效
echo "export TUSHARE_TOKEN=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" >> ~/.bashrc
source ~/.bashrc
```

#### 方法 3：代码中设置

```python
from tushare_flow import TushareFetcher

fetcher = TushareFetcher(token='a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6')
```

---

## 💰 积分制度

Tushare 使用积分制，基础数据免费：

### 获取积分

- **注册赠送**: 100 积分
- **每日签到**: +10 积分
- **分享推广**: +50~100 积分
- **完善资料**: +20 积分

### 基础数据需求

| 数据接口 | 所需积分 | 说明 |
|---------|---------|------|
| stock_basic | 免费 | 股票列表 |
| daily | 免费 | 日线行情 |
| trade_cal | 免费 | 交易日历 |
| moneyflow | **120 积分** | 资金流数据 ⚠️ |

**结论：** 
- 基础行情数据免费使用
- **资金流数据 (moneyflow) 需要 120 积分**
- 注册送 100 积分，还需 20 积分
- 每日签到 +10 积分，2 天即可解锁

---

## 📊 使用示例

### 1. 主力净流入排行

```bash
# 使用 Tushare
python3 tushare_flow.py --top 20

# 指定日期
python3 tushare_flow.py --top 20 --date 20260317

# 个股资金流历史
python3 tushare_flow.py --stock 600000.SH
```

### 2. 集成到 fund_flow

```bash
# 自动选择数据源（优先 Tushare）
python3 fund_flow.py --top 20

# 强制使用 Tushare
python3 fund_flow.py --top 20 --source tushare

# 临时指定 Token
python3 fund_flow.py --top 20 --tushare-token a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### 3. Python API

```python
from tushare_flow import TushareFetcher

# 初始化
fetcher = TushareFetcher(token='your_token')

# 获取资金流排行
stocks = fetcher.get_moneyflow_rank(trade_date='20260317', limit=50)

# 打印排行
fetcher.print_ranking(stocks, top_n=10)

# 获取个股历史
history = fetcher.get_individual_moneyflow('600000.SH')
fetcher.print_individual('600000.SH', history)
```

---

## 🔍 数据字段说明

### moneyflow 接口

| 字段 | 说明 | 单位 |
|------|------|------|
| ts_code | 股票代码 | - |
| trade_date | 交易日期 | YYYYMMDD |
| buy_sm_amount | 小单买入金额 | 万 |
| sell_sm_amount | 小单卖出金额 | 万 |
| buy_md_amount | 中单买入金额 | 万 |
| sell_md_amount | 中单卖出金额 | 万 |
| buy_lg_amount | 大单买入金额 | 万 |
| sell_lg_amount | 大单卖出金额 | 万 |
| buy_elg_amount | 特大单买入金额 | 万 |
| sell_elg_amount | 特大单卖出金额 | 万 |
| **net_mf_amount** | **主力资金净流入净额** | **万** |

### 主力净流入计算

```
主力净流入 = (特大单买入 + 大单买入) - (特大单卖出 + 大单卖出)
```

Tushare 直接提供 `net_mf_amount` 字段，更准确！

---

## ⚠️ 常见问题

### Q1: Token 无效？

**检查：**
1. Token 是否复制完整（无空格）
2. Token 是否过期（重新获取）
3. 网络连接是否正常

**解决：**
```bash
python3 tushare_flow.py --check
```

### Q2: 积分不足？

**解决：**
1. 每日签到（+10 积分）
2. 完善个人信息（+20 积分）
3. 分享推广（+50~100 积分）

基础数据（moneyflow）免费使用！

### Q3: 数据获取失败？

**可能原因：**
1. 网络问题
2. API 限制（每分钟调用次数）
3. 交易日期非交易日

**解决：**
```bash
# 检查交易日
python3 -c "from tushare_flow import TushareFetcher; f = TushareFetcher(); f.check_token()"
```

---

## 📈 数据对比

| 数据源 | 数据类型 | 准确性 | 稳定性 | 成本 |
|--------|---------|--------|--------|------|
| **Tushare** | 真实 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 免费 |
| 百度股市通 | 真实 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 免费 |
| 腾讯财经 | 估算 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 免费 |
| 东方财富 | 真实 | ⭐⭐⭐⭐⭐ | ⭐⭐ | 免费 |

**推荐：** Tushare > 百度 > 腾讯（估算）

---

## 🔗 相关链接

- **官网**: https://tushare.pro
- **文档**: https://tushare.pro/document/2
- **社区**: https://tushare.pro/user/community
- **数据字典**: https://tushare.pro/document/2?doc_id=27

---

## 📝 配置检查清单

- [ ] 注册 Tushare 账号
- [ ] 获取 API Token
- [ ] 配置 Token（命令行/环境变量）
- [ ] 验证 Token 有效
- [ ] 测试获取数据
- [ ] 集成到自动推送

---

**最后更新：2026-03-17**

**版本：v1.0**
