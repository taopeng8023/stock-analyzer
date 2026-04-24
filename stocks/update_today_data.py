#!/usr/bin/env python3
"""
补充今日市场行情数据
使用 Tushare API 获取 2026-04-16 数据
"""
import json
import requests
from pathlib import Path
from datetime import datetime
import time

print("="*70)
print("补充今日市场行情数据")
print("="*70)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")

# Tushare API 配置
TUSHARE_TOKEN = "a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4"
TUSHARE_API = "http://api.tushare.pro"

TODAY = "20260416"

print(f"\n获取日期: {TODAY}")
print("调用 Tushare API...")

# 调用 Tushare API
payload = {
    'api_name': 'daily',
    'token': TUSHARE_TOKEN,
    'params': {'trade_date': TODAY},
    'fields': ''
}

try:
    resp = requests.post(TUSHARE_API, json=payload, timeout=30)
    result = resp.json()
    
    if result.get('code') != 0:
        print(f"API错误: {result.get('msg', '未知错误')}")
        exit(1)
    
    data = result.get('data', {})
    items = data.get('items', [])
    fields = data.get('fields', [])
    
    print(f"获取数据: {len(items)}条")
    
    if len(items) == 0:
        print("今日无交易数据，可能是非交易日")
        exit(0)
    
    # 统计更新
    success_count = 0
    skip_count = 0
    error_count = 0
    
    print("\n追加到历史数据...")
    
    for item in items:
        ts_code = item[0]  # ts_code 是第一个字段
        
        # 提取股票代码（去掉市场后缀）
        if '.' in ts_code:
            code = ts_code.split('.')[0]
            market = ts_code.split('.')[1]  # SZ/SH
        else:
            code = ts_code
            market = 'SZ' if code.startswith('0') or code.startswith('3') else 'SH'
        
        # 确定文件名
        market_code = '0' if market == 'SZ' else '1'
        filename = f"{market_code}.{code}.json"
        
        # 如果不存在，尝试其他命名
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            filepath = HISTORY_DIR / f"{code}.json"
        
        if not filepath.exists():
            skip_count += 1
            continue
        
        try:
            with open(filepath, 'r') as f:
                raw_data = json.load(f)
            
            existing_items = raw_data.get('items', [])
            existing_fields = raw_data.get('fields', [])
            
            # 检查是否已存在该日期
            for existing in existing_items:
                if isinstance(existing, list) and existing[1] == TODAY:
                    skip_count += 1
                    continue
            
            # 追加新数据（追加到末尾，因为数据从旧到新）
            existing_items.append(item)
            
            # 更新元数据
            raw_data['items'] = existing_items
            raw_data['update_time'] = str(datetime.now())
            raw_data['record_count'] = len(existing_items)
            
            # 保存
            with open(filepath, 'w') as f:
                json.dump(raw_data, f)
            
            success_count += 1
            
            if success_count % 500 == 0:
                print(f"  已更新 {success_count} 股...")
        
        except Exception as e:
            error_count += 1
    
    print(f"\n更新完成:")
    print(f"  成功追加: {success_count}股")
    print(f"  跳过(已存在): {skip_count}股")
    print(f"  错误: {error_count}股")
    
    # 验证更新
    print("\n验证更新:")
    verify_files = sorted(HISTORY_DIR.glob('*.json'))[:3]
    for fp in verify_files:
        with open(fp) as f:
            raw = json.load(f)
        items = raw['items']
        if items:
            latest_date = str(items[-1][1])
            print(f'{fp.stem}: 最新日期 {latest_date}')
    
    # 保存今日数据摘要
    summary_file = HISTORY_DIR.parent / "data" / f"daily_update_{TODAY}.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'date': TODAY,
            'total_records': len(items),
            'success': success_count,
            'skip': skip_count,
            'error': error_count,
            'update_time': str(datetime.now())
        }, f)
    
    print(f"\n摘要保存: {summary_file.name}")
    print("\n完成:", datetime.now())

except requests.exceptions.Timeout:
    print("API超时，请稍后重试")
except Exception as e:
    print(f"错误: {e}")