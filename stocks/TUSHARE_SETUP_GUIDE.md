# 📋 Tushare Pro 配置指南

**Tushare Pro**: 专业金融数据接口平台  
**官网**: https://tushare.pro  
**状态**: 📝 需申请 token

---

## 🚀 申请步骤

### 1. 注册账号

1. 访问 https://tushare.pro
2. 点击右上角"注册"
3. 填写邮箱、密码等信息
4. 验证邮箱

### 2. 获取 Token

1. 登录后点击右上角用户名
2. 进入"个人主页"
3. 点击"接口 TOKEN"
4. 复制 Token（类似：`abc123def456...`）

### 3. 积分说明

- **注册赠送**: 100 积分
- **基础数据**: 20-50 积分/接口
- **提升积分**: 
  - 完善资料 +100
  - 每日签到 +5
  - 充值（1 元=10 积分）
  - 贡献代码/文档

### 4. 推荐配置

**最低配置**（100 积分）:
- 股票基本信息（20 积分）
- 实时行情（20 积分）
- 历史行情（50 积分）

**推荐配置**（500+ 积分）:
- 基础数据（100 积分）
- 行情数据（200 积分）
- 财务数据（200 积分）

---

## 🔧 安装与配置

### 1. 安装 Tushare

```bash
pip3 install tushare
```

### 2. 配置 Token

**方式 1: 代码中配置**
```python
import tushare as ts

ts.set_token('your_token_here')
pro = ts.pro_api()
```

**方式 2: 配置文件**
```bash
# 创建 ~/.tushare_token 文件
echo "your_token_here" > ~/.tushare_token
```

```python
# 读取配置
with open('~/.tushare_token', 'r') as f:
    token = f.read().strip()
ts.set_token(token)
```

**方式 3: 环境变量**
```bash
export TUSHARE_TOKEN="your_token_here"
```

```python
import os
token = os.environ.get('TUSHARE_TOKEN')
ts.set_token(token)
```

---

## 📊 常用接口

### 1. 股票列表

```python
import tushare as ts

ts.set_token('your_token')
pro = ts.pro_api()

# 获取 A 股列表
data = pro.stock_basic(
    exchange='',
    list_status='L',
    fields='ts_code,symbol,name,area,industry,list_date'
)

print(f"获取 {len(data)} 只股票")
print(data.head())
```

### 2. 实时行情

```python
# 获取实时行情
data = pro.quote_daily(
    ts_code='600519.SH',
    start_date='20260322',
    end_date='20260322'
)

print(data)
```

### 3. 历史行情

```python
# 获取历史 K 线
data = pro.daily(
    ts_code='600519.SH',
    start_date='20260301',
    end_date='20260322'
)

print(f"获取 {len(data)} 条 K 线")
```

### 4. 财务数据

```python
# 获取财务指标
data = pro.fina_indicator(
    ts_code='600519.SH',
    start_date='20250101',
    end_date='20260322'
)

print(data[['end_date', 'roe', 'eps', 'pe_ttm']])
```

### 5. 资金流

```python
# 获取个股资金流
data = pro.moneyflow(
    ts_code='600519.SH',
    start_date='20260322',
    end_date='20260322'
)

print(data[['buy_sm_amount', 'sell_sm_amount', 'net_mf_amount']])
```

---

## 🔗 集成到工作流

### 创建 Tushare 数据源模块

```python
# tushare_source.py
import tushare as ts
from pathlib import Path

class TushareSource:
    """Tushare Pro 数据源"""
    
    def __init__(self, token: str = None):
        if not token:
            # 从文件读取
            token_file = Path.home() / '.tushare_token'
            if token_file.exists():
                token = token_file.read_text().strip()
            else:
                raise ValueError("未配置 Tushare token")
        
        ts.set_token(token)
        self.pro = ts.pro_api()
    
    def get_stock_list(self) -> List[Dict]:
        """获取股票列表"""
        data = self.pro.stock_basic(
            exchange='',
            list_status='L',
            fields='ts_code,symbol,name,area,industry'
        )
        
        return [
            {
                'code': row['symbol'],
                'name': row['name'],
                'ts_code': row['ts_code'],
                'industry': row['industry'],
                'source': 'tushare',
            }
            for _, row in data.iterrows()
        ]
    
    def get_realtime_quotes(self, codes: List[str]) -> List[Dict]:
        """获取实时行情"""
        all_quotes = []
        
        for code in codes:
            ts_code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
            
            data = self.pro.quote_daily(
                ts_code=ts_code,
                start_date=datetime.now().strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d')
            )
            
            if len(data) > 0:
                all_quotes.append({
                    'code': code,
                    'price': data.iloc[0]['close'],
                    'change_pct': data.iloc[0]['pct_chg'],
                    'volume': data.iloc[0]['vol'],
                    'source': 'tushare',
                })
        
        return all_quotes
    
    def get_main_flow(self, top_n: int = 50) -> List[Dict]:
        """获取主力净流入排名"""
        # 获取全市场资金流
        data = self.pro.moneyflow(
            start_date=datetime.now().strftime('%Y%m%d'),
            end_date=datetime.now().strftime('%Y%m%d')
        )
        
        # 按主力净流入排序
        data = data.sort_values('net_mf_amount', ascending=False)
        
        return [
            {
                'code': row['ts_code'][:6],
                'name': '',  # 需要关联股票列表
                'main_flow': row['net_mf_amount'] / 10000,  # 万
                'source': 'tushare',
            }
            for _, row in data.head(top_n).iterrows()
        ]
```

---

## 📊 积分优化建议

### 免费获取积分

1. **完善资料** (+100 积分)
   - 填写个人信息
   - 验证手机号

2. **每日签到** (+5 积分/天)
   - 访问 https://tushare.pro/user/checkin
   - 连续签到有额外奖励

3. **贡献代码** (+50-200 积分)
   - 提交 PR 到 Tushare GitHub
   - 贡献数据源接口

4. **帮助他人** (+10-50 积分)
   - 回答社区问题
   - 分享使用经验

### 付费充值

- **价格**: 1 元 = 10 积分
- **推荐**: 首充 50 元（500 积分）
- **用途**: 获取更高级数据接口

---

## 🎯 推荐配置方案

### 方案 1: 免费用户（100 积分）

**适用**: 个人学习、小规模使用

**接口**:
- 股票基本信息（20 积分）
- 实时行情（20 积分）
- 历史行情（50 积分，限 100 次/天）

**限制**:
- 调用次数有限
- 数据更新延迟

### 方案 2: 进阶用户（500 积分）

**适用**: 量化交易、中等规模使用

**接口**:
- 基础数据（100 积分）
- 行情数据（200 积分）
- 财务数据（200 积分）

**优势**:
- 调用次数充足
- 数据更新及时

### 方案 3: 专业用户（2000+ 积分）

**适用**: 机构、大规模使用

**接口**:
- 全量接口
- Level-2 行情
- 高频数据

**优势**:
- 无调用限制
- 实时数据

---

## 📁 配置文件

### tushare_config.json

```json
{
  "token": "your_token_here",
  "api_url": "https://api.tushare.pro",
  "timeout": 10,
  "retry_times": 3,
  "cache_dir": "~/.cache/tushare",
  "rate_limit": {
    "per_minute": 60,
    "per_day": 500
  }
}
```

### 使用配置

```python
import json
from pathlib import Path

def load_tushare_config():
    config_file = Path(__file__).parent / 'tushare_config.json'
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config['token']
    else:
        print("❌ 未找到 Tushare 配置文件")
        print("请创建 tushare_config.json 并配置 token")
        return None
```

---

## 🔍 验证配置

```python
def test_tushare_config():
    """测试 Tushare 配置"""
    token = load_tushare_config()
    
    if not token:
        return False
    
    try:
        import tushare as ts
        ts.set_token(token)
        pro = ts.pro_api()
        
        # 测试获取股票列表
        data = pro.stock_basic(exchange='', list_status='L')
        
        if len(data) > 0:
            print(f"✅ Tushare 配置成功")
            print(f"   获取到 {len(data)} 只股票")
            return True
        else:
            print("❌ Tushare 返回空数据")
            return False
            
    except Exception as e:
        print(f"❌ Tushare 测试失败：{e}")
        return False
```

---

## 📞 技术支持

- **官方文档**: https://tushare.pro/document/1
- **社区论坛**: https://tushare.pro/user/comment
- **GitHub**: https://github.com/waditu/tushare
- **QQ 群**: 288644319

---

**状态**: 📝 需申请 token  
**推荐**: 注册并配置 Tushare Pro 以获得稳定数据源

---

_📋 Tushare Pro 配置指南_  
_🔑 稳定数据源 | 📊 专业金融数据 | 🚀 推荐配置_
