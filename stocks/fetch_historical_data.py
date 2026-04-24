#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向前补充 A 股历史行情数据

在现有数据基础上，向前补充一年历史数据（2022 年）
继续使用 JSON 格式文件（fields/items 格式）向前追加数据

用法:
    python3 fetch_historical_data.py --year 2022    # 补充 2022 年数据
    python3 fetch_historical_data.py --start 20220101 --end 20221231
    python3 fetch_historical_data.py --check        # 检查现有数据日期范围
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
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/fetch_historical.log')
DATA_DIR.mkdir(exist_ok=True)

# API
api_url = 'http://api.tushare.pro'


def load_stock_list():
    """从缓存或 all_stocks_list.csv 加载股票列表"""
    cache_file = DATA_DIR / 'stock_list.json'
    
    if cache_file.exists():
        print(f'从缓存加载股票列表：{cache_file}')
        with open(cache_file, 'r', encoding='utf-8') as f:
            stock_list = json.load(f)
        print(f'加载到 {len(stock_list)} 只股票')
        return stock_list
    
    csv_file = Path('/home/admin/.openclaw/workspace/stocks/all_stocks_list.csv')
    if csv_file.exists():
        stocks = []
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            import csv
            reader = csv.DictReader(f)
            for row in reader:
                key = 'ts_code' if 'ts_code' in row else list(row.keys())[0]
                ts_code = row[key].strip()
                stocks.append({'ts_code': ts_code})
        print(f'从 CSV 加载 {len(stocks)} 只股票')
        return stocks
    
    print('未找到股票列表文件')
    return None


def get_existing_date_range(symbol: str) -> Optional[Dict]:
    """
    检查现有数据的日期范围
    
    Returns:
        {'earliest': '20230103', 'latest': '20241231', 'count': 500} or None
    """
    # 尝试多种文件名格式
    code_part = symbol.split('.')[0]
    possible_files = [
        DATA_DIR / f'{code_part}.json',
        DATA_DIR / f'{symbol.replace(".", "_")}.json',
    ]
    
    for filepath in possible_files:
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'items' in data and 'fields' in data:
                    fields = data['fields']
                    items = data['items']
                    
                    if not items:
                        return None
                    
                    # 找到 trade_date 字段索引
                    try:
                        date_idx = fields.index('trade_date')
                    except ValueError:
                        return None
                    
                    # 获取所有日期
                    dates = [item[date_idx] for item in items if item[date_idx]]
                    dates.sort()
                    
                    return {
                        'earliest': dates[0],
                        'latest': dates[-1],
                        'count': len(items),
                        'filepath': str(filepath)
                    }
            except Exception as e:
                print(f'读取 {filepath} 失败：{e}')
    
    return None


def fetch_daily_data(ts_code: str, start_date: str, end_date: str, retry_count: int = 3) -> Optional[Dict]:
    """获取单只股票日线数据（带限流重试）"""
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
                        print(f'限流，等待{wait_time}秒后重试...')
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


def merge_data(existing_data: Dict, new_data: Dict) -> Dict:
    """
    合并新旧数据，保持时间顺序（从旧到新）
    
    existing_data: 现有数据（较新的数据）
    new_data: 新获取的数据（较早的数据）
    """
    fields = existing_data.get('fields', [])
    existing_items = existing_data.get('items', [])
    new_items = new_data.get('items', [])
    
    # 找到 trade_date 字段索引
    try:
        date_idx = fields.index('trade_date')
    except ValueError:
        # 如果没有 trade_date 字段，直接拼接
        return {
            'fields': fields,
            'items': new_items + existing_items
        }
    
    # 合并并排序
    all_items = new_items + existing_items
    all_items.sort(key=lambda x: x[date_idx])
    
    # 去重（保留最新的）
    seen_dates = set()
    unique_items = []
    for item in reversed(all_items):  # 从新到旧遍历
        date = item[date_idx]
        if date not in seen_dates:
            seen_dates.add(date)
            unique_items.insert(0, item)  # 插回前面保持顺序
    
    return {
        'fields': fields,
        'items': unique_items
    }


def save_data(symbol: str, data: Dict):
    """保存数据到 JSON 文件"""
    code_part = symbol.split('.')[0]
    filepath = DATA_DIR / f'{code_part}.json'
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    
    return filepath


def check_existing_data(limit: int = 10):
    """检查现有数据的日期范围"""
    print('=' * 80)
    print('📊 检查现有数据日期范围')
    print('=' * 80)
    
    stock_list = load_stock_list()
    if not stock_list:
        print('无法加载股票列表')
        return
    
    if limit:
        stock_list = stock_list[:limit]
    
    stats = {
        'earliest_dates': [],
        'latest_dates': [],
        'total_records': 0
    }
    
    for i, stock in enumerate(stock_list):
        ts_code = stock.get('ts_code', '')
        symbol = ts_code.split('.')[0]
        
        date_range = get_existing_date_range(ts_code)
        if date_range:
            stats['earliest_dates'].append(date_range['earliest'])
            stats['latest_dates'].append(date_range['latest'])
            stats['total_records'] += date_range['count']
            
            if i < 20:  # 显示前 20 只
                print(f'{ts_code}: {date_range["earliest"]} ~ {date_range["latest"]} ({date_range["count"]}条)')
    
    if stats['earliest_dates']:
        stats['earliest_dates'].sort()
        stats['latest_dates'].sort()
        
        print()
        print(f'最早数据：{stats["earliest_dates"][0]}')
        print(f'最晚数据：{stats["latest_dates"][-1]}')
        print(f'总记录数：{stats["total_records"]:,}')
    
    print('=' * 80)


def fetch_historical_data(start_date: str, end_date: str, limit: int = None):
    """
    批量获取历史数据并追加到现有文件
    
    Args:
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        limit: 限制获取股票数量
    """
    print('=' * 80)
    print(f'📊 向前补充历史数据：{start_date} ~ {end_date}')
    print('=' * 80)
    
    stock_list = load_stock_list()
    if not stock_list:
        print('无法加载股票列表')
        return
    
    if limit:
        stock_list = stock_list[:limit]
    
    print(f'计划获取 {len(stock_list)} 只股票')
    print()
    
    start_time = time.time()
    success_count = 0
    fail_count = 0
    skip_count = 0
    append_count = 0
    
    for i, stock in enumerate(stock_list):
        ts_code = stock.get('ts_code', '')
        symbol = ts_code.split('.')[0]
        
        # 检查现有数据
        existing_range = get_existing_date_range(ts_code)
        
        if existing_range:
            # 如果已有数据覆盖目标日期范围，跳过
            if (existing_range['earliest'] <= start_date and 
                existing_range['latest'] >= end_date):
                if i < 50 or i % 100 == 0:
                    print(f'[{i+1}/{len(stock_list)}] {ts_code} - 已有完整数据，跳过')
                skip_count += 1
                success_count += 1
                continue
            
            # 如果目标日期与现有数据有重叠，需要合并
            needs_merge = (existing_range['earliest'] <= end_date)
        else:
            needs_merge = False
        
        # 获取新数据
        if i % 100 == 0:
            elapsed = time.time() - start_time
            print(f'\n进度：{i+1}/{len(stock_list)} (成功:{success_count} 失败:{fail_count} 跳过:{skip_count} 追加:{append_count} 耗时:{elapsed:.1f}秒)')
        
        print(f'[{i+1}/{len(stock_list)}] {ts_code} - 获取 {start_date}~{end_date}...', end=' ')
        
        result, error = fetch_daily_data(ts_code, start_date, end_date)
        
        if result and result.get('items'):
            item_count = len(result['items'])
            
            if needs_merge and existing_range:
                # 合并数据
                existing_data = {
                    'fields': existing_range.get('fields', result['fields']),
                    'items': []  # 需要重新加载
                }
                
                # 重新加载完整数据
                filepath = Path(existing_range['filepath'])
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                merged = merge_data(existing_data, result)
                save_data(ts_code, merged)
                
                append_count += 1
                print(f'合并成功 (新增{item_count}条，总计{len(merged["items"])}条)')
            else:
                # 直接保存（新文件或完全覆盖）
                if not existing_range:
                    save_data(ts_code, result)
                    print(f'保存成功 ({item_count}条)')
                else:
                    # 部分重叠，需要合并
                    filepath = Path(existing_range['filepath'])
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    merged = merge_data(existing_data, result)
                    save_data(ts_code, merged)
                    append_count += 1
                    print(f'合并成功 (新增{item_count}条，总计{len(merged["items"])}条)')
            
            success_count += 1
        else:
            fail_count += 1
            print(f'失败：{error}')
        
        # 频率控制：每分钟最多 50 次 = 每 1.2 秒一次
        time.sleep(1.2)
    
    elapsed = time.time() - start_time
    print()
    print('=' * 80)
    print('📊 获取完成')
    print(f'总计：{len(stock_list)} 只')
    print(f'成功：{success_count} 只')
    print(f'失败：{fail_count} 只')
    print(f'跳过：{skip_count} 只')
    print(f'追加：{append_count} 只')
    print(f'耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)')
    print('=' * 80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='向前补充 A 股历史数据')
    parser.add_argument('--year', type=int, help='补充指定年份数据 (如 2022)')
    parser.add_argument('--start', type=str, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--limit', type=int, help='限制获取股票数量')
    parser.add_argument('--check', action='store_true', help='检查现有数据日期范围')
    
    args = parser.parse_args()
    
    if args.check:
        check_existing_data(limit=args.limit)
        return
    
    if args.year:
        start_date = f'{args.year}0101'
        end_date = f'{args.year}1231'
    elif args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        # 默认补充 2022 年数据
        print('未指定日期，默认补充 2022 年数据 (20220101~20221231)')
        start_date = '20220101'
        end_date = '20221231'
    
    fetch_historical_data(start_date, end_date, limit=args.limit)


if __name__ == '__main__':
    main()
