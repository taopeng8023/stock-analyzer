#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML每日选股系统 - 内存优化版
分批扫描，避免内存溢出
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import warnings
from pathlib import Path
import pickle

warnings.filterwarnings('ignore')

CACHE_DIR = Path(__file__).parent / 'data_tushare'
MODEL_DIR = Path(__file__).parent / 'models'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'

# 特征列表（简化版）
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
    """加载模型"""
    model_files = sorted(MODEL_DIR.glob('ml_selector_*.pkl'), reverse=True)
    if not model_files:
        return None
    
    with open(model_files[0], 'rb') as f:
        data = pickle.load(f)
    
    data['threshold'] = data.get('threshold', 0.65)
    data['features'] = data.get('features', FEATURES)
    
    print(f"✅ 模型: {model_files[0].name}")
    print(f"  阈值: {data['threshold']*100:.0f}%")
    
    return data


def calc_features(df):
    """计算特征"""
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
    """扫描单只股票"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
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
                'close': latest['close'],
                'rsi': latest['rsi'],
                'p_ma20': (latest['close'] - latest['ma20']) / latest['ma20']
            }
        
        return None
    
    except:
        return None


def main():
    """主流程"""
    print('='*80)
    print('ML每日选股系统')
    print('='*80)
    
    # 加载模型
    model_data = load_model()
    if not model_data:
        return
    
    model = model_data['model']
    scaler = model_data['scaler']
    features = model_data['features']
    threshold = model_data['threshold']
    
    # 加载股票列表
    symbols = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    print(f"\n📊 股票池: {len(symbols)} 只")
    print(f"  阈值: {threshold*100:.0f}%")
    
    # 分批扫描
    results = []
    batch_size = 500
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        
        for symbol in batch:
            result = scan_stock(symbol, model, scaler, features, threshold)
            if result:
                results.append(result)
        
        print(f"  ⏳ {min(i+batch_size, len(symbols))}/{len(symbols)} | 发现:{len(results)}")
    
    # 排序
    results.sort(key=lambda x: -x['prob'])
    
    # 输出
    print("\n" + "="*80)
    print(f"🤖 ML选股结果 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*80)
    
    if results:
        print(f"\n发现高置信度股票: {len(results)} 只")
        print(f"\n🏆 TOP 10:")
        print("| 代码 | 置信度 | 现价 | RSI | 跌MA20 |")
        print("|------|--------|------|-----|--------|")
        
        for r in results[:10]:
            print(f"| {r['symbol']} | {r['prob']*100:.0f}% | {r['close']:.2f} | {r['rsi']:.0f} | {r['p_ma20']*100:.1f}% |")
        
        # 保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pd.DataFrame(results).to_csv(
            RESULTS_DIR / f'ml_pick_{timestamp}.csv',
            index=False, encoding='utf-8-sig'
        )
        print(f"\n💾 保存: ml_pick_{timestamp}.csv")
    else:
        print("\n未发现高置信度买入信号")
    
    return results


if __name__ == '__main__':
    main()