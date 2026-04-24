#!/usr/bin/env python3
"""ML选股 - 主板TOP5 (快速版)"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
import pickle
import random

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

def is_main_board(s):
    return s.startswith('60') or s.startswith('00')

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
    data['rsi'] = 100 - 100/(1 + gain/loss.replace(0, 0.001))
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

def scan(symbol, model, scaler, threshold):
    fp = CACHE_DIR / f'{symbol}.json'
    if not fp.exists():
        return None
    try:
        with open(fp, 'r') as f:
            d = json.load(f)
        df = pd.DataFrame(d['items'], columns=d['fields'])
        df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        for c in ['open', 'high', 'low', 'close', 'volume']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna()
        if len(df) < 60:
            return None
        feat = calc_features(df)
        latest = feat.iloc[-1]
        X = latest[FEATURES].values.reshape(1, -1)
        if np.any(np.isnan(X)):
            return None
        X_s = scaler.transform(X)
        prob = model.predict_proba(X_s)[0, 1]
        if prob > threshold:
            return {
                'symbol': symbol,
                'prob': prob,
                'close': float(latest['close']),
                'rsi': float(latest['rsi']),
                'p_ma20': float((latest['close'] - latest['ma20']) / latest['ma20']),
                'kdj_j': float(latest['kdj_j'])
            }
    except:
        return None

# 主流程
model_files = sorted(MODEL_DIR.glob('ml_selector*.pkl'), reverse=True)
with open(model_files[0], 'rb') as f:
    data = pickle.load(f)
model = data['model']
scaler = data['scaler']
threshold = data.get('threshold', 0.65)

print(f'模型: {model_files[0].name}')
print(f'阈值: {threshold*100:.0f}%')

# 主板股票
symbols = [f.stem for f in CACHE_DIR.glob('*.json')]
main_symbols = [s for s in symbols if is_main_board(s)]
print(f'主板总数: {len(main_symbols)}')

# 随机抽样500只主板股票演示
random.seed(42)
sample = random.sample(main_symbols, min(500, len(main_symbols)))
print(f'抽样扫描: {len(sample)}只')

results = []
for s in sample:
    r = scan(s, model, scaler, threshold)
    if r:
        results.append(r)

results.sort(key=lambda x: -x['prob'])
print(f'\n发现高置信度: {len(results)}只')

if results:
    print('\n🏆 主板TOP 5 (基于历史数据):')
    print('| 代码 | 置信度 | 现价 | RSI | 跌MA20 | KDJ-J |')
    print('|------|--------|------|-----|--------|-------|')
    for r in results[:5]:
        print(f'| {r["symbol"]} | {r["prob"]*100:.0f}% | ¥{r["close"]:.2f} | {r["rsi"]:.0f} | {r["p_ma20"]*100:.1f}% | {r["kdj_j"]:.0f} |')