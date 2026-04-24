#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新历史数据到最新日期

用法:
    python3 update_to_latest.py              # 更新所有股票
    python3 update_to_latest.py --check      # 检查进度
"""

import json
import time
import os
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Tushare Token
TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/update_history.log')

# API
api_url = 'http://api.tushare.pro'

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
    
    if cache_file.exists():
        log(f'从缓存加载股票列表：{cache_file}')
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    csv_file = Path('/home/admin/.openclaw/workspace/stocks/all_stocks_list.csv')
    if csv_file.exists():
        import csv
        stocks = []
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts_code = row.get('ts_code', '').strip()
                if ts_code:
                    stocks.append({'ts_code': ts_code})
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
        
        return stocks
    
    return []

def fetch_daily_data(ts_code: str, start_date: str, end_date: str, retry_count: int = 3) -> Optional[Dict]:
    """获取单只股票日线数据"""
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
                if '每分钟最多' in error_msg or '限流' in error_msg:
                    if attempt < retry_count - 1:
                        wait_time = 65
                        log(f'⚠️ 限流，等待 {wait_time} 秒后重试...')
                        time.sleep(wait_time)
                        continue
                return None, error_msg
            
            data = result.get('data')
            if data and 'items' in data:
                return {'fields': data['fields'], 'items': data['items']}, None
            return None, "No data"
        
        except Exception as e:
            if attempt < retry_count - 1:
                time.sleep(1)
                continue
            return None, str(e)
    
    return None, "Max retries exceeded"

def update_stock_data(ts_code: str, new_items: List, new_fields: List) -> bool:
    """更新股票数据文件，合并新数据"""
    symbol = ts_code.split('.')[0]
    filepath = DATA_DIR / f'{symbol}.json'
    
    try:
        # 读取现有数据
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing_items = existing.get('items', [])
        else:
            existing_items = []
        
        # 构建日期集合用于去重
        existing_dates = set()
        for item in existing_items:
            if len(item) > 1:
                existing_dates.add(item[1])  # trade_date 是第二个字段
        
        # 添加新数据（去重）
        added = 0
        for item in new_items:
            if len(item) > 1 and item[1] not in existing_dates:
                existing_items.insert(0, item)  # 插入到开头（最新日期在前）
                added += 1
        
        if added > 0:
            # 按日期降序排序
            existing_items.sort(key=lambda x: x[1] if len(x) > 1 else '0', reverse=True)
            
            # 更新文件
            existing['items'] = existing_items
            existing['record_count'] = len(existing_items)
            existing['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        
        return True
    
    except Exception as e:
        log(f'更新 {ts_code} 失败: {e}')
        return False

def get_latest_trade_date() -> str:
    """获取最近的交易日期（今天或上一个交易日）"""
    today = datetime.now()
    # 简单处理：返回今天，API 会自动处理非交易日
    return today.strftime('%Y%m%d')

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='更新历史数据到最新')
    parser.add_argument('--check', action='store_true', help='检查进度')
    parser.add_argument('--days', type=int, default=30, help='获取最近N天数据 (默认30天)')
    
    args = parser.parse_args()
    
    # 检查进度
    if args.check:
        # 抽样检查几个文件
        samples = ['000001', '600000', '000002', '600519', '300750']
        for s in samples:
            filepath = DATA_DIR / f'{s}.json'
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = data.get('items', [])
                latest = items[0][1] if items else 'N/A'
                count = len(items)
                print(f'{s}: 最新日期={latest}, 记录数={count}')
        return
    
    log('=' * 80)
    log('📊 更新历史数据到最新')
    log('=' * 80)
    
    stock_list = load_stock_list()
    if not stock_list:
        log('❌ 无法加载股票列表')
        return
    
    log(f'计划更新 {len(stock_list)} 只股票')
    
    # 计算日期范围
    end_date = get_latest_trade_date()
    start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y%m%d')
    
    log(f'获取日期范围：{start_date} ~ {end_date}')
    
    start_time = time.time()
    updated_count = 0
    skip_count = 0
    fail_count = 0
    
    for i, stock in enumerate(stock_list):
        ts_code = stock.get('ts_code', '')
        symbol = ts_code.split('.')[0]
        
        if i % 200 == 0:
            elapsed = time.time() - start_time
            log(f'进度：{i+1}/{len(stock_list)} (更新:{updated_count} 跳过:{skip_count} 失败:{fail_count} 耗时:{elapsed:.1f}秒)')
        
        # 获取新数据
        result, error = fetch_daily_data(ts_code, start_date, end_date)
        
        if result and result.get('items'):
            new_items = result['items']
            new_fields = result['fields']
            
            if update_stock_data(ts_code, new_items, new_fields):
                added = len(new_items)
                updated_count += 1
            else:
                fail_count += 1
        else:
            skip_count += 1
        
        # 频率控制
        time.sleep(1.2)
    
    elapsed = time.time() - start_time
    log('=' * 80)
    log('📊 更新完成')
    log(f'总计：{len(stock_list)} 只')
    log(f'更新：{updated_count} 只')
    log(f'跳过：{skip_count} 只 (无新数据)')
    log(f'失败：{fail_count} 只')
    log(f'耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)')
    log('=' * 80)

if __name__ == '__main__':
    main()