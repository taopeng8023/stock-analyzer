#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能补充 A 股历史数据
只获取缺失的股票数据，不重复获取已有的数据

A 股市场约 5300 只股票：
- 深市主板：000001-002999
- 创业板：300001-301999  
- 沪市主板：600000-603999
- 科创板：688001-688999
- 北交所：8xxxxx
"""

import json
import time
import os
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Tushare Token
TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
DATA_DIR.mkdir(exist_ok=True)

# 日志目录
LOG_DIR = Path('/home/admin/.openclaw/workspace/stocks/logs')
LOG_DIR.mkdir(exist_ok=True)


def generate_all_a_share_codes():
    """生成全量 A 股代码列表（约 5300 只）"""
    codes = []
    
    # 深市主板：000001-002999
    for code in range(1, 3000):
        symbol = f'{code:06d}'
        codes.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '深市主板'})
    
    # 创业板：300001-301999
    for code in range(300001, 302000):
        symbol = f'{code:06d}'
        codes.append({'ts_code': f'{symbol}.SZ', 'symbol': symbol, 'market': '创业板'})
    
    # 沪市主板：600000-603999
    for code in range(600000, 604000):
        symbol = f'{code:06d}'
        codes.append({'ts_code': f'{symbol}.SH', 'symbol': symbol, 'market': '沪市主板'})
    
    # 科创板：688001-688999
    for code in range(688001, 689000):
        symbol = f'{code:06d}'
        codes.append({'ts_code': f'{symbol}.SH', 'symbol': symbol, 'market': '科创板'})
    
    # 北交所：800000-899999
    for code in range(800000, 900000):
        symbol = f'{code:06d}'
        codes.append({'ts_code': f'{symbol}.BJ', 'symbol': symbol, 'market': '北交所'})
    
    return codes


def get_existing_symbols():
    """获取已存在的股票代码"""
    existing = set()
    for f in DATA_DIR.glob('*.json'):
        symbol = f.stem
        existing.add(symbol)
    return existing


def check_data_quality(symbol):
    """检查数据质量，返回是否需要重新获取"""
    filepath = DATA_DIR / f'{symbol}.json'
    
    if not filepath.exists():
        return 'missing'
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if len(data) == 0:
            return 'empty'
        
        if len(data) < 200:  # 数据不足
            return 'incomplete'
        
        # 检查日期范围
        dates = [d['日期'] for d in data]
        min_date = min(dates)
        max_date = max(dates)
        
        # 如果数据不足一年，需要补充
        if len(data) < 240:
            return 'incomplete'
        
        return 'complete'
        
    except Exception as e:
        return f'error:{e}'


def fetch_daily_data(ts_code, start_date, end_date):
    """获取日线数据"""
    api_url = 'http://api.tushare.pro'
    
    payload = {
        'api_name': 'daily',
        'token': TUSHARE_TOKEN,
        'params': {
            'ts_code': ts_code,
            'start_date': start_date,
            'end_date': end_date
        },
        'fields': ''
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=30)
        resp.raise_for_status()
        
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
        print(f'请求失败：{e}')
        return None


def save_data(symbol, data):
    """保存数据"""
    filepath = DATA_DIR / f'{symbol}.json'
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 80)
    print("📊 智能补充 A 股历史数据")
    print("=" * 80)
    
    # 生成全量代码列表
    print("\n生成全量 A 股代码列表...")
    all_codes = generate_all_a_share_codes()
    print(f"   全量代码数：{len(all_codes)} 只")
    
    # 获取已存在的股票
    existing = get_existing_symbols()
    print(f"   已存在数据：{len(existing)} 只")
    
    # 找出缺失的股票
    missing = []
    incomplete = []
    
    print("\n检查数据完整性...")
    for stock in all_codes:
        symbol = stock['symbol']
        status = check_data_quality(symbol)
        
        if status == 'missing':
            missing.append(stock)
        elif status in ['empty', 'incomplete']:
            incomplete.append(stock)
    
    print(f"   缺失股票：{len(missing)} 只")
    print(f"   不完整：{len(incomplete)} 只")
    
    # 合并需要获取的股票
    to_fetch = missing + incomplete
    print(f"   需要获取：{len(to_fetch)} 只")
    
    if len(to_fetch) == 0:
        print("\n✅ 所有股票数据已完整！")
        return
    
    # 设置日期范围
    start_date = '20250327'
    end_date = '20260327'
    
    print(f"\n日期范围：{start_date} ~ {end_date}")
    print("=" * 80)
    print("\n开始获取数据...\n")
    
    # 获取数据
    success = 0
    fail = 0
    skip = 0
    
    start_time = time.time()
    last_request = 0
    
    for i, stock in enumerate(to_fetch, 1):
        ts_code = stock['ts_code']
        symbol = stock['symbol']
        market = stock['market']
        
        # 频率限制：每 2 秒一次
        now = time.time()
        elapsed = now - last_request
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
        last_request = time.time()
        
        # 获取数据
        data = fetch_daily_data(ts_code, start_date, end_date)
        
        if data and len(data) > 0:
            save_data(symbol, data)
            success += 1
            if i % 100 == 0:
                elapsed_total = time.time() - start_time
                print(f"[{i}/{len(to_fetch)}] {symbol} ({market}) - ✅ 成功 ({len(data)}条) "
                      f"[累计：{success}成功/{fail}失败] 耗时:{elapsed_total:.1f}s")
        else:
            fail += 1
            if i % 100 == 0:
                print(f"[{i}/{len(to_fetch)}] {symbol} ({market}) - ❌ 失败 "
                      f"[累计：{success}成功/{fail}失败]")
        
        # 每 500 只休息一下
        if i % 500 == 0:
            print(f"\n💤 休息 5 秒...")
            time.sleep(5)
    
    # 完成统计
    elapsed_total = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("📊 获取完成")
    print("=" * 80)
    print(f"   需要获取：{len(to_fetch)} 只")
    print(f"   成功：{success} 只")
    print(f"   失败：{fail} 只")
    print(f"   总耗时：{elapsed_total:.1f}秒 ({elapsed_total/60:.1f}分钟)")
    print(f"   平均速度：{len(to_fetch)/elapsed_total:.2f}只/秒")
    print("=" * 80)
    
    # 最终统计
    final_existing = len(get_existing_symbols())
    print(f"\n当前数据文件总数：{final_existing} 只")
    
    # 保存报告
    report = {
        'time': datetime.now().isoformat(),
        'start_date': start_date,
        'end_date': end_date,
        'summary': {
            'all_codes': len(all_codes),
            'existing_before': len(existing),
            'missing': len(missing),
            'incomplete': len(incomplete),
            'to_fetch': len(to_fetch),
            'success': success,
            'fail': fail,
            'existing_after': final_existing
        }
    }
    
    report_file = LOG_DIR / f'fetch_missing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 报告已保存：{report_file}")


if __name__ == '__main__':
    main()
