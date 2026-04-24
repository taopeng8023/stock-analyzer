#!/usr/bin/env python3
"""
批量更新今日行情数据 - 分批处理版
解决：
1. 涨跌幅计算修正
2. 分批处理避免连接限制
3. 增加重试机制
"""
import os
import json
import requests
import pandas as pd
from datetime import datetime
import time
import random

print("="*80)
print("批量更新今日行情 - 分批处理")
print("="*80)
print(f"开始时间: {datetime.now()}")

DATA_DIR = "/home/admin/.openclaw/workspace/stocks/data_history_2022_2026"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://quote.eastmoney.com/',
}

def get_market(code):
    if code.startswith('6'):
        return '1'
    elif code.startswith(('0', '3')):
        return '0'
    return '1'

def get_realtime_quote(code, retry=3):
    """获取实时行情 - 增加重试"""
    market = get_market(code)
    secid = f"{market}.{code}"
    
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        'secid': secid,
        'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60',
        '_': int(time.time() * 1000)
    }
    
    for attempt in range(retry):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                q = data['data']
                close = q.get('f43', 0) / 100
                pre_close = q.get('f60', 0) / 100
                
                # 涨跌幅计算
                if pre_close > 0:
                    pct_chg = (close - pre_close) / pre_close * 100
                    change = close - pre_close
                else:
                    pct_chg = 0
                    change = 0
                
                return {
                    'ts_code': code,
                    'trade_date': datetime.now().strftime('%Y%m%d'),
                    'open': q.get('f46', 0) / 100,
                    'high': q.get('f44', 0) / 100,
                    'low': q.get('f45', 0) / 100,
                    'close': close,
                    'pre_close': pre_close,
                    'change': change,
                    'pct_chg': pct_chg,
                    'vol': q.get('f47', 0),
                    'amount': q.get('f48', 0),
                }
            return None
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(1)
            else:
                return None
    
    return None

# 获取股票列表
stock_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.json')])
total = len(stock_files)
print(f"股票总数: {total}")

# 分批处理 (每批100股，间隔2秒)
batch_size = 100
total_batches = total // batch_size + 1

updated_total = 0
failed_total = 0

# 先处理重点持仓股票
priority_stocks = ['002709', '600089', '603739']  # 天赐材料, 特变电工, 蔚蓝生物

print("\n优先更新持仓股票...")
for code in priority_stocks:
    quote = get_realtime_quote(code)
    if quote and quote['close'] > 0:
        file_path = os.path.join(DATA_DIR, f"{code}.json")
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if 'items' in data:
            today_date = datetime.now().strftime('%Y%m%d')
            dates = [item[1] for item in data['items']]
            
            if today_date not in dates:
                new_item = [
                    code, quote['trade_date'], quote['open'], quote['high'],
                    quote['low'], quote['close'], quote['pre_close'],
                    quote['change'], quote['pct_chg'], quote['vol'], quote['amount']
                ]
                data['items'].append(new_item)
                
                with open(file_path, 'w') as f:
                    json.dump(data, f)
                
                print(f"  ✅ {code}: ¥{quote['close']:.2f} ({quote['pct_chg']:.2f}%)")
                updated_total += 1
            else:
                print(f"  ⏭️ {code}: 已有今日数据")
    
    time.sleep(0.5)

# 分批处理剩余股票 (处理500股)
print("\n批量更新其他股票 (处理500股)...")
batch_files = random.sample(stock_files, 500)

for batch_idx in range(0, len(batch_files), batch_size):
    batch = batch_files[batch_idx:batch_idx + batch_size]
    
    print(f"\n批次 {batch_idx//batch_size + 1}/{len(batch_files)//batch_size + 1}")
    
    batch_updated = 0
    for stock_file in batch:
        code = stock_file.replace('.json', '')
        quote = get_realtime_quote(code, retry=2)
        
        if quote and quote['close'] > 0:
            file_path = os.path.join(DATA_DIR, stock_file)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if 'items' in data:
                    today_date = datetime.now().strftime('%Y%m%d')
                    dates = [item[1] for item in data['items']]
                    
                    if today_date not in dates and quote['pct_chg'] < 20 and quote['pct_chg'] > -20:
                        new_item = [
                            code, quote['trade_date'], quote['open'], quote['high'],
                            quote['low'], quote['close'], quote['pre_close'],
                            quote['change'], quote['pct_chg'], quote['vol'], quote['amount']
                        ]
                        data['items'].append(new_item)
                        
                        with open(file_path, 'w') as f:
                            json.dump(data, f)
                        
                        batch_updated += 1
            except:
                pass
        
        time.sleep(0.2)
    
    updated_total += batch_updated
    print(f"  本批更新: {batch_updated}")
    
    time.sleep(2)  # 批次间隔

print(f"\n{'='*60}")
print(f"更新完成")
print(f"{'='*60}")
print(f"总更新: {updated_total}股")

# 验证
print(f"\n验证天赐材料数据...")
with open(os.path.join(DATA_DIR, "002709.json"), 'r') as f:
    data = json.load(f)
    items = data['items']
    latest = items[-1]
    print(f"  最新日期: {latest[1]}")
    print(f"  最新收盘: ¥{latest[5]:.2f}")
    print(f"  涨跌幅: {latest[8]:.2f}%")

print(f"\n完成时间: {datetime.now()}")