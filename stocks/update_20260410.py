#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制更新指定日期行情数据
日期: 2026-04-10
"""

import json
import requests
import time
from pathlib import Path
from datetime import datetime
import pandas as pd

# Tushare配置
TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'
API_URL = 'http://api.tushare.pro'

# 数据目录
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
BACKUP_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_backup_20260410')

# 目标日期
TARGET_DATE = '20260410'

print('='*60)
print(f'更新行情数据 - {TARGET_DATE}')
print('='*60)
print()


def get_daily_quotes(date, retry=3):
    """获取指定日期全市场行情"""
    payload = {
        'api_name': 'daily',
        'token': TUSHARE_TOKEN,
        'params': {
            'trade_date': date
        },
        'fields': 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
    }
    
    for i in range(retry):
        try:
            resp = requests.post(API_URL, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                return result.get('data')
            else:
                print(f"API错误: {result.get('msg')}")
                if i < retry - 1:
                    time.sleep(1)
        except Exception as e:
            print(f"请求失败: {e}")
            if i < retry - 1:
                time.sleep(1)
    
    return None


def update_stock_file(symbol, new_data):
    """更新单只股票数据文件"""
    filepath = DATA_DIR / f'{symbol}.json'
    
    if not filepath.exists():
        # 新股票，直接创建
        with open(filepath, 'w') as f:
            json.dump({
                'fields': ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount'],
                'items': [new_data]
            }, f)
        return 'created'
    
    # 读取现有数据
    with open(filepath, 'r') as f:
        existing = json.load(f)
    
    items = existing.get('items', [])
    
    # 检查是否已有该日期数据
    for item in items:
        if item[1] == new_data[1]:  # trade_date
            # 已存在，替换
            item[:] = new_data
            with open(filepath, 'w') as f:
                json.dump(existing, f)
            return 'replaced'
    
    # 新数据，插入到最前面（最新日期）
    items.insert(0, new_data)
    
    # 限制数据长度（保留最近3年）
    if len(items) > 800:
        items = items[:800]
    
    existing['items'] = items
    with open(filepath, 'w') as f:
        json.dump(existing, f)
    
    return 'added'


def backup_data():
    """备份现有数据"""
    import shutil
    if BACKUP_DIR.exists():
        print(f"备份目录已存在: {BACKUP_DIR}")
    else:
        print(f"备份现有数据到: {BACKUP_DIR}")
        shutil.copytree(DATA_DIR, BACKUP_DIR)
        print("备份完成")


def main():
    # 备份
    backup_data()
    print()
    
    # 获取4月10日行情
    print(f"获取 {TARGET_DATE} 全市场行情...")
    data = get_daily_quotes(TARGET_DATE)
    
    if not data or not data.get('items'):
        print("❌ 获取数据失败")
        return
    
    items = data.get('items')
    fields = data.get('fields')
    
    print(f"获取到 {len(items)} 条行情数据")
    print()
    
    # 更新各股票文件
    updated = 0
    created = 0
    replaced = 0
    
    for i, item in enumerate(items):
        ts_code = item[0]  # 如 '000001.SZ'
        symbol = ts_code.split('.')[0]  # '000001'
        
        result = update_stock_file(symbol, item)
        
        if result == 'created':
            created += 1
        elif result == 'replaced':
            replaced += 1
        else:
            updated += 1
        
        if (i + 1) % 500 == 0:
            print(f"进度: {i+1}/{len(items)} ({(i+1)/len(items)*100:.0f}%)")
    
    print()
    print('='*60)
    print('更新完成')
    print('='*60)
    print(f"新增: {created}")
    print(f"替换: {replaced}")
    print(f"追加: {updated}")
    print(f"总计: {len(items)}")
    
    # 验证
    print()
    print("验证数据...")
    
    # 检查平安银行
    test_file = DATA_DIR / '000001.json'
    with open(test_file, 'r') as f:
        test_data = json.load(f)
    
    latest = test_data['items'][0]
    print(f"平安银行最新数据: {latest[1]} 收盘价 ¥{latest[5]}")
    
    if latest[1] == TARGET_DATE:
        print("✅ 数据已更新到 2026-04-10")
    else:
        print(f"⚠️ 最新日期为 {latest[1]}")


if __name__ == '__main__':
    main()