#!/usr/bin/env python3
"""ML选股主板TOP5 - 使用完整2022-2026数据"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
import pickle

DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')

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

def calc_features(df):
    """计算技术指标"""
    d = df.copy()
    d['ma5'] = d['close'].rolling(5).mean()
    d['ma10'] = d['close'].rolling(10).mean()
    d['ma20'] = d['close'].rolling(20).mean()
    d['p_ma5'] = (d['close'] - d['ma5']) / d['ma5']
    d['p_ma10'] = (d['close'] - d['ma10']) / d['ma10']
    d['p_ma20'] = (d['close'] - d['ma20']) / d['ma20']
    d['ma5_slope'] = d['ma5'] / d['ma5'].shift(5) - 1
    d['ma20_slope'] = d['ma20'] / d['ma20'].shift(10) - 1
    d['ret1'] = d['close'].pct_change()
    d['ret5'] = d['close'].pct_change(5)
    d['ret10'] = d['close'].pct_change(10)
    d['vol5'] = d['ret1'].rolling(5).std()
    d['vol20'] = d['ret1'].rolling(20).std()
    delta = d['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    d['rsi'] = 100 - 100/(1 + gain/loss.replace(0, 0.001))
    ema12 = d['close'].ewm(span=12, adjust=False).mean()
    ema26 = d['close'].ewm(span=26, adjust=False).mean()
    d['macd_dif'] = ema12 - ema26
    d['macd_dea'] = d['macd_dif'].ewm(span=9, adjust=False).mean()
    d['macd_hist'] = (d['macd_dif'] - d['macd_dea']) * 2
    lowv = d['low'].rolling(9).min()
    highv = d['high'].rolling(9).max()
    rsv = (d['close'] - lowv) / (highv - lowv + 0.001) * 100
    d['kdj_k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
    d['kdj_d'] = d['kdj_k'].ewm(alpha=1/3, adjust=False).mean()
    d['kdj_j'] = 3 * d['kdj_k'] - 2 * d['kdj_d']
    d['vol_ma5'] = d['vol'].rolling(5).mean()
    d['vol_ratio'] = d['vol'] / d['vol_ma5']
    d['hl_pct'] = (d['high'] - d['low']) / d['close']
    return d

def scan_stock(symbol, model, scaler):
    """扫描单只股票"""
    fp = DATA_DIR / f'{symbol}.json'
    if not fp.exists():
        return None
    try:
        with open(fp, 'r') as f:
            data = json.load(f)
        df = pd.DataFrame(data['items'], columns=data['fields'])
        for c in ['open', 'high', 'low', 'close', 'vol']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna()
        
        # 数据倒序，需要正序排列
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        if len(df) < 60:
            return None
        
        feat = calc_features(df)
        latest = feat.iloc[-1]
        X = latest[FEATURES].values.reshape(1, -1)
        
        if np.any(np.isnan(X)):
            return None
        
        X_s = scaler.transform(X)
        prob = model.predict_proba(X_s)[0, 1]
        
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
    print('='*60)
    print('ML选股 - 主板TOP 5')
    print('='*60)
    
    # 加载模型
    model_files = sorted(MODEL_DIR.glob('ml_selector*.pkl'), reverse=True)
    with open(model_files[0], 'rb') as f:
        md = pickle.load(f)
    model = md['model']
    scaler = md['scaler']
    threshold = md.get('threshold', 0.65)
    
    print(f'模型: {model_files[0].name}')
    print(f'精确率: {md.get("high_precision", 0.8)*100:.1f}%')
    print(f'阈值: {threshold*100:.0f}%')
    
    # 主板股票 (沪市60, 深市00)
    symbols = [f.stem for f in DATA_DIR.glob('*.json') 
               if f.stem.startswith('60') or f.stem.startswith('00')]
    
    print(f'主板总数: {len(symbols)}只')
    
    # 扫描
    results = []
    for i, s in enumerate(symbols):
        r = scan_stock(s, model, scaler)
        if r:
            results.append(r)
        if (i+1) % 500 == 0:
            print(f'  扫描: {i+1}/{len(symbols)} | 发现: {len(results)}')
    
    print(f'\n扫描完成: {len(results)}只主板')
    
    # 排序
    results.sort(key=lambda x: -x['prob'])
    
    # 高置信度
    high_conf = [r for r in results if r['prob'] > threshold]
    
    print(f'\n🏆 主板TOP 5:')
    print('| 代码 | 置信度 | 现价 | RSI | 跌MA20 | KDJ-J |')
    print('|------|--------|------|-----|--------|-------|')
    for r in results[:5]:
        print(f'| {r["symbol"]} | {r["prob"]*100:.0f}% | ¥{r["close"]:.2f} | {r["rsi"]:.0f} | {r["p_ma20"]*100:.1f}% | {r["kdj_j"]:.0f} |')
    
    print(f'\n高置信度(>{threshold*100:.0f}%): {len(high_conf)}只')
    
    if high_conf:
        print('\n✅ 推荐买入:')
        for r in high_conf[:10]:
            print(f'  {r["symbol"]} | {r["prob"]*100:.0f}% | ¥{r["close"]:.2f}')
        
        # 保存结果
        pd.DataFrame(results[:20]).to_csv(
            RESULTS_DIR / 'ml_main_board_top5.csv',
            index=False
        )
    
    return results

if __name__ == '__main__':
    main()