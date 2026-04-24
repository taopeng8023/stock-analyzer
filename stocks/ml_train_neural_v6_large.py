#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 V6 - 更大规模训练

优化方向:
- 增加股票数量：1000 → 2500 只
- 增加样本数：50 万 → 100 万条
- 保持 5 模型集成架构
- 使用更高效的内存管理
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
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

DATA_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026')
MODEL_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/models')
LOG_FILE = Path('/Users/taopeng/.openclaw/workspace/stocks/ml_train_neural_v6_large.log')

def log(msg):
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_and_prepare_stock(stock_file, min_records=150):
    """加载单只股票并计算 15 个优化特征"""
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
        
        # ===== 基础特征 =====
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
        
        # ===== V5 有效特征 (精简到 3 个) =====
        df['momentum10'] = (df['close'] / df['close'].shift(10) - 1).clip(-0.9, 5)
        
        df['volatility5'] = df['ret5'].rolling(5).std()
        df['volatility10'] = df['ret5'].rolling(10).std()
        df['vol_change'] = (df['volatility5'] / (df['volatility10'] + 1e-10)).clip(0.1, 10)
        
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        df['price_position'] = ((df['close'] - low_20) / (high_20 - low_20 + 1e-10)).clip(0, 1)
        
        # 标签：未来 5 天涨幅是否超过 3%
        df['future_return'] = df['close'].shift(-5) / df['close'] - 1
        df['label'] = (df['future_return'] > 0.03).astype(int)
        
        # 删除 NaN
        feature_cols = ['p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
                       'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
                       'momentum10', 'vol_change', 'price_position']
        df = df.dropna(subset=feature_cols + ['label'])
        
        if len(df) < 80:
            return None
        
        return df[feature_cols + ['label']]
    
    except Exception as e:
        return None

def prepare_and_train():
    """准备数据并逐个训练模型"""
    log('='*60)
    log('神经网络选股模型 V6 - 更大规模训练 (2500 只股票)')
    log('='*60)
    
    start_time = time.time()
    
    # 准备数据
    log('\n准备训练数据...')
    stock_files = list(DATA_DIR.glob('*.json'))
    log(f'发现 {len(stock_files):,} 只股票数据')
    
    n_stocks = min(2500, len(stock_files))  # 增加到 2500 只
    selected_files = random.sample(stock_files, n_stocks)
    log(f'选择 {n_stocks} 只股票进行训练')
    
    all_dfs = []
    batch_size = 500
    
    for i, stock_file in enumerate(selected_files):
        df = load_and_prepare_stock(stock_file)
        if df is None:
            continue
        
        all_dfs.append(df)
        
        if (i + 1) % batch_size == 0:
            log(f'已加载 {i+1}/{n_stocks} 只股票，累计 {sum(len(d) for d in all_dfs):,} 条样本')
            gc.collect()
    
    log(f'\n合并数据...')
    combined = pd.concat(all_dfs, ignore_index=True)
    log(f'总样本数：{len(combined):,}')
    log(f'正样本比例：{combined["label"].mean()*100:.1f}%')
    
    positives = combined[combined['label'] == 1]
    negatives = combined[combined['label'] == 0]
    
    n_pos = min(len(positives), 330000)  # 增加到 100 万样本
    n_neg = min(len(negatives), 670000)
    
    pos_sample = positives.sample(n=n_pos, random_state=42)
    neg_sample = negatives.sample(n=n_neg, random_state=42)
    
    sampled = pd.concat([pos_sample, neg_sample], ignore_index=True)
    sampled = sampled.sample(frac=1, random_state=42).reset_index(drop=True)
    
    log(f'采样后：{len(sampled):,} 条 (正样本：{sampled["label"].mean()*100:.1f}%)')
    
    feature_cols = ['p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
                   'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
                   'momentum10', 'vol_change', 'price_position']
    
    X = sampled[feature_cols].values.astype(np.float32)
    y = sampled['label'].values
    
    log(f'特征矩阵：{X.shape}')
    log(f'特征内存：{X.nbytes / 1024**2:.1f}MB')
    
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full, y_train_full, test_size=0.15, random_state=42, stratify=y_train_full
    )
    
    log(f'训练集：{len(X_train):,}')
    log(f'验证集：{len(X_val):,}')
    log(f'测试集：{len(X_test):,}')
    
    log('标准化...')
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)
    
    # 保存临时数据
    temp_dir = MODEL_DIR / 'temp_v6_large'
    temp_dir.mkdir(exist_ok=True)
    
    np.save(temp_dir / 'X_train.npy', X_train_s)
    np.save(temp_dir / 'X_val.npy', X_val_s)
    np.save(temp_dir / 'X_test.npy', X_test_s)
    np.save(temp_dir / 'y_train.npy', y_train)
    np.save(temp_dir / 'y_val.npy', y_val)
    np.save(temp_dir / 'y_test.npy', y_test)
    
    with open(temp_dir / 'scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    with open(temp_dir / 'features.json', 'w') as f:
        json.dump(feature_cols, f)
    
    log(f'临时数据已保存到：{temp_dir}')
    
    # 释放内存
    del X, y, X_train_s, X_val_s, X_test_s, combined, all_dfs, sampled
    gc.collect()
    
    # 训练 5 个模型
    log('='*60)
    log('分批训练 5 个模型...')
    log('='*60)
    
    seeds = [42, 123, 456, 789, 1024]
    model_paths = []
    
    for i, seed in enumerate(seeds):
        model_idx = i + 1
        model_path = MODEL_DIR / f'ml_nn_v6_large_model{model_idx}_seed{seed}.pkl'
        model_paths.append(model_path)
        
        log(f'\n加载数据...')
        X_train = np.load(temp_dir / 'X_train.npy')
        X_val = np.load(temp_dir / 'X_val.npy')
        y_train = np.load(temp_dir / 'y_train.npy')
        y_val = np.load(temp_dir / 'y_val.npy')
        
        log(f'训练模型 {model_idx}/5 (seed={seed})...')
        
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
        
        log(f'  模型{model_idx}: AUC={val_auc:.4f}, 迭代={model.n_iter_}')
        
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': model,
                'seed': seed,
                'val_auc': val_auc,
                'model_idx': model_idx
            }, f)
        
        log(f'  模型已保存：{model_path}')
        
        # 释放内存
        del X_train, X_val, y_train, y_val, model
        gc.collect()
        
        log(f'模型 {model_idx}/5 完成，AUC={val_auc:.4f}')
    
    log(f'\n5 个模型训练完成!')
    log(f'模型文件:')
    for p in model_paths:
        log(f'  - {p.name}')
    
    # 评估集成
    log('\n' + '='*60)
    log('评估集成模型...')
    log('='*60)
    
    X_test = np.load(temp_dir / 'X_test.npy')
    y_test = np.load(temp_dir / 'y_test.npy')
    
    y_test_probs = []
    aucs = []
    
    for model_path in model_paths:
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        model = data['model']
        prob = model.predict_proba(X_test)[:, 1]
        y_test_probs.append(prob)
        aucs.append(data['val_auc'])
    
    y_test_prob_ensemble = np.mean(y_test_probs, axis=0)
    y_test_pred_ensemble = (y_test_prob_ensemble >= 0.5).astype(int)
    
    acc = accuracy_score(y_test, y_test_pred_ensemble)
    prec = precision_score(y_test, y_test_pred_ensemble, zero_division=0)
    rec = recall_score(y_test, y_test_pred_ensemble, zero_division=0)
    f1 = f1_score(y_test, y_test_pred_ensemble, zero_division=0)
    auc = roc_auc_score(y_test, y_test_prob_ensemble)
    
    log(f'\n集成模型评估:')
    log(f'准确率：{acc:.4f}')
    log(f'精确率：{prec:.4f}')
    log(f'召回率：{rec:.4f}')
    log(f'F1: {f1:.4f}')
    log(f'AUC: {auc:.4f}')
    log(f'单模型 AUC: {[f"{a:.4f}" for a in aucs]}')
    log(f'平均 AUC: {np.mean(aucs):.4f} ± {np.std(aucs):.4f}')
    
    log('\n| 阈值 | 覆盖 | 精确率 |')
    best_threshold = 0.5
    best_prec = 0
    for threshold in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        high_conf = (y_test_prob_ensemble >= threshold).sum()
        if high_conf > 0:
            conf_prec = precision_score(y_test, y_test_prob_ensemble >= threshold, zero_division=0)
            log(f'| {int(threshold*100)}% | {high_conf} | {conf_prec:.4f} |')
            if conf_prec > best_prec and high_conf >= 50:
                best_prec = conf_prec
                best_threshold = threshold
    
    log(f'\n最佳阈值：{int(best_threshold*100)}% (精确率：{best_prec:.4f})')
    
    # 保存集成配置
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ensemble_config = {
        'model_paths': [str(p) for p in model_paths],
        'scaler_path': str(temp_dir / 'scaler.pkl'),
        'features_path': str(temp_dir / 'features.json'),
        'aucs': aucs,
        'avg_auc': float(np.mean(aucs)),
        'test_auc': float(auc),
        'best_threshold': best_threshold,
        'best_prec': float(best_prec),
        'timestamp': timestamp,
        'n_stocks': n_stocks,
        'n_samples': len(sampled)
    }
    
    config_path = MODEL_DIR / f'ml_nn_v6_large_ensemble_config_{timestamp}.json'
    with open(config_path, 'w') as f:
        json.dump(ensemble_config, f, indent=2)
    
    log(f'\n集成配置已保存：{config_path}')
    
    # 清理临时文件
    log('\n清理临时文件...')
    import shutil
    shutil.rmtree(temp_dir)
    log(f'临时目录已删除：{temp_dir}')
    
    log('='*60)
    log(f'总耗时：{time.time() - start_time:.0f}s')
    log(f'完成时间：{datetime.now()}')
    log('='*60)

if __name__ == '__main__':
    main = prepare_and_train
    main()
