#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速获取剩余缺失的 A 股数据
直接检查文件是否存在，不检查内容，加快速度
"""

import json
import time
import os
import sys
import requests
from pathlib import Path
from datetime import datetime

# Tushare Token
TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
LOG_DIR = Path('/home/admin/.openclaw/workspace/stocks/logs')
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


def generate_all_codes():
    """生成全量 A 股代码"""
    codes = []
    # 深市主板
    for code in range(1, 3000):
        codes.append(f'{code:06d}.SZ')
    # 创业板
    for code in range(300001, 302000):
        codes.append(f'{code:06d}.SZ')
    # 沪市主板
    for code in range(600000, 604000):
        codes.append(f'{code:06d}.SH')
    # 科创板
    for code in range(688001, 689000):
        codes.append(f'{code:06d}.SH')
    # 北交所
    for code in range(800000, 900000):
        codes.append(f'{code:06d}.BJ')
    return codes


def fetch_data(ts_code, start_date, end_date):
    """获取日线数据"""
    api_url = 'http://api.tushare.pro'
    payload = {
        'api_name': 'daily',
        'token': TUSHARE_TOKEN,
        'params': {'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
        'fields': ''
    }
    try:
        resp = requests.post(api_url, json=payload, timeout=30)
        result = resp.json()
        if result.get('code') != 0:
            return None
        data = result.get('data')
        if data and 'items' in data:
            fields = data.get('fields', [])
            items = data.get('items', [])
            daily_data = []
            for item in items:
                record = dict(zip(fields, item))
                daily_data.append({
                    '日期': str(record.get('trade_date', '')),
                    '开盘': float(record.get('open', 0)),
                    '收盘': float(record.get('close', 0)),
                    '最高': float(record.get('high', 0)),
                    '最低': float(record.get('low', 0)),
                    '成交量': float(record.get('vol', 0)) * 100,
                    '成交额': float(record.get('amount', 0)) * 1000,
                    '涨跌幅': float(record.get('pct_chg', 0)),
                })
            daily_data.sort(key=lambda x: x['日期'])
            return daily_data
        return None
    except Exception as e:
        return None


def main():
    print("=" * 80)
    print("📊 快速获取剩余 A 股数据")
    print("=" * 80)
    
    # 生成代码
    all_codes = generate_all_codes()
    print(f"\n全量代码：{len(all_codes)} 只")
    
    # 找出现有文件
    existing = set()
    for f in DATA_DIR.glob('*.json'):
        existing.add(f.stem)
    print(f"已存在：{len(existing)} 只")
    
    # 找出缺失的
    missing = []
    for ts_code in all_codes:
        symbol = ts_code.split('.')[0]
        if symbol not in existing:
            missing.append(ts_code)
    
    print(f"缺失：{len(missing)} 只")
    print("=" * 80)
    
    if not missing:
        print("\n✅ 所有股票数据已存在！")
        return
    
    # 获取数据
    start_date = '20250327'
    end_date = '20260327'
    
    print(f"\n日期范围：{start_date} ~ {end_date}")
    print("\n开始获取...\n")
    
    success = 0
    fail = 0
    start_time = time.time()
    last_request = 0
    
    for i, ts_code in enumerate(missing, 1):
        symbol = ts_code.split('.')[0]
        
        # 频率限制
        now = time.time()
        if now - last_request < 1.5:
            time.sleep(1.5 - (now - last_request))
        last_request = time.time()
        
        data = fetch_data(ts_code, start_date, end_date)
        
        if data and len(data) > 0:
            filepath = DATA_DIR / f'{symbol}.json'
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            success += 1
            if i % 50 == 0:
                elapsed = time.time() - start_time
                print(f"[{i}/{len(missing)}] {symbol} ✅ ({len(data)}条) [成功:{success} 失败:{fail}] {elapsed:.0f}s")
                sys.stdout.flush()
        else:
            fail += 1
        
        if i % 500 == 0:
            print("\n💤 休息 3 秒...")
            time.sleep(3)
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"完成！成功:{success} 失败:{fail} 耗时:{elapsed:.0f}s ({elapsed/60:.1f}min)")
    print("=" * 80)
    
    # 最终统计
    final_count = len(list(DATA_DIR.glob('*.json')))
    print(f"当前数据文件总数：{final_count} 只")


if __name__ == '__main__':
    main()
