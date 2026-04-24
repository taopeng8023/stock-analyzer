#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
继续获取剩余 A 股历史数据
从 all_stocks_list.csv 读取，检查已获取的股票，续传剩余股票
"""

import json
import time
import os
import csv
import requests
from pathlib import Path
from datetime import datetime

# Tushare Token
TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/fetch_continue.log')
DATA_DIR.mkdir(exist_ok=True)

# 日期范围
START_DATE = '20230101'
END_DATE = '20241231'

# API
api_url = 'http://api.tushare.pro'

def load_stock_list():
    """从 all_stocks_list.csv 加载股票列表"""
    stocks = []
    with open('/home/admin/.openclaw/workspace/stocks/all_stocks_list.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 打印第一行调试
            if len(stocks) == 0:
                print(f"DEBUG: 列名={list(row.keys())}")
            key = 'ts_code' if 'ts_code' in row else list(row.keys())[0]
            stocks.append(row[key].strip())
    return stocks

def is_already_fetched(ts_code):
    """检查股票数据是否已获取"""
    # 转换代码格式：000001.SZ -> 000001_SZ
    code_part = ts_code.split('.')[0]
    market = ts_code.split('.')[1]
    market_short = 'SZ' if market == 'SZ' else 'SH' if market == 'SH' else 'BJ'
    csv_file = DATA_DIR / f"{code_part}_{market_short}.csv"
    return csv_file.exists() and csv_file.stat().st_size > 1000

def fetch_daily_data(ts_code):
    """获取单只股票日线数据"""
    payload = {
        'api_name': 'daily',
        'token': TUSHARE_TOKEN,
        'params': {'ts_code': ts_code, 'start_date': START_DATE, 'end_date': END_DATE},
        'fields': ''
    }
    try:
        resp = requests.post(api_url, json=payload, timeout=30)
        result = resp.json()
        if result.get('code') != 0:
            return None, result.get('msg')
        data = result.get('data')
        if data and 'items' in data:
            fields = data.get('fields', [])
            items = data.get('items', [])
            return {'fields': fields, 'items': items}, None
        return None, "No data"
    except Exception as e:
        return None, str(e)

def save_data(ts_code, data):
    """保存数据到 CSV 和 JSON"""
    code_part = ts_code.split('.')[0]
    market = ts_code.split('.')[1]
    market_short = 'SZ' if market == 'SZ' else 'SH' if market == 'SH' else 'BJ'
    
    fields = data['fields']
    items = data['items']
    
    # 保存 CSV
    csv_file = DATA_DIR / f"{code_part}_{market_short}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'open', 'close', 'high', 'low', 'volume', 'ts_code'])
        for item in items:
            record = dict(zip(fields, item))
            writer.writerow([
                record.get('trade_date', ''),
                record.get('open', 0),
                record.get('close', 0),
                record.get('high', 0),
                record.get('low', 0),
                float(record.get('vol', 0)) * 100,
                ts_code
            ])
    
    # 保存 JSON
    json_file = DATA_DIR / f"{code_part}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({'fields': fields, 'items': items}, f, ensure_ascii=False)
    
    return len(items)

def log(message):
    """日志输出"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')

def main():
    log("=" * 80)
    log("📊 继续获取 A 股历史数据")
    log("=" * 80)
    log(f"日期范围：{START_DATE} ~ {END_DATE}")
    log(f"数据目录：{DATA_DIR}")
    
    # 加载股票列表
    log("\n[1/3] 加载股票列表...")
    all_stocks = load_stock_list()
    log(f"总股票数：{len(all_stocks)}")
    
    # 检查已获取的
    log("\n[2/3] 检查已获取的股票...")
    remaining = []
    for ts_code in all_stocks:
        if not is_already_fetched(ts_code):
            remaining.append(ts_code)
    
    log(f"已获取：{len(all_stocks) - len(remaining)}")
    log(f"剩余：{len(remaining)}")
    
    if not remaining:
        log("\n✅ 所有股票数据已获取完成!")
        return
    
    # 获取剩余股票
    log("\n[3/3] 开始获取剩余股票...")
    success = 0
    failed = 0
    rate_limited = 0
    
    for i, ts_code in enumerate(remaining):
        if i % 10 == 0:
            log(f"进度：{i}/{len(remaining)} ({i*100/len(remaining):.1f}%) - 成功:{success} 失败:{failed}")
        
        data, error = fetch_daily_data(ts_code)
        
        if data:
            rows = save_data(ts_code, data)
            success += 1
            log(f"✓ {ts_code} ({rows}行)")
        else:
            failed += 1
            if '每分钟' in str(error) or '限流' in str(error):
                rate_limited += 1
                log(f"⚠ {ts_code} 限流，等待 65 秒...")
                time.sleep(65)
                # 重试
                data, error = fetch_daily_data(ts_code)
                if data:
                    rows = save_data(ts_code, data)
                    success += 1
                    failed -= 1
                    log(f"✓ {ts_code} 重试成功 ({rows}行)")
            else:
                log(f"✗ {ts_code} 失败：{error}")
        
        # 请求间隔
        time.sleep(0.15)
    
    log("\n" + "=" * 80)
    log("📊 完成!")
    log(f"成功：{success}")
    log(f"失败：{failed}")
    log(f"限流：{rate_limited}")
    log("=" * 80)

if __name__ == '__main__':
    main()
