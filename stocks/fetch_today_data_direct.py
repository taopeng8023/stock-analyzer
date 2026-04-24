#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Tushare 获取今日（2026-03-30）收盘后交易数据

Token: a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

# 配置
TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
LOG_DIR = Path('/home/admin/.openclaw/workspace/stocks/logs')

# 今日日期
TODAY = '20260330'

print("=" * 80)
print("Tushare 今日数据获取")
print("=" * 80)
print(f"Token: {TUSHARE_TOKEN[:20]}...")
print(f"目标日期：{TODAY}")
print(f"数据目录：{DATA_DIR}")
print()

# API 地址
api_url = 'http://api.tushare.pro'

# 1. 获取股票列表
print("[1/3] 获取股票列表...")
stock_payload = {
    'api_name': 'stock_basic',
    'token': TUSHARE_TOKEN,
    'params': {'list_status': 'L'},
    'fields': ''
}

try:
    resp = requests.post(api_url, json=stock_payload, timeout=60)
    result = resp.json()
    
    if result.get('code') != 0:
        print(f"❌ 获取股票列表失败：{result.get('msg')}")
        exit(1)
    
    data = result.get('data')
    if data and 'items' in data:
        fields = data.get('fields', [])
        items = data.get('items', [])
        
        stocks = []
        for item in items:
            record = dict(zip(fields, item))
            ts_code = record.get('ts_code', '')
            if ts_code:
                stocks.append({
                    'ts_code': ts_code,
                    'symbol': ts_code.split('.')[0]
                })
        
        print(f"   股票总数：{len(stocks)} 只")
    else:
        print("❌ 未获取到股票列表")
        exit(1)
        
except Exception as e:
    print(f"❌ 异常：{e}")
    exit(1)

# 2. 获取今日数据
print(f"\n[2/3] 获取 {TODAY} 行情数据...")
print("   预计耗时：30-60 分钟")
print()

success = 0
exists = 0
fail = 0
no_data = 0
last_request = 0

start_time = time.time()

for i, stock in enumerate(stocks):
    ts_code = stock['ts_code']
    symbol = stock['symbol']
    filepath = DATA_DIR / f'{symbol}.json'
    
    # 频率限制（每 1.2 秒一次）
    now = time.time()
    if now - last_request < 1.2:
        time.sleep(1.2 - (now - last_request))
    last_request = time.time()
    
    # 获取今日数据
    daily_payload = {
        'api_name': 'daily',
        'token': TUSHARE_TOKEN,
        'params': {
            'ts_code': ts_code,
            'start_date': TODAY,
            'end_date': TODAY
        },
        'fields': ''
    }
    
    try:
        resp = requests.post(api_url, json=daily_payload, timeout=30)
        result = resp.json()
        
        if result.get('code') != 0:
            fail += 1
            continue
        
        data = result.get('data')
        if not data or 'items' not in data or not data['items']:
            no_data += 1
            continue
        
        # 解析数据
        fields = data.get('fields', [])
        item = data['items'][0]
        record = dict(zip(fields, item))
        
        new_data = {
            '日期': str(record.get('trade_date', '')),
            '开盘': float(record.get('open', 0)),
            '收盘': float(record.get('close', 0)),
            '最高': float(record.get('high', 0)),
            '最低': float(record.get('low', 0)),
            '成交量': float(record.get('vol', 0)) * 100,
            '成交额': float(record.get('amount', 0)) * 1000,
            '涨跌幅': float(record.get('pct_chg', 0))
        }
        
        # 读取现有数据
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # 检查是否已存在
            existing_dates = [d['日期'] for d in existing_data]
            if new_data['日期'] in existing_dates:
                exists += 1
                continue
            
            # 追加数据
            existing_data.append(new_data)
            existing_data.sort(key=lambda x: x['日期'])
            
            # 保存
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
        else:
            # 新文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump([new_data], f, ensure_ascii=False, indent=2)
        
        success += 1
        
        # 进度
        if (i + 1) % 500 == 0:
            elapsed = time.time() - start_time
            print(f"   进度：{i+1}/{len(stocks)} (成功:{success} 已存在:{exists} 无数据:{no_data} 失败:{fail}) 耗时:{elapsed:.0f}s")
    
    except Exception as e:
        fail += 1

elapsed = time.time() - start_time

# 3. 完成统计
print()
print("=" * 80)
print("执行完成")
print("=" * 80)
print(f"   股票总数：{len(stocks)} 只")
print(f"   成功更新：{success} 只")
print(f"   已存在：{exists} 只")
print(f"   无数据：{no_data} 只")
print(f"   失败：{fail} 只")
print(f"   总耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
print("=" * 80)

# 保存报告
report = {
    'date': TODAY,
    'time': datetime.now().isoformat(),
    'data_source': 'Tushare',
    'token': TUSHARE_TOKEN[:20] + '...',
    'summary': {
        'total': len(stocks),
        'success': success,
        'exists': exists,
        'no_data': no_data,
        'fail': fail
    },
    'elapsed': elapsed
}

report_file = LOG_DIR / f'update_report_{TODAY}_tushare.json'
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\n💾 报告已保存：{report_file}")
print()
print("✅ 今日数据获取完成！")

# 验证最新数据
print("\n验证数据...")
test_file = DATA_DIR / '000001.json'
if test_file.exists():
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"   000001 最新日期：{data[-1]['日期']}")
    if data[-1]['日期'] == TODAY:
        print(f"   ✅ 今日数据已更新")
    else:
        print(f"   ⚠️ 最新数据：{data[-1]['日期']}")
