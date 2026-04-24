#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从本地文件列表更新股票数据到 2026-04-07

不使用 Tushare 股票列表接口（避免频率限制）
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

# 日期范围
START_DATE = '20260403'
END_DATE = '20260407'

# API
api_url = 'http://api.tushare.pro'

print("=" * 80)
print("股票数据批量更新 - 从本地文件列表")
print("=" * 80)
print(f"日期范围：{START_DATE} ~ {END_DATE}")
print()

# 从本地文件获取股票列表
print("[1/4] 读取本地股票文件...")
files = list(DATA_DIR.glob('*.json'))
stocks = []
for f in files:
    symbol = f.stem
    # 转换为 Tushare 格式
    if symbol.startswith('6'):
        ts_code = f'{symbol}.SH'
    elif symbol.startswith('0') or symbol.startswith('3'):
        ts_code = f'{symbol}.SZ'
    else:
        ts_code = f'{symbol}.BJ'
    
    stocks.append({
        'symbol': symbol,
        'ts_code': ts_code
    })

print(f"   本地文件数：{len(stocks)} 只")

# 检查需要更新的股票
print(f"\n[2/4] 筛选需要更新的股票...")

need_update = []
already_latest = 0

for stock in stocks:
    symbol = stock['symbol']
    filepath = DATA_DIR / f'{symbol}.json'
    
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data:
            latest_date = data[-1]['日期']
            if latest_date < END_DATE:
                need_update.append(stock)
            else:
                already_latest += 1

print(f"   需要更新：{len(need_update)} 只")
print(f"   已是最新：{already_latest} 只")

# 批量获取数据
print(f"\n[3/4] 获取 {START_DATE} ~ {END_DATE} 数据...")
print("   分批执行，每批 500 只")
print()

success = 0
no_data = 0
fail = 0
last_request = 0
start_time = time.time()

# 分批处理
batch_size = 500
total_batches = (len(need_update) + batch_size - 1) // batch_size

for batch_idx in range(total_batches):
    batch_start = batch_idx * batch_size
    batch_end = min((batch_idx + 1) * batch_size, len(need_update))
    batch_stocks = need_update[batch_start:batch_end]
    
    print(f"批次 {batch_idx+1}/{total_batches} ({batch_start+1}-{batch_end}):")
    
    for stock in batch_stocks:
        ts_code = stock['ts_code']
        symbol = stock['symbol']
        filepath = DATA_DIR / f'{symbol}.json'
        
        # 频率限制
        now = time.time()
        if now - last_request < 0.5:
            time.sleep(0.5 - (now - last_request))
        last_request = time.time()
        
        # 获取数据
        daily_payload = {
            'api_name': 'daily',
            'token': TUSHARE_TOKEN,
            'params': {
                'ts_code': ts_code,
                'start_date': START_DATE,
                'end_date': END_DATE
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
            items = data.get('items', [])
            
            new_records = []
            for item in items:
                record = dict(zip(fields, item))
                new_records.append({
                    '日期': str(record.get('trade_date', '')),
                    '开盘': float(record.get('open', 0)),
                    '收盘': float(record.get('close', 0)),
                    '最高': float(record.get('high', 0)),
                    '最低': float(record.get('low', 0)),
                    '成交量': float(record.get('vol', 0)) * 100,
                    '成交额': float(record.get('amount', 0)) * 1000,
                    '涨跌幅': float(record.get('pct_chg', 0))
                })
            
            # 合并数据
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                existing_dates = {d['日期'] for d in existing_data}
                
                for rec in new_records:
                    if rec['日期'] not in existing_dates:
                        existing_data.append(rec)
                
                existing_data.sort(key=lambda x: x['日期'])
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(new_records, f, ensure_ascii=False, indent=2)
            
            success += 1
        
        except Exception as e:
            fail += 1
    
    elapsed = time.time() - start_time
    print(f"  完成：{batch_end}/{len(need_update)} (成功:{success} 无数据:{no_data} 失败:{fail}) 耗时:{elapsed:.0f}s")
    print()

elapsed = time.time() - start_time

# 完成统计
print("=" * 80)
print("执行完成")
print("=" * 80)
print(f"   成功更新：{success} 只")
print(f"   无数据：{no_data} 只")
print(f"   失败：{fail} 只")
print(f"   已是最新：{already_latest} 只")
print(f"   总耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
print("=" * 80)

# 保存报告
report = {
    'date': datetime.now().isoformat(),
    'period': f'{START_DATE} ~ {END_DATE}',
    'summary': {
        'total_files': len(stocks),
        'need_update': len(need_update),
        'success': success,
        'no_data': no_data,
        'fail': fail,
        'already_latest': already_latest
    },
    'elapsed': elapsed
}

report_file = LOG_DIR / f'update_batch1_{END_DATE}.json'
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\n💾 报告已保存：{report_file}")

# 验证
print("\n验证数据...")
test_files = ['000001.json', '600519.json', '300750.json', '601318.json']
for name in test_files:
    f = DATA_DIR / name
    if f.exists():
        with open(f, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        print(f"   {name}: {len(data)}条，最新：{data[-1]['日期']}")

# 统计今日数据
print("\n统计今日数据...")
today_count = 0
for f in DATA_DIR.glob('*.json'):
    with open(f, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    if data and data[-1]['日期'] == END_DATE:
        today_count += 1

print(f"   今日 ({END_DATE}) 数据：{today_count} 只")
print()
print("✅ 数据更新完成！")
