#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取今日全市场行情数据 (2026-04-13)

使用东方财富/新浪/Tushare多源获取
"""

import json
import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/fetch_today.log')

TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'
TODAY = datetime.now().strftime('%Y%m%d')
TODAY_FMT = datetime.now().strftime('%Y-%m-%d')

def log(msg):
    print(msg)
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')

def fetch_tushare_daily():
    """使用Tushare获取今日日线数据"""
    log('='*60)
    log(f'Tushare获取今日行情 ({TODAY_FMT})')
    log('='*60)
    
    api_url = 'http://api.tushare.pro'
    
    # 获取全部股票日线
    payload = {
        'api_name': 'daily',
        'token': TUSHARE_TOKEN,
        'params': {
            'trade_date': TODAY
        },
        'fields': 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=60)
        result = resp.json()
        
        if result.get('code') != 0:
            log(f'❌ Tushare失败: {result.get("msg")}')
            return None
        
        data = result.get('data', {})
        fields = data.get('fields', [])
        items = data.get('items', [])
        
        if not items:
            log(f'⚠️ 今日({TODAY})无交易数据')
            return None
        
        df = pd.DataFrame(items, columns=fields)
        log(f'✅ 获取 {len(df)} 条日线数据')
        
        return df
        
    except Exception as e:
        log(f'❌ Tushare异常: {e}')
        return None

def fetch_eastmoney_quote():
    """使用东方财富获取实时行情"""
    log('\n东方财富实时行情...')
    
    # 东方财富全市场行情API
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    
    params = {
        'pn': 1,
        'pz': 5000,
        'po': 1,
        'np': 1,
        'fields': 'f12,f14,f2,f3,f4,f5,f6,f7,f15,f16,f17,f18',
        'fid': 'f3',
        'fs': 'm:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23',
    }
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        
        if data.get('data') and data['data'].get('diff'):
            items = data['data']['diff']
            df = pd.DataFrame(items)
            
            # 字段映射
            df = df.rename(columns={
                'f12': 'code',
                'f14': 'name',
                'f2': 'close',
                'f3': 'pct_chg',
                'f4': 'change',
                'f5': 'vol',
                'f6': 'amount',
                'f15': 'high',
                'f16': 'low',
                'f17': 'open',
                'f18': 'pre_close'
            })
            
            # 过滤无效数据
            df = df[df['close'] > 0]
            
            log(f'✅ 东方财富获取 {len(df)} 条')
            return df
        else:
            log('⚠️ 东方财富返回空')
            return None
            
    except Exception as e:
        log(f'❌ 东方财富异常: {e}')
        return None

def calculate_features(df):
    """计算技术指标特征"""
    log('\n计算技术指标...')
    
    # 确保数值类型
    for col in ['open', 'high', 'low', 'close', 'vol', 'amount']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['close'])
    
    features = []
    
    for _, row in df.iterrows():
        try:
            close = row['close']
            high = row['high']
            low = row['low']
            vol = row.get('vol', 0)
            pct_chg = row.get('pct_chg', 0)
            
            # 简化特征 (基于单日数据估算)
            feat = {
                'code': row.get('code', row.get('ts_code', '')),
                'date': TODAY_FMT,
                'close': close,
                'high': high,
                'low': low,
                'vol': vol,
                'pct_chg': pct_chg,
                
                # 简化技术指标 (需要历史数据才能准确计算)
                'hl_pct': (high - low) / close if close > 0 else 0,  # 振幅
                'hc_pct': (high - close) / close if close > 0 else 0,  # 上影线
                'cl_pct': (close - low) / close if close > 0 else 0,  # 下影线
                'vol_ratio': 1.0,  # 需历史均值
            }
            
            features.append(feat)
            
        except Exception as e:
            continue
    
    feat_df = pd.DataFrame(features)
    log(f'✅ 计算特征 {len(feat_df)} 条')
    
    return feat_df

def save_today_data(df):
    """保存今日数据"""
    if df is None or len(df) == 0:
        log('⚠️ 无数据保存')
        return
    
    # 保存到data_tushare目录
    today_file = DATA_DIR / f'{TODAY}_daily.csv'
    df.to_csv(today_file, index=False)
    log(f'✅ 已保存: {today_file}')
    
    # 同时更新到temp_full目录用于训练
    temp_dir = Path('/home/admin/.openclaw/workspace/stocks/temp_full')
    temp_file = temp_dir / f'today_{TODAY}.csv'
    df.to_csv(temp_file, index=False)
    log(f'✅ 已保存训练数据: {temp_file}')
    
    return today_file

def main():
    with open(LOG_FILE, 'w') as f:
        f.write(f'今日行情获取 - {datetime.now()}\n\n')
    
    log('='*60)
    log(f'获取今日全市场行情数据')
    log(f'日期: {TODAY_FMT}')
    log('='*60)
    
    # 优先Tushare
    df_tushare = fetch_tushare_daily()
    
    # 备用东方财富
    if df_tushare is None or len(df_tushare) < 1000:
        df_east = fetch_eastmoney_quote()
        if df_east is not None and len(df_east) > 0:
            df_tushare = df_east
    
    # 计算特征
    if df_tushare is not None:
        feat_df = calculate_features(df_tushare)
        save_today_data(feat_df)
    
    log('\n' + '='*60)
    log(f'完成: {datetime.now()}')
    log('='*60)

if __name__ == '__main__':
    main()