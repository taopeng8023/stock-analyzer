# 🐍 Python 升级指南

**时间**: 2026 年 3 月 27 日  
**目标**: 升级 Python 到 3.9+ 以支持 AkShare

---

## 📊 当前状态

| 项目 | 版本 | 状态 |
|------|------|------|
| Python | 3.6.8 / 3.8.17 | ⚠️ 不满足 AkShare 要求 |
| AkShare | - | ❌ 需要 Python 3.9+ |
| Tushare | - | ✅ 支持 Python 3.8 |

---

## 🎯 升级方案对比

### 方案 1: 源码编译 Python 3.9（推荐但耗时）

**时间**: 30-60 分钟  
**难度**: 中等  
**影响**: 不影响现有 Python 环境

**步骤**:
```bash
# 1. 安装依赖
sudo yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget

# 2. 下载 Python 3.9
cd /tmp
wget https://www.python.org/ftp/python/3.9.18/Python-3.9.18.tgz
tar -xzf Python-3.9.18.tgz
cd Python-3.9.18

# 3. 编译安装
./configure --enable-optimizations --prefix=/usr/local/python3.9
make -j$(nproc)
sudo make altinstall

# 4. 验证
python3.9 --version

# 5. 安装 pip
python3.9 -m ensurepip --upgrade

# 6. 安装 AkShare
python3.9 -m pip install akshare
```

**优点**:
- ✅ 稳定可靠
- ✅ 不影响现有环境
- ✅ 可以安装多个版本

**缺点**:
- ⏳ 编译时间长（30-60 分钟）
- ⚠️ 需要编译工具

---

### 方案 2: 使用 Tushare（立即可用 ⭐⭐⭐⭐⭐）

**时间**: 5 分钟  
**难度**: 简单  
**影响**: 无

**步骤**:
```bash
# 1. 安装 Tushare（支持 Python 3.8）
pip3 install --user tushare

# 2. 获取 Token
# 访问 https://tushare.pro 注册账号
# 获取免费 Token

# 3. 修改代码
# 编辑 stocks/akshare_integration.py
# token='your_tushare_token'

# 4. 测试
python3 stocks/akshare_integration.py
```

**优点**:
- ✅ 立即可用
- ✅ 支持 Python 3.8
- ✅ 数据稳定
- ✅ 文档完善

**缺点**:
- ⚠️ 需要注册 Token（免费）
- ⚠️ 高级功能需要积分

---

### 方案 3: 使用 Conda（如果已安装）

**时间**: 10 分钟  
**难度**: 简单

**步骤**:
```bash
# 1. 创建新环境
conda create -n stock python=3.9

# 2. 激活环境
conda activate stock

# 3. 安装 AkShare
pip install akshare

# 4. 使用
python stocks/akshare_integration.py
```

**优点**:
- ✅ 快速
- ✅ 隔离环境

**缺点**:
- ⚠️ 需要已安装 Conda

---

## 💡 推荐方案

**鹏总，强烈建议**:

### 今天（立即行动）
**使用 Tushare** - 5 分钟即可完成，立即可用！

```bash
# 1. 安装
pip3 install --user tushare

# 2. 获取 Token（5 分钟）
# 访问 https://tushare.pro
# 注册 → 获取 Token

# 3. 测试
python3 stocks/akshare_integration.py
```

### 本周（有时间再做）
**升级 Python** - 源码编译，更稳定

```bash
# 周末空闲时执行
# 预计耗时：30-60 分钟
sudo yum install -y gcc openssl-devel bzip2-devel libffi-devel
# ... 按方案 1 执行
```

---

## 📁 代码已就绪

**文件**: `stocks/akshare_integration.py`

**功能**:
- ✅ AkShare 数据获取
- ✅ Tushare 数据获取
- ✅ 自动降级处理
- ✅ 完整错误处理

**使用**:
```python
from akshare_integration import AkShareDataFetcher, TushareDataFetcher

# AkShare（需要 Python 3.9+）
ak_fetcher = AkShareDataFetcher()
stocks = ak_fetcher.get_main_force_rank()

# Tushare（支持 Python 3.8）
ts_fetcher = TushareDataFetcher(token='your_token')
stocks = ts_fetcher.get_main_force_rank()
```

---

## 🚀 立即开始（使用 Tushare）

### 第 1 步：安装 Tushare

```bash
pip3 install --user tushare
```

### 第 2 步：获取 Token

1. 访问 https://tushare.pro
2. 点击右上角"注册"
3. 填写邮箱、密码
4. 邮箱验证
5. 登录后点击"个人主页"
6. 复制 Token（一串字母数字）

### 第 3 步：配置 Token

编辑 `stocks/akshare_integration.py`:

```python
# 找到这一行（约第 120 行）
self.token = token or 'your_tushare_token'

# 改为：
self.token = token or '你的 token'
```

### 第 4 步：测试运行

```bash
cd /home/admin/.openclaw/workspace/stocks
python3 akshare_integration.py
```

### 预期输出

```
✅ Tushare 已安装
✅ Tushare 初始化成功
📊 使用 Tushare 获取资金流向...
✅ 获取成功，共 100 条数据

📊 获取到 100 条数据
----------------------------------------------------------------------
序号   代码     名称       价格     涨幅     主力净额
----------------------------------------------------------------------
1    601899   紫金矿业   ¥32.09   +1.25%    12.50 亿
2    600930   华电新能   ¥6.95    +4.35%     8.20 亿
...
----------------------------------------------------------------------
```

---

## ⏳ Python 升级（周末执行）

### 完整命令

```bash
# 1. 安装编译依赖
sudo yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make curl

# 2. 下载 Python 3.9.18
cd /tmp
wget https://www.python.org/ftp/python/3.9.18/Python-3.9.18.tgz

# 3. 解压
tar -xzf Python-3.9.18.tgz
cd Python-3.9.18

# 4. 配置（启用优化）
./configure --enable-optimizations --prefix=/usr/local/python3.9

# 5. 编译（约 20-30 分钟）
make -j$(nproc)

# 6. 安装
sudo make altinstall

# 7. 验证
/usr/local/python3.9/bin/python3.9 --version

# 8. 安装 pip
/usr/local/python3.9/bin/python3.9 -m ensurepip --upgrade

# 9. 安装 AkShare
/usr/local/python3.9/bin/python3.9 -m pip install akshare

# 10. 创建软链接（可选）
sudo ln -s /usr/local/python3.9/bin/python3.9 /usr/local/bin/python3.9
sudo ln -s /usr/local/python3.9/bin/pip3.9 /usr/local/bin/pip3.9

# 11. 测试
python3.9 -c "import akshare; print('✅ AkShare 可用')"
```

---

## 📊 对比总结

| 方案 | 时间 | 难度 | 推荐度 |
|------|------|------|--------|
| Tushare | 5 分钟 | ⭐ | ⭐⭐⭐⭐⭐ |
| Python 升级 | 60 分钟 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Conda | 10 分钟 | ⭐⭐ | ⭐⭐⭐ |

---

## 💡 最终建议

**鹏总，建议**:

### 今天（现在）
1. ✅ **安装 Tushare**（5 分钟）
2. ✅ **获取 Token**（5 分钟）
3. ✅ **测试运行**（2 分钟）
4. ✅ **开始推送**（立即）

### 周末（有时间）
1. ⏳ **升级 Python**（60 分钟）
2. ⏳ **安装 AkShare**（5 分钟）
3. ⏳ **切换数据源**（2 分钟）

---

## 📞 下一步

**鹏总，现在可以**:

1. **立即使用 Tushare** - 我帮您安装配置
2. **周末升级 Python** - 我提供完整脚本
3. **两者都用** - Tushare 先用，Python 升级后切 AkShare

**您想现在安装 Tushare 吗？** 🚀
