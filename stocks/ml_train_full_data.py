#!/usr/bin/env python3
"""
ML模型训练 - 使用2022-2026完整数据
数据目录: data_history_2022_2026
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import time
import pickle
import gc
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')
TEMP_DIR = Path('/home/admin/.openclaw/workspace/stocks/temp_full')
TEMP_DIR.mkdir(exist_ok=True)

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

def calc_features(df):
    """计算技术指标"""
    d = df.copy()
    
    # 均线
    for p in [5, 10, 20, 60]:
        d[f'ma{p}'] = d['close'].rolling(p).mean()
        d[f'p_ma{p}'] = (d['close'] - d[f'ma{p}']) / d[f'ma{p}']
    
    # 斜率
    d['ma5_slope'] = d['ma5'] / d['ma5'].shift(5) - 1
    d['ma10_slope'] = d['ma10'] / d['ma10'].shift(5) - 1
    d['ma20_slope'] = d['ma20'] / d['ma20'].shift(10) - 1
    
    # 涨跌幅
    for days in [1, 5, 10, 20]:
        d[f'ret{days}'] = d['close'].pct_change(days)
    
    # 波动率
    for days in [5, 10, 20]:
        d[f'vol{days}'] = d['ret1'].rolling(days).std()
    
    # RSI
    delta = d['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    d['rsi'] = 100 - 100/(1 + gain/loss.replace(0, 0.001))
    
    # MACD
    ema12 = d['close'].ewm(span=12, adjust=False).mean()
    ema26 = d['close'].ewm(span=26, adjust=False).mean()
    d['macd_dif'] = ema12 - ema26
    d['macd_dea'] = d['macd_dif'].ewm(span=9, adjust=False).mean()
    d['macd_hist'] = (d['macd_dif'] - d['macd_dea']) * 2
    
    # KDJ
    lowv = d['low'].rolling(9).min()
    highv = d['high'].rolling(9).max()
    rsv = (d['close'] - lowv) / (highv - lowv + 0.001) * 100
    d['kdj_k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
    d['kdj_d'] = d['kdj_k'].ewm(alpha=1/3, adjust=False).mean()
    d['kdj_j'] = 3 * d['kdj_k'] - 2 * d['kdj_d']
    
    # 成交量
    d['vol_ma5'] = d['vol'].rolling(5).mean()
    d['vol_ma20'] = d['vol'].rolling(20).mean()
    d['vol_ratio'] = d['vol'] / d['vol_ma5']
    d['vol_ratio20'] = d['vol'] / d['vol_ma20']
    
    # 价格形态
    d['hl_pct'] = (d['high'] - d['low']) / d['close']
    d['hc_pct'] = (d['high'] - d['close']) / d['close']
    d['cl_pct'] = (d['close'] - d['low']) / d['close']
    
    # 布林带
    d['boll_mid'] = d['close'].rolling(20).mean()
    d['boll_std'] = d['close'].rolling(20).std()
    d['boll_upper'] = d['boll_mid'] + 2 * d['boll_std']
    d['boll_lower'] = d['boll_mid'] - 2 * d['boll_std']
    d['boll_pos'] = (d['close'] - d['boll_lower']) / (d['boll_upper'] - d['boll_lower'] + 0.001)
    
    return d

def process_batch(batch_idx, symbols, forward_days=5, profit_pct=0.03):
    """处理一批股票并保存"""
    batch_rows = []
    
    for s in symbols:
        try:
            with open(DATA_DIR / f'{s}.json', 'r') as f:
                d = json.load(f)
            
            df = pd.DataFrame(d['items'], columns=d['fields'])
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df = df.sort_values('trade_date').reset_index(drop=True)  # 正序
            
            for c in ['open', 'high', 'low', 'close', 'vol']:
                df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)
            
            df = df.dropna()
            if len(df) < 60:
                continue
            
            feat = calc_features(df)
            
            # 计算未来收益
            feat['future_ret'] = feat['close'].shift(-forward_days) / feat['close'] - 1
            feat['label'] = (feat['future_ret'] > profit_pct).astype(int)
            
            valid = feat.dropna(subset=FEATURES + ['future_ret'])
            
            if len(valid) < forward_days + 10:
                continue
            
            # 收集样本（排除最后几天）
            for idx in valid.index[:-forward_days]:
                row = {'label': feat.loc[idx, 'label']}
                for f in FEATURES:
                    row[f] = feat.loc[idx, f]
                batch_rows.append(row)
        
        except:
            pass
    
    if not batch_rows:
        return 0
    
    # 保存到临时文件
    df_batch = pd.DataFrame(batch_rows)
    temp_file = TEMP_DIR / f'batch_{batch_idx}.csv'
    df_batch.to_csv(temp_file, index=False)
    
    count = len(df_batch)
    
    del df_batch, batch_rows
    gc.collect()
    
    return count

def train_from_files():
    """从临时文件训练"""
    print('\n' + '='*60)
    print('从文件加载数据训练')
    print('='*60)
    
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    
    if not batch_files:
        print('❌ 无临时数据文件')
        return None, None
    
    print(f'批次文件: {len(batch_files)}个')
    
    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'max_depth': 5,
        'eta': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': 42
    }
    
    print('\n增量训练...')
    start = time.time()
    
    model = None
    total_samples = 0
    total_buy = 0
    
    for i, f in enumerate(batch_files):
        df = pd.read_csv(f)
        X = df[FEATURES].values
        y = df['label'].values
        
        samples = len(X)
        buys = sum(y == 1)
        total_samples += samples
        total_buy += buys
        
        # 创建DMatrix
        dmat = xgb.DMatrix(X, label=y)
        
        if model is None:
            model = xgb.train(params, dmat, num_boost_round=100)
        else:
            model = xgb.train(params, dmat, num_boost_round=20, xgb_model=model)
        
        print(f'  [{i+1}/{len(batch_files)}] {f.name} | 样本:{samples} | 买入:{buys}')
        
        del df, X, y, dmat
        gc.collect()
    
    elapsed = time.time() - start
    print(f'\n训练完成: {elapsed:.0f}s')
    print(f'总样本: {total_samples}')
    print(f'买入信号: {total_buy} ({total_buy/total_samples*100:.1f}%)')
    
    # 评估（用最后一个batch）
    df_test = pd.read_csv(batch_files[-1])
    X_test = df_test[FEATURES].values
    y_test = df_test['label'].values
    
    dtest = xgb.DMatrix(X_test)
    y_prob = model.predict(dtest)
    y_pred = (y_prob > 0.5).astype(int)
    
    acc = sum(y_pred == y_test) / len(y_test)
    
    # 最佳阈值
    best_th = 0.65
    best_prec = 0
    
    for th in [0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        mask = y_prob > th
        if sum(mask) > 10:
            prec = sum(y_test[mask] == 1) / sum(mask)
            if prec > best_prec:
                best_prec = prec
                best_th = th
    
    print(f'\n性能:')
    print(f'  准确率: {acc:.4f}')
    print(f'  最佳阈值: {best_th*100:.0f}%')
    print(f'  高置信度精确率: {best_prec:.4f}')
    
    # 特征重要性
    imp = model.get_score(importance_type='weight')
    print('\nTop 10 特征:')
    for k, v in sorted(imp.items(), key=lambda x: -x[1])[:10]:
        print(f'  {k}: {v}')
    
    return model, {
        'threshold': best_th,
        'high_precision': best_prec,
        'accuracy': acc,
        'total_samples': total_samples
    }

def main():
    print('='*60)
    print('ML训练 - 2022-2026完整数据')
    print('='*60)
    
    # 清理临时目录
    for f in TEMP_DIR.glob('batch_*.csv'):
        f.unlink()
    
    symbols = [f.stem for f in DATA_DIR.glob('*.json')]
    print(f'\n股票总数: {len(symbols)}')
    
    # 分批处理
    batch_size = 500
    num_batches = (len(symbols) + batch_size - 1) // batch_size
    
    print(f'批次大小: {batch_size}')
    print(f'总批次: {num_batches}')
    
    start = time.time()
    
    for batch_idx in range(num_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(symbols))
        batch_symbols = symbols[start_idx:end_idx]
        
        print(f'\n批次 {batch_idx+1}/{num_batches} ({start_idx}-{end_idx})')
        
        count = process_batch(batch_idx, batch_symbols)
        
        elapsed = time.time() - start
        print(f'  保存: {count}样本 | 耗时:{elapsed:.0f}s')
        
        gc.collect()
    
    elapsed_prep = time.time() - start
    print(f'\n数据准备完成: {elapsed_prep:.0f}s ({elapsed_prep/60:.1f}分钟)')
    
    # 训练
    model, config = train_from_files()
    
    if model is None:
        return
    
    # 保存模型
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_file = MODEL_DIR / f'ml_full_{timestamp}.json'
    model.save_model(model_file)
    
    config['model_file'] = str(model_file)
    config['features'] = FEATURES
    config['forward_days'] = 5
    config['profit_pct'] = 0.03
    
    config_file = MODEL_DIR / f'ml_full_config_{timestamp}.json'
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f'\n保存: {model_file}')
    print(f'保存: {config_file}')
    
    # 清理临时文件
    for f in TEMP_DIR.glob('batch_*.csv'):
        f.unlink()
    
    elapsed_total = time.time() - start
    print(f'\n总耗时: {elapsed_total:.0f}s ({elapsed_total/60:.1f}分钟)')
    
    print('\n' + '='*60)
    print('✅ 训练完成')
    print('='*60)

if __name__ == '__main__':
    main()