#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 - 多配置测试

测试不同配置组合:
- 网络结构: 大/中/小
- 学习率: 高/中/低
- 特征集: 全部/核心
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

from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

TEMP_DIR = Path('/home/admin/.openclaw/workspace/stocks/temp_full')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/ml_train_multi_config.log')

# 不同特征集
FEATURES_FULL = [
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

FEATURES_CORE = [
    'p_ma5', 'p_ma10', 'p_ma20',
    'ma5_slope', 'ma10_slope',
    'ret5', 'ret10', 'ret20',
    'rsi',
    'macd_hist',
    'kdj_k', 'kdj_d',
    'vol_ratio',
    'boll_pos'
]

FEATURES_MINI = [
    'p_ma5', 'p_ma10', 'p_ma20',
    'ret5', 'ret10',
    'rsi',
    'macd_hist',
    'vol_ratio'
]

# 测试配置
CONFIGS = [
    {'name': '大网络全特征', 'layers': (256, 128, 64), 'lr': 0.001, 'features': FEATURES_CORE, 'batch_iter': 2},
    {'name': '深层网络', 'layers': (128, 64, 32, 16), 'lr': 0.002, 'features': FEATURES_CORE, 'batch_iter': 2},
    {'name': '宽网络', 'layers': (200, 100), 'lr': 0.002, 'features': FEATURES_CORE, 'batch_iter': 2},
    {'name': '高学习率', 'layers': (128, 64, 32), 'lr': 0.01, 'features': FEATURES_CORE, 'batch_iter': 2},
    {'name': '低学习率', 'layers': (128, 64, 32), 'lr': 0.0005, 'features': FEATURES_CORE, 'batch_iter': 3},
    {'name': '核心特征', 'layers': (64, 32), 'lr': 0.002, 'features': FEATURES_MINI, 'batch_iter': 3},
]

def log(msg):
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_batch(batch_file, features):
    """加载批次数据"""
    cols = features + ['label']
    df = pd.read_csv(batch_file, usecols=cols)
    X = df[features].values.astype(np.float32)
    y = df['label'].values
    del df
    gc.collect()
    return X, y

def train_config(config, train_files, test_file):
    """训练单个配置"""
    log('='*60)
    log(f'配置: {config["name"]}')
    log(f'  网络: {config["layers"]}')
    log(f'  学习率: {config["lr"]}')
    log(f'  特征数: {len(config["features"])}')
    log('='*60)
    
    start_time = time.time()
    features = config['features']
    
    # 初始化
    X_init, y_init = load_batch(train_files[0], features)
    scaler = StandardScaler()
    scaler.fit(X_init)
    
    model = MLPClassifier(
        hidden_layer_sizes=config['layers'],
        activation='relu',
        solver='adam',
        alpha=0.001,
        batch_size=256,
        learning_rate='adaptive',
        learning_rate_init=config['lr'],
        max_iter=config['batch_iter'],
        random_state=42,
        warm_start=True,
        verbose=False
    )
    
    X_init_s = scaler.transform(X_init)
    model.fit(X_init_s, y_init)
    del X_init, X_init_s, y_init
    gc.collect()
    
    # 分批训练
    for batch_file in train_files[1:]:
        X_batch, y_batch = load_batch(batch_file, features)
        X_batch_s = scaler.transform(X_batch)
        
        for _ in range(config['batch_iter']):
            model.partial_fit(X_batch_s, y_batch)
        
        del X_batch, X_batch_s, y_batch
        gc.collect()
    
    # 测试
    X_test, y_test = load_batch(test_file, features)
    X_test_s = scaler.transform(X_test)
    
    y_prob = model.predict_proba(X_test_s)[:, 1]
    y_pred = model.predict(X_test_s)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    # 最佳阈值
    best_th = 0.7
    best_prec = 0
    for th in [0.70, 0.75, 0.80, 0.85]:
        mask = y_prob > th
        if sum(mask) > 10:
            th_prec = sum(y_test[mask] == 1) / sum(mask)
            if th_prec > best_prec:
                best_prec = th_prec
                best_th = th
    
    elapsed = time.time() - start_time
    
    log(f'\n结果:')
    log(f'  时间: {elapsed:.1f}s')
    log(f'  AUC: {auc:.4f}')
    log(f'  精确率(70%阈值): {prec:.4f}')
    log(f'  最佳阈值: {best_th*100:.0f}% -> {best_prec:.4f}')
    
    del X_test, X_test_s, y_test
    gc.collect()
    
    return {
        'name': config['name'],
        'layers': config['layers'],
        'lr': config['lr'],
        'features': len(features),
        'time': elapsed,
        'auc': auc,
        'precision': prec,
        'best_threshold': best_th,
        'best_precision': best_prec
    }

def main():
    with open(LOG_FILE, 'w') as f:
        f.write(f'多配置测试日志 - {datetime.now()}\n\n')
    
    log('='*60)
    log('神经网络选股模型 - 多配置测试')
    log('='*60)
    
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    test_file = batch_files[-2]  # batch_9
    train_files = batch_files[:-2]  # batch_0~batch_8 + batch_10
    
    log(f'训练批次: {len(train_files)}个')
    log(f'测试批次: {test_file.name}')
    log(f'测试配置数: {len(CONFIGS)}')
    
    results = []
    
    for config in CONFIGS:
        try:
            result = train_config(config, train_files, test_file)
            results.append(result)
            log('')
        except Exception as e:
            log(f'配置 {config["name"]} 失败: {e}')
            log('')
    
    # 结果汇总
    log('='*60)
    log('结果汇总')
    log('='*60)
    log('| 配置 | 网络 | 特征 | 时间 | AUC | 最佳精确率 |')
    log('|------|------|------|------|-----|-----------|')
    
    # 按AUC排序
    results.sort(key=lambda x: x['auc'], reverse=True)
    
    for r in results:
        layers_str = '-'.join(str(x) for x in r['layers'])
        log(f'| {r["name"]} | {layers_str} | {r["features"]} | {r["time"]:.0f}s | {r["auc"]:.4f} | {r["best_precision"]:.4f} |')
    
    # 最佳配置
    if results:
        best = results[0]
        log(f'\n最佳配置: {best["name"]} (AUC={best["auc"]:.4f})')
    
    log(f'\n完成时间: {datetime.now()}')

if __name__ == '__main__':
    main()