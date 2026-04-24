#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
追加最新行情数据到历史数据

直接获取最近几个交易日的数据，追加到现有文件
"""

import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time

TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'
API_URL = 'http://api.tushare.pro'

DATA_DIR_JSON = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
DATA_DIR_CSV = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/append_quote.log')

def log(msg):
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f'{datetime.now()}: {msg}\n')

def fetch_daily_data(trade_date):
    """获取指定日期的全市场日线数据"""
    payload = {
        'api_name': 'daily',
        'token': TUSHARE_TOKEN,
        'params': {'trade_date': trade_date},
        'fields': 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
    }
    
    try:
        resp = requests.post(API_URL, json=payload, timeout=60)
        result = resp.json()
        
        if result.get('code') == 0:
            items = result['data']['items']
            return items
        else:
            log(f'Tushare {trade_date}: {result.get("msg", "未知错误")}')
            return None
    except Exception as e:
        log(f'请求失败 {trade_date}: {e}')
        return None

def get_latest_dates(df):
    """从现有数据获取最新日期"""
    # 查找所有JSON文件的最新日期
    json_files = list(DATA_DIR_JSON.glob('*.json'))
    
    latest_dates = {}
    for jf in json_files[:10]:  # 只检查前10个
        try:
            with open(jf, 'r') as f:
                data = json.load(f)
            if data['items']:
                code = data['symbol'].split('.')[0]
                latest_dates[code] = data['items'][0][1]  # 最新日期YYYYMMDD
        except:
            continue
    
    return latest_dates

def append_to_json(code, new_item):
    """追加到JSON文件"""
    json_file = DATA_DIR_JSON / f'{code}.json'
    
    if not json_file.exists():
        return False
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查是否已存在
        existing_dates = [item[1] for item in data['items']]
        if new_item[1] in existing_dates:
            return True
        
        # 追加
        data['items'].insert(0, new_item)
        data['record_count'] = len(data['items'])
        data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 更新date_range
        first_date = data['items'][0][1]
        last_date = data['items'][-1][1]
        data['date_range'] = f'{last_date} ~ {first_date}'
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        return False

def append_to_csv(code, new_item):
    """追加到CSV文件"""
    csv_file = DATA_DIR_CSV / f'{code}_SZ.csv'
    
    if not csv_file.exists():
        return False
    
    try:
        df = pd.read_csv(csv_file)
        
        new_date = new_item[1]
        if new_date in df['date'].astype(str).values:
            return True
        
        new_row = {
            'date': new_date,
            'open': new_item[2],
            'close': new_item[5],
            'high': new_item[3],
            'low': new_item[4],
            'volume': new_item[9],
            'ts_code': new_item[0]
        }
        
        df_new = pd.DataFrame([new_row])
        df = pd.concat([df_new, df], ignore_index=True)
        df.to_csv(csv_file, index=False)
        
        return True
    except:
        return False

def main():
    with open(LOG_FILE, 'w') as f:
        f.write(f'追加行情数据 - {datetime.now()}\n')
    
    log('='*60)
    log('追加最新行情数据')
    log('='*60)
    
    # 检查现有最新日期
    sample_file = DATA_DIR_JSON / '000001.json'
    with open(sample_file, 'r') as f:
        sample_data = json.load(f)
    
    current_latest = sample_data['items'][0][1]
    log(f'现有最新日期: {current_latest}')
    
    # 尝试获取最近几天的数据
    today = datetime.now()
    
    # 尝试最近5个可能的交易日 (跳过周末)
    dates_to_try = []
    for i in range(1, 8):
        d = today - timedelta(days=i)
        # 跳过周末 (周六=5, 周日=6)
        if d.weekday() < 5:
            dates_to_try.append(d.strftime('%Y%m%d'))
    
    log(f'尝试日期: {dates_to_try}')
    
    total_added = 0
    
    for trade_date in dates_to_try:
        if trade_date <= current_latest:
            log(f'{trade_date} 已存在，跳过')
            continue
        
        log(f'\n获取 {trade_date}...')
        items = fetch_daily_data(trade_date)
        
        if not items:
            log(f'{trade_date}: 无数据')
            continue
        
        log(f'{trade_date}: 获取 {len(items)} 条')
        
        # 追加
        success = 0
        for item in items:
            ts_code = item[0]
            code = ts_code.split('.')[0]
            
            if append_to_json(code, item):
                append_to_csv(code, item)
                success += 1
        
        log(f'{trade_date}: 成功追加 {success}')
        total_added += success
        
        # 如果成功获取数据，继续下一个日期
        if success > 100:
            continue
        else:
            break
    
    log('='*60)
    log(f'总计追加: {total_added}')
    log(f'完成时间: {datetime.now()}')
    log('='*60)

if __name__ == '__main__':
    main()