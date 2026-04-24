#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML选股 - 快速演示版
只扫描部分股票，展示当前可用的高置信度股票
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import pickle

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')

FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20',
    'ma5_slope', 'ma20_slope',
    'ret1', 'ret5', 'ret10',
    'vol5', 'vol20',
    'rsi',
    'macd_dif', 'macd_dea', 'macd_hist',
    'kdj_k', 'kdj_d', 'kdj_j',
    'vol_ratio',
    'hl_pct'
]


def load_model():
    model_files = sorted(MODEL_DIR.glob('ml_selector*.pkl'), reverse=True)
    if not model_files:
        return None
    with open(model_files[0], 'rb') as f:
        return pickle.load(f)


def calc_features(df):
    data = df.copy()
    data['ma5'] = data['close'].rolling(5).mean()
    data['ma10'] = data['close'].rolling(10).mean()
    data['ma20'] = data['close'].rolling(20).mean()
    data['p_ma5'] = (data['close'] - data['ma5']) / data['ma5']
    data['p_ma10'] = (data['close'] - data['ma10']) / data['ma10']
    data['p_ma20'] = (data['close'] - data['ma20']) / data['ma20']
    data['ma5_slope'] = data['ma5'] / data['ma5'].shift(5) - 1
    data['ma20_slope'] = data['ma20'] / data['ma20'].shift(10) - 1
    data['ret1'] = data['close'].pct_change()
    data['ret5'] = data['close'].pct_change(5)
    data['ret10'] = data['close'].pct_change(10)
    data['vol5'] = data['ret1'].rolling(5).std()
    data['vol20'] = data['ret1'].rolling(20).std()
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss.replace(0, 0.001)
    data['rsi'] = 100 - (100 / (1 + rs))
    ema12 = data['close'].ewm(span=12, adjust=False).mean()
    ema26 = data['close'].ewm(span=26, adjust=False).mean()
    data['macd_dif'] = ema12 - ema26
    data['macd_dea'] = data['macd_dif'].ewm(span=9, adjust=False).mean()
    data['macd_hist'] = (data['macd_dif'] - data['macd_dea']) * 2
    lowv = data['low'].rolling(9).min()
    highv = data['high'].rolling(9).max()
    rsv = (data['close'] - lowv) / (highv - lowv + 0.001) * 100
    data['kdj_k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
    data['kdj_d'] = data['kdj_k'].ewm(alpha=1/3, adjust=False).mean()
    data['kdj_j'] = 3 * data['kdj_k'] - 2 * data['kdj_d']
    data['vol_ma5'] = data['volume'].rolling(5).mean()
    data['vol_ratio'] = data['volume'] / data['vol_ma5']
    data['hl_pct'] = (data['high'] - data['low']) / data['close']
    return data


def scan_stock(symbol, model, scaler, features, threshold):
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        df = pd.DataFrame(data['items'], columns=data['fields'])
        df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()
        if len(df) < 60:
            return None
        feat_df = calc_features(df)
        latest = feat_df.iloc[-1]
        feat_vals = latest[features].values
        if np.any(np.isnan(feat_vals)):
            return None
        X = feat_vals.reshape(1, -1)
        X_s = scaler.transform(X)
        prob = model.predict_proba(X_s)[0, 1]
        if prob > threshold:
            return {
                'symbol': symbol,
                'prob': prob,
                'close': float(latest['close']),
                'rsi': float(latest['rsi']),
                'p_ma20': float((latest['close'] - latest['ma20']) / latest['ma20'])
            }
        return None
    except:
        return None


def main():
    print('='*60)
    print('ML选股快速演示')
    print('='*60)
    
    model_data = load_model()
    if not model_data:
        print('❌ 无模型')
        return
    
    model = model_data['model']
    scaler = model_data['scaler']
    features = model_data.get('features', FEATURES)
    threshold = model_data.get('threshold', 0.65)
    
    print(f'✅ 模型加载成功')
    print(f'  阈值: {threshold*100:.0f}%')
    
    # 只取部分股票演示
    import random
    symbols = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    random.seed(42)
    sample = random.sample(symbols, min(500, len(symbols)))
    
    print(f'  扫描: {len(sample)}只股票')
    
    results = []
    for i, symbol in enumerate(sample):
        r = scan_stock(symbol, model, scaler, features, threshold)
        if r:
            results.append(r)
        if (i+1) % 100 == 0:
            print(f'  ⏳ {i+1}/{len(sample)} | 发现:{len(results)}')
    
    results.sort(key=lambda x: -x['prob'])
    
    print(f'\n发现高置信度股票: {len(results)}只')
    
    if results:
        print('\n🏆 TOP 10:')
        print('| 代码 | 置信度 | 现价 | RSI | 跌MA20 |')
        print('|------|--------|------|-----|--------|')
        for r in results[:10]:
            print(f"| {r['symbol']} | {r['prob']*100:.0f}% | {r['close']:.2f} | {r['rsi']:.0f} | {r['p_ma20']*100:.1f}% |")


if __name__ == '__main__':
    main()