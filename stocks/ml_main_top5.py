#!/usr/bin/env python3
"""ML选股 - 主板TOP5"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
import pickle

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')

FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'p_ma60',
    'ma5_slope', 'ma10_slope', 'ma20_slope',
    'ret1', 'ret5', 'ret10', 'ret20',
    'vol5', 'vol10', 'vol20',
    'rsi',
    'macd_dif', 'macd_dea', 'macd_hist',
    'kdj_k', 'kdj_d', 'kdj_j',
    'vol_ratio', 'vol_ratio20',
    'hl_pct', 'hc_pct', 'cl_pct',
    'boll_pos'
]

# 主板代码规则
def is_main_board(symbol):
    """判断是否主板"""
    # 沪市主板: 600/601/603
    if symbol.startswith('60'):
        return True
    # 深市主板: 000/001/002/003
    if symbol.startswith('00'):
        return True
    return False

def calc_features(df):
    data = df.copy()
    for p in [5, 10, 20, 60]:
        data[f'ma{p}'] = data['close'].rolling(p).mean()
        data[f'p_ma{p}'] = (data['close'] - data[f'ma{p}']) / data[f'ma{p}']
    data['ma5_slope'] = data['ma5'] / data['ma5'].shift(5) - 1
    data['ma10_slope'] = data['ma10'] / data['ma10'].shift(5) - 1
    data['ma20_slope'] = data['ma20'] / data['ma20'].shift(10) - 1
    for d in [1, 5, 10, 20]:
        data[f'ret{d}'] = data['close'].pct_change(d)
    for d in [5, 10, 20]:
        data[f'vol{d}'] = data['ret1'].rolling(d).std()
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
    data['vol_ma20'] = data['volume'].rolling(20).mean()
    data['vol_ratio'] = data['volume'] / data['vol_ma5']
    data['vol_ratio20'] = data['volume'] / data['vol_ma20']
    data['hl_pct'] = (data['high'] - data['low']) / data['close']
    data['hc_pct'] = (data['high'] - data['close']) / data['close']
    data['cl_pct'] = (data['close'] - data['low']) / data['close']
    data['boll_mid'] = data['close'].rolling(20).mean()
    data['boll_std'] = data['close'].rolling(20).std()
    data['boll_upper'] = data['boll_mid'] + 2 * data['boll_std']
    data['boll_lower'] = data['boll_mid'] - 2 * data['boll_std']
    data['boll_pos'] = (data['close'] - data['boll_lower']) / (data['boll_upper'] - data['boll_lower'] + 0.001)
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

def main():
    # 加载模型
    model_files = sorted(MODEL_DIR.glob('ml_selector*.pkl'), reverse=True)
    if not model_files:
        print('无模型')
        return
    with open(model_files[0], 'rb') as f:
        data = pickle.load(f)
    model = data['model']
    scaler = data['scaler']
    threshold = data.get('threshold', 0.65)
    
    print(f'模型: {model_files[0].name}')
    print(f'阈值: {threshold*100:.0f}%')
    
    # 扫描主板
    symbols = [f.stem for f in CACHE_DIR.glob('*.json')]
    main_symbols = [s for s in symbols if is_main_board(s)]
    print(f'主板股票: {len(main_symbols)}只')
    
    results = []
    for i, s in enumerate(main_symbols):
        r = scan(s, model, scaler, threshold)
        if r:
            results.append(r)
        if (i+1) % 500 == 0:
            print(f'  扫描:{i+1}/{len(main_symbols)} | 发现:{len(results)}')
    
    results.sort(key=lambda x: -x['prob'])
    
    print(f'\n发现: {len(results)}只高置信度主板股票')
    
    if results:
        print('\n🏆 主板TOP 5:')
        print('| 代码 | 置信度 | 现价 | RSI | 跌MA20 | KDJ-J |')
        print('|------|--------|------|-----|--------|-------|')
        for r in results[:5]:
            print(f'| {r["symbol"]} | {r["prob"]*100:.0f}% | ¥{r["close"]:.2f} | {r["rsi"]:.0f} | {r["p_ma20"]*100:.1f}% | {r["kdj_j"]:.0f} |')
        
        # 保存
        pd.DataFrame(results[:20]).to_csv(
            Path('/home/admin/.openclaw/workspace/stocks/backtest_results') / 'ml_main_top5.csv',
            index=False
        )

if __name__ == '__main__':
    main()