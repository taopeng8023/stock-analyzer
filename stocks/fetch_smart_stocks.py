#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能获取 A 股全量数据
1. 先从 Tushare 获取真实存在的股票列表
2. 只获取缺失的股票数据
"""

import json
import time
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


def get_stock_list():
    """从 Tushare 获取真实存在的股票列表"""
    api_url = 'http://api.tushare.pro'
    payload = {
        'api_name': 'stock_basic',
        'token': TUSHARE_TOKEN,
        'params': {
            'exchange': '',
            'list_status': 'L',  # 只获取正常上市的股票
        },
        'fields': ''
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=60)
        result = resp.json()
        
        if result.get('code') != 0:
            print(f"API 错误：{result.get('msg')}")
            return None
        
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
                        'symbol': ts_code.split('.')[0],
                        'name': record.get('name', ''),
                        'exchange': record.get('exchange', '')
                    })
            
            return stocks
        
        return None
        
    except Exception as e:
        print(f"请求失败：{e}")
        return None


def get_existing_symbols():
    """获取已存在的股票代码"""
    existing = set()
    for f in DATA_DIR.glob('*.json'):
        existing.add(f.stem)
    return existing


def check_data_quality(symbol):
    """检查数据质量"""
    filepath = DATA_DIR / f'{symbol}.json'
    
    if not filepath.exists():
        return 'missing'
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if len(data) == 0:
            return 'empty'
        
        if len(data) >= 240:  # 一年约 240 个交易日
            return 'complete'
        
        return 'incomplete'
        
    except:
        return 'error'


def fetch_daily_data(ts_code, start_date, end_date):
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
    print("📊 智能获取 A 股全量数据")
    print("=" * 80)
    
    # 1. 获取真实股票列表
    print("\n[1/4] 获取真实股票列表...")
    stocks = get_stock_list()
    
    if not stocks:
        print("❌ 获取股票列表失败，使用备用方案")
        # 备用方案：使用已存在的数据推断
        existing = get_existing_symbols()
        print(f"   已存在数据：{len(existing)} 只")
        print("   跳过股票列表获取，直接检查现有数据")
        return
    
    print(f"   真实股票数：{len(stocks)} 只")
    
    # 2. 检查现有数据
    print("\n[2/4] 检查现有数据...")
    existing = get_existing_symbols()
    print(f"   已存在文件：{len(existing)} 只")
    
    # 3. 找出缺失的
    print("\n[3/4] 识别缺失股票...")
    missing = []
    incomplete = []
    
    for stock in stocks:
        symbol = stock['symbol']
        status = check_data_quality(symbol)
        
        if status == 'missing':
            missing.append(stock)
        elif status in ['empty', 'incomplete']:
            incomplete.append(stock)
    
    print(f"   完全缺失：{len(missing)} 只")
    print(f"   数据不完整：{len(incomplete)} 只")
    
    to_fetch = missing + incomplete
    print(f"   需要获取：{len(to_fetch)} 只")
    
    if not to_fetch:
        print("\n✅ 所有股票数据已完整！")
        return
    
    # 4. 获取数据
    print("\n[4/4] 开始获取数据...")
    print(f"   日期范围：20250327 ~ 20260327")
    print("=" * 80)
    
    start_date = '20250327'
    end_date = '20260327'
    
    success = 0
    fail = 0
    start_time = time.time()
    last_request = 0
    
    for i, stock in enumerate(to_fetch, 1):
        ts_code = stock['ts_code']
        symbol = stock['symbol']
        name = stock.get('name', '')
        
        # 频率限制
        now = time.time()
        if now - last_request < 1.5:
            time.sleep(1.5 - (now - last_request))
        last_request = time.time()
        
        data = fetch_daily_data(ts_code, start_date, end_date)
        
        if data and len(data) > 0:
            filepath = DATA_DIR / f'{symbol}.json'
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            success += 1
            if i % 50 == 0:
                elapsed = time.time() - start_time
                print(f"[{i}/{len(to_fetch)}] {symbol} {name} ✅ ({len(data)}条) [成功:{success} 失败:{fail}] {elapsed:.0f}s")
        else:
            fail += 1
            if i % 100 == 0:
                print(f"[{i}/{len(to_fetch)}] {symbol} {name} ❌ [成功:{success} 失败:{fail}]")
        
        if i % 500 == 0:
            print("\n💤 休息 3 秒...")
            time.sleep(3)
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"📊 获取完成")
    print(f"   需要获取：{len(to_fetch)} 只")
    print(f"   成功：{success} 只")
    print(f"   失败：{fail} 只")
    print(f"   耗时：{elapsed:.0f}s ({elapsed/60:.1f}min)")
    print("=" * 80)
    
    # 最终统计
    final_count = len(list(DATA_DIR.glob('*.json')))
    print(f"\n当前数据文件总数：{final_count} 只")
    
    # 保存报告
    report = {
        'time': datetime.now().isoformat(),
        'summary': {
            'total_stocks': len(stocks),
            'existing_before': len(existing),
            'missing': len(missing),
            'incomplete': len(incomplete),
            'to_fetch': len(to_fetch),
            'success': success,
            'fail': fail,
            'existing_after': final_count
        }
    }
    
    report_file = LOG_DIR / f'fetch_smart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"💾 报告已保存：{report_file}")


if __name__ == '__main__':
    main()
