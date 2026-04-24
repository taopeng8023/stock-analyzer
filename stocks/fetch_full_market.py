#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场行情获取 - 多源聚合

使用多个数据源确保完整性
"""

import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
TODAY = datetime.now().strftime('%Y%m%d')

def fetch_sina_all():
    """新浪财经全市场行情"""
    print('新浪财经获取...')
    
    # 新浪A股列表API
    url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
    
    params = {
        'page': 1,
        'num': 8000,
        'sort': 'symbol',
        'asc': 1,
        'node': 'hs_a',
        '_s_r_a': 'page'
    }
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        
        if data:
            df = pd.DataFrame(data)
            # 字段映射
            df = df.rename(columns={
                'symbol': 'code',
                'name': 'name',
                'trade': 'close',
                'pricechange': 'change',
                'changepercent': 'pct_chg',
                'volume': 'vol',
                'amount': 'amount',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'settlement': 'pre_close'
            })
            
            df = df[df['close'].notna() & (df['close'] != '0')]
            print(f'✅ 新浪获取 {len(df)} 条')
            return df
    except Exception as e:
        print(f'❌ 新浪失败: {e}')
    
    return None

def fetch_eastmoney_pages():
    """东方财富分页获取"""
    print('东方财富分页获取...')
    
    all_data = []
    
    for page in range(1, 5):  # 5页
        url = 'http://push2.eastmoney.com/api/qt/clist/get'
        
        params = {
            'pn': page,
            'pz': 1000,
            'po': 1,
            'np': 1,
            'fields': 'f12,f14,f2,f3,f4,f5,f6,f7,f15,f16,f17,f18',
            'fid': 'f3',
            'fs': 'b:MK0021,b:MK0022,b:MK0023,b:MK0024',
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get('data') and data['data'].get('diff'):
                items = data['data']['diff']
                all_data.extend(items)
                print(f'  页{page}: {len(items)}条')
        except:
            break
    
    if all_data:
        df = pd.DataFrame(all_data)
        df = df.rename(columns={
            'f12': 'code', 'f14': 'name', 'f2': 'close',
            'f3': 'pct_chg', 'f4': 'change', 'f5': 'vol',
            'f6': 'amount', 'f15': 'high', 'f16': 'low',
            'f17': 'open', 'f18': 'pre_close'
        })
        
        df = df[df['close'] > 0]
        print(f'✅ 东方财富共 {len(df)} 条')
        return df
    
    return None

def merge_and_save():
    """合并多源数据"""
    print('='*60)
    print(f'全市场行情获取 {datetime.now().strftime("%Y-%m-%d")}')
    print('='*60)
    
    df_sina = fetch_sina_all()
    df_east = fetch_eastmoney_pages()
    
    # 合并
    if df_sina is not None and len(df_sina) > 0:
        df = df_sina
        source = 'sina'
    elif df_east is not None and len(df_east) > 0:
        df = df_east
        source = 'eastmoney'
    else:
        print('❌ 无数据')
        return
    
    # 添加日期
    df['date'] = datetime.now().strftime('%Y-%m-%d')
    
    # 计算基础特征
    df['hl_pct'] = (pd.to_numeric(df['high'], errors='coerce') - pd.to_numeric(df['low'], errors='coerce')) / pd.to_numeric(df['close'], errors='coerce')
    df['vol_ratio'] = 1.0
    
    # 保存
    file_path = DATA_DIR / f'{TODAY}_daily.csv'
    df.to_csv(file_path, index=False)
    print(f'✅ 已保存 {len(df)} 条: {file_path}')
    
    # 训练数据
    temp_file = Path('/home/admin/.openclaw/workspace/stocks/temp_full/today_{TODAY}.csv')
    df.to_csv(temp_file, index=False)
    
    return df

if __name__ == '__main__':
    df = merge_and_save()
    if df:
        print(f'\n数据概览:')
        print(f'  股票数: {len(df)}')
        print(f'  涨停: {len(df[df["pct_chg"].astype(float) >= 9.5])}')
        print(f'  跌停: {len(df[df["pct_chg"].astype(float) <= -9.5])}')
        print(f'  上涨: {len(df[df["pct_chg"].astype(float) > 0])}')
        print(f'  下跌: {len(df[df["pct_chg"].astype(float) < 0])}')