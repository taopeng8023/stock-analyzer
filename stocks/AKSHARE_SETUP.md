# 📥 AKShare 集成指南

**同花顺真实数据接口**

---

## 🚀 快速开始

### 1. 安装 AKShare

```bash
# 方法 1：直接安装
pip install akshare

# 方法 2：使用国内镜像（更快）
pip install akshare -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方法 3：如果 pip 不可用
python3 -m pip install akshare
```

### 2. 验证安装

```bash
python3 -c "import akshare as ak; print('AKShare 版本:', ak.__version__)"
```

成功输出：
```
AKShare 版本：1.x.x
```

### 3. 获取数据

```bash
# 查看个股资金流排行
python3 akshare_flow.py --top 10

# 查看行业资金流
python3 akshare_flow.py --industry

# 查看概念资金流
python3 akshare_flow.py --concept

# 查看个股详情
python3 akshare_flow.py --stock 浦发银行
```

---

## 📊 数据说明

### 数据来源

| 数据项 | 来源 | 真实性 |
|--------|------|--------|
| 个股资金流 | 同花顺 | ✅ 真实 |
| 行业资金流 | 同花顺 | ✅ 真实 |
| 概念资金流 | 同花顺 | ✅ 真实 |
| 个股详情 | 同花顺 | ✅ 真实 |

### 数据字段

**个股资金流排行:**
- 代码、名称、最新价、涨跌幅
- 主力净流入净额
- 特大单、大单、中单、小单净流入
- 所属行业

**个股详情:**
- 日期
- 主力净流入净额
- 特大单、大单、中单、小单净流入
- 历史数据（通常 1 年）

---

## 🔧 使用示例

### 示例 1：查看主力净流入排行

```bash
python3 akshare_flow.py --top 20
```

输出：
```
==========================================================================================
💰 个股资金流排行 (今日) Top20
数据源：AKShare/同花顺 (真实数据)
==========================================================================================

数据字段：['代码', '名称', '最新价', '涨跌幅', '主力净流入净额', ...]

前 10 条数据:
    代码      名称    最新价   涨跌幅   主力净流入净额
0  600000  浦发银行   10.38  +6.91%    12345.67 万
1  600519  贵州茅台  1485.00 +20.66%   23456.78 万
...

==========================================================================================
```

### 示例 2：查看行业资金流

```bash
python3 akshare_flow.py --industry
```

### 示例 3：查看个股详情

```bash
python3 akshare_flow.py --stock 浦发银行
```

### 示例 4：保存 CSV

```bash
# 保存排行数据
python3 akshare_flow.py --top 50 --save

# 保存行业数据
python3 akshare_flow.py --industry --save

# 保存个股详情
python3 akshare_flow.py --stock 浦发银行 --save
```

---

## 📁 导入研究数据库

### 导入排行前 10 只股票

```bash
python3 import_akshare.py --all --top 10
```

### 导入单只股票

```bash
python3 import_akshare.py --code 浦发银行
```

### 导入行业数据

```bash
python3 import_akshare.py --industry
```

---

## ⚠️ 注意事项

### 1. 安装问题

**问题：** pip 不可用

**解决：**
```bash
# 使用 python3 -m pip
python3 -m pip install akshare

# 或下载离线包安装
wget https://files.pythonhosted.org/packages/.../akshare-1.x.x-py3-none-any.whl
pip install akshare-1.x.x-py3-none-any.whl
```

**问题：** 依赖冲突

**解决：**
```bash
# 升级 pip
pip install --upgrade pip

# 使用虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install akshare
```

### 2. 数据获取失败

**问题：** 网络超时

**解决：**
```python
# 增加超时时间
import akshare as ak
ak.set_timeout(30)
```

**问题：** 数据为空

**解决：**
- 检查股票名称是否正确
- 检查市场是否正确（沪/深）
- 等待几分钟重试

### 3. 访问频率

**建议：**
- 每次请求间隔 0.5-1 秒
- 单次获取不超过 100 条
- 避免多线程并发

---

## 📊 与 Tushare 对比

| 特性 | AKShare/同花顺 | Tushare |
|------|---------------|---------|
| **数据质量** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **安装** | 需要 pip | 需要 pip |
| **Token** | 不需要 | 需要 |
| **积分** | 不需要 | 需要 120 积分 |
| **权限** | 无限制 | 需要审批 |
| **文档** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **稳定性** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 💡 推荐工作流

### 方案 A：使用 AKShare（立即可用）

```bash
# 1. 安装
pip install akshare

# 2. 获取数据
python3 akshare_flow.py --top 20

# 3. 导入研究数据库
python3 import_akshare.py --all --top 10

# 4. 分析
python3 research_simple.py --code 600000.SH
```

### 方案 B：等待 Tushare 权限

```bash
# 1. 等待 Tushare 审批
# 2. 配置 Token
python3 tushare_flow.py --config <token>

# 3. 导入数据
python3 research_import.py --code 600000.SH
```

### 方案 C：混合使用

```bash
# 日常使用 AKShare
python3 akshare_flow.py --top 20

# 重要研究用 Tushare（更稳定）
python3 tushare_flow.py --top 20
```

---

## 📚 相关文档

- `THS_DATA_GUIDE.md` - 同花顺数据使用指南
- `RESEARCH_DATA_POLICY.md` - 研究数据政策
- `CURRENT_STATUS_FINAL.md` - 当前系统状态

---

## 🔗 相关链接

- **AKShare 官网：** https://akshare.akfamily.xyz
- **GitHub:** https://github.com/akfamily/akshare
- **文档:** https://akshare.akfamily.xyz/data/index.html
- **同花顺:** http://www.10jqka.com.cn

---

**最后更新：2026-03-17 23:55**

**状态：✅ 已集成 AKShare/同花顺真实数据**

**⚠️ 仅用于个人研究学习，不得用于商业用途**
