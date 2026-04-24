#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 模型继续训练 - 模型 4 和 5 (内存优化版)

优化:
- 减少样本到 50 万 (vs 70 万)
- 分批加载数据
- 及时释放内存
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import time
import pickle
import gc
import sys
from datetime import datetime
import random

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import roc_auc_score

DATA_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026')
MODEL_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/models')
LOG_FILE = Path('/Users/taopeng/.openclaw/workspace/stocks/ml_train_neural_v8_continue.log')

def log(msg):
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_and_prepare_stock(stock_file, min_records=150):
    """加载单只股票并计算 V8 特征"""
    try:
        with open(stock_file, 'r') as f:
            data = json.load(f)
        
        items = data.get('items', [])
        if len(items) < min_records:
            return None
        
        fields = data.get('fields', [])
        idx_map = {name: i for i, name in enumerate(fields)}
        
        required = ['trade_date', 'close', 'open', 'high', 'low', 'vol', 'pct_chg']
        if not all(r in idx_map for r in required):
            return None
        
        df_data = []
        for item in items:
            row = {
                'date': item[idx_map['trade_date']],
                'close': item[idx_map['close']],
                'open': item[idx_map['open']],
                'high': item[idx_map['high']],
                'low': item[idx_map['low']],
                'vol': item[idx_map['vol']],
                'pct_chg': item[idx_map['pct_chg']]
            }
            df_data.append(row)
        
        df = pd.DataFrame(df_data)
        df = df.sort_values('date').reset_index(drop=True)
        
        # 基础特征
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        df['p_ma5'] = (df['close'] - df['ma5']) / (df['ma5'] + 1e-10)
        df['p_ma10'] = (df['close'] - df['ma10']) / (df['ma10'] + 1e-10)
        df['p_ma20'] = (df['close'] - df['ma20']) / (df['ma20'] + 1e-10)
        
        df['ma5_slope'] = df['ma5'].pct_change(5)
        df['ma10_slope'] = df['ma10'].pct_change(5)
        
        df['ret5'] = df['close'].pct_change(5)
        df['ret10'] = df['close'].pct_change(10)
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - 100 / (1 + rs)
        
        df['vol_ma5'] = df['vol'].rolling(5).mean()
        df['vol_ratio'] = df['vol'] / (df['vol_ma5'] + 1e-10)
        
        df['ma20_roll'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['boll_upper'] = df['ma20_roll'] + 2 * df['std20']
        df['boll_lower'] = df['ma20_roll'] - 2 * df['std20']
        df['boll_pos'] = (df['close'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'] + 1e-10)
        
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_hist'] = df['macd'] - df['macd'].ewm(span=9, adjust=False).mean()
        
        low_9 = df['low'].rolling(9).min()
        high_9 = df['high'].rolling(9).max()
        df['kdj_k'] = 100 * (df['close'] - low_9) / (high_9 - low_9 + 1e-10)
        
        df['momentum10'] = (df['close'] / df['close'].shift(10) - 1).clip(-0.9, 5)
        
        df['volatility5'] = df['ret5'].rolling(5).std()
        df['volatility10'] = df['ret5'].rolling(10).std()
        df['vol_change'] = (df['volatility5'] / (df['volatility10'] + 1e-10)).clip(0.1, 10)
        
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        df['price_position'] = ((df['close'] - low_20) / (high_20 - low_20 + 1e-10)).clip(0, 1)
        
        df['future_return_5d'] = df['close'].shift(-5) / df['close'] - 1
        df['recent_return'] = df['close'].pct_change(3)
        df['acceleration'] = df['recent_return'] - df['recent_return'].shift(3)
        df['volatility_rank'] = df['volatility5'].rolling(60).rank(pct=True)
        df['up_days_ratio'] = (df['pct_chg'] > 0).rolling(10).mean()
        df['momentum_strength'] = (df['ret5'] - df['ret10']).clip(-0.5, 0.5)
        
        # V8 新增
        df['vol_price_corr'] = df['vol'].rolling(20).corr(df['close']).fillna(0).clip(-1, 1)
        df['vol_trend'] = (df['vol_ma5'] / (df['vol'].rolling(20).mean() + 1e-10)).clip(0.5, 2.0)
        df['momentum_accel'] = (df['ret5'] - df['ret5'].shift(5)).clip(-0.5, 0.5)
        df['trend_strength'] = (df['ma5'] - df['ma20']) / (df['ma20'] + 1e-10)
        df['volatility_trend'] = (df['volatility5'] / (df['volatility5'].shift(5) + 1e-10)).clip(0.5, 2.0)
        df['range_ratio'] = (df['high'] - df['low']) / (df['close'] + 1e-10)
        df['money_flow_proxy'] = (df['vol'] * df['pct_chg'] / 1e6).clip(-100, 100)
        df['money_flow_ma'] = df['money_flow_proxy'].rolling(5).mean()
        
        df['label'] = (df['future_return_5d'] > 0.05).astype(int)
        
        feature_cols = ['p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
                       'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
                       'momentum10', 'vol_change', 'price_position',
                       'volatility_rank', 'recent_return', 'acceleration',
                       'up_days_ratio', 'momentum_strength',
                       'vol_price_corr', 'vol_trend', 'momentum_accel', 'trend_strength',
                       'volatility_trend', 'range_ratio', 'money_flow_proxy', 'money_flow_ma']
        
        df = df.dropna(subset=feature_cols + ['label'])
        
        if len(df) < 80:
            return None
        
        return df[feature_cols + ['label']]
    
    except Exception as e:
        return None

def prepare_data_lite():
    """准备轻量数据 (50 万样本)"""
    log('='*60)
    log('V8 继续训练 - 内存优化版')
    log('='*60)
    
    stock_files = list(DATA_DIR.glob('*.json'))
    n_stocks = min(1200, len(stock_files))  # 减少到 1200 只
    selected_files = random.sample(stock_files, n_stocks)
    
    log(f'选择 {n_stocks} 只股票')
    
    all_dfs = []
    batch_size = 200
    
    for i, stock_file in enumerate(selected_files):
        df = load_and_prepare_stock(stock_file)
        if df is None:
            continue
        
        all_dfs.append(df)
        
        if (i + 1) % batch_size == 0:
            log(f'已加载 {i+1}/{n_stocks} 只股票')
            gc.collect()
    
    log(f'\n合并数据...')
    combined = pd.concat(all_dfs, ignore_index=True)
    log(f'总样本数：{len(combined):,}')
    
    positives = combined[combined['label'] == 1]
    negatives = combined[combined['label'] == 0]
    
    # 50 万样本
    n_pos = min(len(positives), 125000)
    n_neg = min(len(negatives), 375000)
    
    pos_sample = positives.sample(n=n_pos, random_state=42)
    neg_sample = negatives.sample(n=n_neg, random_state=42)
    
    sampled = pd.concat([pos_sample, neg_sample], ignore_index=True)
    sampled = sampled.sample(frac=1, random_state=42).reset_index(drop=True)
    
    log(f'采样后：{len(sampled):,} 条')
    
    feature_cols = ['p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
                   'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
                   'momentum10', 'vol_change', 'price_position',
                   'volatility_rank', 'recent_return', 'acceleration',
                   'up_days_ratio', 'momentum_strength',
                   'vol_price_corr', 'vol_trend', 'momentum_accel', 'trend_strength',
                   'volatility_trend', 'range_ratio', 'money_flow_proxy', 'money_flow_ma']
    
    X = sampled[feature_cols].values.astype(np.float32)
    y = sampled['label'].values
    
    # 清理异常值
    X = np.nan_to_num(X, nan=0.0, posinf=10.0, neginf=-10.0)
    
    log(f'特征矩阵：{X.shape} ({X.nbytes / 1024**2:.1f}MB)')
    
    # 划分数据集
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)
    
    log(f'训练集：{len(X_train):,}')
    log(f'验证集：{len(X_val):,}')
    log(f'测试集：{len(X_test):,}')
    
    # 标准化
    log('标准化...')
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)
    
    # 保存
    temp_dir = MODEL_DIR / 'temp_v8_continue'
    temp_dir.mkdir(exist_ok=True)
    
    np.save(temp_dir / 'X_train.npy', X_train_s)
    np.save(temp_dir / 'X_val.npy', X_val_s)
    np.save(temp_dir / 'X_test.npy', X_test_s)
    np.save(temp_dir / 'y_train.npy', y_train)
    np.save(temp_dir / 'y_val.npy', y_val)
    np.save(temp_dir / 'y_test.npy', y_test)
    
    with open(temp_dir / 'scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    
    log(f'临时数据：{temp_dir}')
    
    del X, y, X_train_s, X_val_s, X_test_s, combined, all_dfs, sampled
    gc.collect()
    
    return temp_dir

def train_model(temp_dir, seed, model_idx):
    """训练单个模型"""
    log(f'\n加载数据...')
    X_train = np.load(temp_dir / 'X_train.npy')
    X_val = np.load(temp_dir / 'X_val.npy')
    y_train = np.load(temp_dir / 'y_train.npy')
    y_val = np.load(temp_dir / 'y_val.npy')
    
    log(f'训练模型 {model_idx} (seed={seed})...')
    
    model = MLPClassifier(
        hidden_layer_sizes=(256, 128, 64),
        activation='relu',
        solver='adam',
        alpha=0.001,
        batch_size=256,
        learning_rate='adaptive',
        learning_rate_init=0.0003,
        max_iter=200,
        random_state=seed,
        verbose=False,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=20
    )
    
    model.fit(X_train, y_train)
    
    y_val_prob = model.predict_proba(X_val)[:, 1]
    val_auc = roc_auc_score(y_val, y_val_prob)
    
    log(f'  AUC={val_auc:.4f}, 迭代={model.n_iter_}')
    
    model_path = MODEL_DIR / f'ml_nn_v8_model{model_idx}_seed{seed}.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'seed': seed,
            'val_auc': val_auc,
            'model_idx': model_idx
        }, f)
    
    log(f'  已保存：{model_path.name}')
    
    del X_train, X_val, y_train, y_val, model
    gc.collect()
    
    return val_auc

def main():
    with open(LOG_FILE, 'w') as f:
        f.write(f'V8 继续训练 - {datetime.now()}\n\n')
    
    start_time = time.time()
    
    # 准备数据
    temp_dir = prepare_data_lite()
    
    # 训练模型 4 和 5
    log('='*60)
    log('训练模型 4 和 5...')
    log('='*60)
    
    results = []
    
    # 模型 4
    auc4 = train_model(temp_dir, 789, 4)
    results.append(auc4)
    
    # 模型 5
    auc5 = train_model(temp_dir, 1024, 5)
    results.append(auc5)
    
    log(f'\n{">"*60}')
    log(f'训练完成！')
    log(f'模型 4 AUC: {auc4:.4f}')
    log(f'模型 5 AUC: {auc5:.4f}')
    log(f'平均 AUC: {np.mean(results):.4f}')
    log(f'总耗时：{time.time() - start_time:.0f}s')
    log(f'{"="*60}')
    
    # 清理
    import shutil
    log('\n清理临时文件...')
    shutil.rmtree(temp_dir)
    log(f'已删除：{temp_dir}')

if __name__ == '__main__':
    main()
