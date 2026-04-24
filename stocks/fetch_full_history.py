#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取全市场股票历史行情数据 (2022-2026 年)

特点:
1. 数据包含完整的字段说明，方便理解
2. 单独存储，和现有数据区分开
3. 处理 Tushare API 频率限制 (每分钟 50 次)
4. 支持断点续传

用法:
    python3 fetch_full_history.py                    # 获取全量数据
    python3 fetch_full_history.py --limit 100        # 测试模式
    python3 fetch_full_history.py --check            # 检查进度
"""

import json
import time
import os
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Tushare Token
TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'

# 数据目录 (新目录，和现有 data_tushare 区分)
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/fetch_history.log')
DATA_DIR.mkdir(exist_ok=True)

# API
api_url = 'http://api.tushare.pro'

# 字段说明 (中文)
FIELD_DESCRIPTIONS = {
    'ts_code': '股票代码 (如 000001.SZ)',
    'trade_date': '交易日期 (YYYYMMDD 格式)',
    'open': '开盘价 (元)',
    'high': '最高价 (元)',
    'low': '最低价 (元)',
    'close': '收盘价 (元)',
    'pre_close': '昨收价 (元)',
    'change': '涨跌额 (元)',
    'pct_chg': '涨跌幅 (%)',
    'vol': '成交量 (手)',
    'amount': '成交额 (千元)'
}

def log(msg: str):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f'[{timestamp}] {msg}'
    print(log_line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')

def load_stock_list() -> List[Dict]:
    """加载股票列表"""
    cache_file = DATA_DIR / 'stock_list.json'
    csv_file = Path('/home/admin/.openclaw/workspace/stocks/all_stocks_list.csv')
    
    if cache_file.exists():
        log(f'从缓存加载股票列表：{cache_file}')
        with open(cache_file, 'r', encoding='utf-8') as f:
            stock_list = json.load(f)
        log(f'加载到 {len(stock_list)} 只股票')
        return stock_list
    
    if csv_file.exists():
        import csv
        stocks = []
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = 'ts_code' if 'ts_code' in row else list(row.keys())[0]
                ts_code = row[key].strip()
                stocks.append({'ts_code': ts_code})
        log(f'从 CSV 加载 {len(stocks)} 只股票')
        
        # 缓存
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
        
        return stocks
    
    log('❌ 未找到股票列表文件')
    return []

def fetch_daily_data(ts_code: str, start_date: str, end_date: str, retry_count: int = 3) -> Optional[Dict]:
    """
    获取单只股票日线数据 (带限流重试)
    
    返回格式:
    {
        'description': {字段说明},
        'fields': [字段列表],
        'items': [数据列表],
        'fetch_time': '获取时间'
    }
    """
    payload = {
        'api_name': 'daily',
        'token': TUSHARE_TOKEN,
        'params': {'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
        'fields': ''
    }
    
    for attempt in range(retry_count):
        try:
            resp = requests.post(api_url, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') != 0:
                error_msg = result.get('msg', '')
                # 检查是否限流
                if '每分钟最多' in error_msg or '限流' in error_msg:
                    if attempt < retry_count - 1:
                        wait_time = 65
                        log(f'⚠️ 限流，等待 {wait_time} 秒后重试...')
                        time.sleep(wait_time)
                        continue
                return None, error_msg
            
            data = result.get('data')
            if data and 'items' in data:
                # 构建带说明的数据结构
                result_data = {
                    'description': 'A股日线行情数据 (Tushare API)',
                    'fields_description': FIELD_DESCRIPTIONS,
                    'symbol': ts_code,
                    'date_range': f'{start_date} ~ {end_date}',
                    'fields': data['fields'],
                    'items': data['items'],
                    'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'record_count': len(data['items'])
                }
                return result_data, None
            return None, "No data"
        
        except Exception as e:
            if attempt < retry_count - 1:
                time.sleep(1)
                continue
            return None, str(e)
    
    return None, "Max retries exceeded"

def save_data(ts_code: str, data: Dict) -> Path:
    """保存数据到 JSON 文件"""
    code_part = ts_code.split('.')[0]
    filepath = DATA_DIR / f'{code_part}.json'
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

def get_progress() -> Dict:
    """获取进度"""
    completed = list(DATA_DIR.glob('*.json'))
    # 排除 stock_list.json
    completed = [f for f in completed if f.name != 'stock_list.json']
    return {
        'completed': len(completed),
        'files': [f.stem for f in completed[:10]]
    }

def fetch_all_stocks(start_date: str, end_date: str, limit: int = None):
    """
    批量获取历史数据
    
    Args:
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        limit: 限制获取股票数量 (测试用)
    """
    log('=' * 80)
    log(f'📊 获取全市场历史数据：{start_date} ~ {end_date}')
    log(f'📁 数据目录：{DATA_DIR}')
    log('=' * 80)
    
    stock_list = load_stock_list()
    if not stock_list:
        log('❌ 无法加载股票列表')
        return
    
    if limit:
        stock_list = stock_list[:limit]
        log(f'测试模式：仅获取前 {limit} 只')
    
    log(f'计划获取 {len(stock_list)} 只股票')
    
    start_time = time.time()
    success_count = 0
    fail_count = 0
    
    for i, stock in enumerate(stock_list):
        ts_code = stock.get('ts_code', '')
        symbol = ts_code.split('.')[0]
        
        # 检查是否已获取
        filepath = DATA_DIR / f'{symbol}.json'
        if filepath.exists():
            success_count += 1
            if i % 500 == 0:
                log(f'[{i+1}/{len(stock_list)}] {ts_code} - 已存在，跳过')
            continue
        
        if i % 100 == 0:
            elapsed = time.time() - start_time
            log(f'进度：{i+1}/{len(stock_list)} (成功:{success_count} 失败:{fail_count} 耗时:{elapsed:.1f}秒)')
        
        # 获取数据
        result, error = fetch_daily_data(ts_code, start_date, end_date)
        
        if result and result.get('items'):
            save_data(ts_code, result)
            success_count += 1
            item_count = result.get('record_count', len(result['items']))
            if i % 100 == 0:
                log(f'[{i+1}/{len(stock_list)}] {ts_code} - 获取成功 ({item_count} 条)')
        else:
            fail_count += 1
            if i % 500 == 0:
                log(f'[{i+1}/{len(stock_list)}] {ts_code} - 失败：{error}')
        
        # 频率控制：每分钟最多 50 次 = 每 1.2 秒一次
        time.sleep(1.2)
    
    elapsed = time.time() - start_time
    log('=' * 80)
    log('📊 获取完成')
    log(f'总计：{len(stock_list)} 只')
    log(f'成功：{success_count} 只')
    log(f'失败：{fail_count} 只')
    log(f'耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)')
    log(f'数据目录：{DATA_DIR}')
    log('=' * 80)

def create_readme():
    """创建数据说明文件"""
    readme = DATA_DIR / 'README.md'
    content = f'''# A股历史行情数据 (2022-2026)

## 数据来源
- 接口：Tushare daily 接口
- 时间范围：2022-01-01 ~ 2026-12-31 (或当前最新日期)
- 获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 文件结构
每个股票一个 JSON 文件，文件名为股票代码（如 `000001.json`）

## 数据格式

```json
{{
  "description": "A股日线行情数据 (Tushare API)",
  "fields_description": {{
    "ts_code": "股票代码 (如 000001.SZ)",
    "trade_date": "交易日期 (YYYYMMDD 格式)",
    "open": "开盘价 (元)",
    "high": "最高价 (元)",
    "low": "最低价 (元)",
    "close": "收盘价 (元)",
    "pre_close": "昨收价 (元)",
    "change": "涨跌额 (元)",
    "pct_chg": "涨跌幅 (%)",
    "vol": "成交量 (手)",
    "amount": "成交额 (千元)"
  }},
  "symbol": "000001.SZ",
  "date_range": "20220101 ~ 20261231",
  "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"],
  "items": [
    ["000001.SZ", "20220104", 11.64, 11.88, 11.47, 11.82, 11.66, 0.16, 1.3722, 68667.66, 80559.923],
    ...
  ],
  "fetch_time": "2026-04-09 15:30:00",
  "record_count": 1000
}}
```

## 字段说明

| 字段 | 说明 | 单位 |
|------|------|------|
| ts_code | 股票代码 | 格式：代码.交易所 |
| trade_date | 交易日期 | YYYYMMDD |
| open | 开盘价 | 元 |
| high | 最高价 | 元 |
| low | 最低价 | 元 |
| close | 收盘价 | 元 |
| pre_close | 昨收价 | 元 |
| change | 涨跌额 | 元 |
| pct_chg | 涨跌幅 | % |
| vol | 成交量 | 手 |
| amount | 成交额 | 千元 |

## 注意事项

1. **数据完整性**：部分股票可能因退市、暂停交易等原因数据不完整
2. **数据延迟**：Tushare 数据通常 T+1 更新
3. **频率限制**：API 每分钟最多 50 次请求

## 使用示例

```python
import json

# 读取数据
with open('000001.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 获取字段说明
print(data['fields_description'])

# 获取数据
fields = data['fields']
items = data['items']

# 转换为 DataFrame
import pandas as pd
df = pd.DataFrame(items, columns=fields)
```

## 更新日志

- 2026-04-09: 初始获取
'''
    
    with open(readme, 'w', encoding='utf-8') as f:
        f.write(content)
    
    log(f'📄 创建说明文件：{readme}')

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='获取全市场历史行情数据 (2022-2026)')
    parser.add_argument('--limit', type=int, help='限制获取股票数量 (测试用)')
    parser.add_argument('--check', action='store_true', help='检查进度')
    
    args = parser.parse_args()
    
    if args.check:
        progress = get_progress()
        log(f'已完成：{progress["completed"]} 只股票')
        log(f'示例：{", ".join(progress["files"])}...')
        return
    
    # 创建说明文件
    create_readme()
    
    # 获取 2022-2026 年数据
    start_date = '20220101'
    end_date = '20261231'
    
    fetch_all_stocks(start_date, end_date, limit=args.limit)

if __name__ == '__main__':
    main()