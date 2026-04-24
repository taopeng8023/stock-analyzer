#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 - V5 快速突破版

优化:
- 减少批次迭代 (2轮)
- 更小批次文件
- 更快学习率
- 目标10分钟内完成6个配置
"""

import pandas as pd
import numpy as np
from pathlib import Path
import time
import pickle
import gc
import sys
from datetime import datetime

from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, roc_auc_score

TEMP_DIR = Path('/home/admin/.openclaw/workspace/stocks/temp_full')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/ml_train_v5.log')

FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20',
    'ma5_slope', 'ma10_slope',
    'ret5', 'ret10', 'ret20',
    'rsi', 'macd_hist', 'kdj_k', 'kdj_d',
    'vol_ratio', 'boll_pos'
]

# 快速配置
CONFIGS = [
    {'name': 'V5_快宽', 'layers': (256, 128), 'lr': 0.003, 'alpha': 0.01, 'batch_iter': 2},
    {'name': 'V5_快深', 'layers': (128, 64, 32), 'lr': 0.005, 'alpha': 0.005, 'batch_iter': 2},
    {'name': 'V5_中正则', 'layers': (200, 100), 'lr': 0.002, 'alpha': 0.02, 'batch_iter': 2},
    {'name': 'V5_高LR', 'layers': (150, 75), 'lr': 0.01, 'alpha': 0.01, 'batch_iter': 2},
    {'name': 'V5_密集快', 'layers': (100, 100, 50), 'lr': 0.004, 'alpha': 0.008, 'batch_iter': 2},
    {'name': 'V5_最小', 'layers': (64, 32), 'lr': 0.008, 'alpha': 0.015, 'batch_iter': 3},
]

def log(msg):
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_batch(batch_file):
    cols = FEATURES + ['label']
    df = pd.read_csv(batch_file, usecols=cols)
    X = df[FEATURES].values.astype(np.float32)
    y = df['label'].values
    del df
    gc.collect()
    return X, y

def train_config(config, train_files, test_file):
    log('='*50)
    log(f'{config["name"]}: {config["layers"]} LR={config["lr"]} α={config["alpha"]}')
    log('='*50)
    
    start = time.time()
    
    X_init, y_init = load_batch(train_files[0])
    scaler = StandardScaler()
    scaler.fit(X_init)
    
    model = MLPClassifier(
        hidden_layer_sizes=config['layers'],
        activation='relu',
        solver='adam',
        alpha=config['alpha'],
        batch_size=512,  # 更大batch加速
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
    
    for batch_file in train_files[1:]:
        X_batch, y_batch = load_batch(batch_file)
        X_batch_s = scaler.transform(X_batch)
        for _ in range(config['batch_iter']):
            model.partial_fit(X_batch_s, y_batch)
        del X_batch, X_batch_s, y_batch
        gc.collect()
    
    X_test, y_test = load_batch(test_file)
    X_test_s = scaler.transform(X_test)
    
    y_prob = model.predict_proba(X_test_s)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    
    # 阈值分析
    best_prec = 0
    for th in [0.85, 0.90, 0.92]:
        mask = y_prob > th
        if sum(mask) > 10:
            th_prec = sum(y_test[mask] == 1) / sum(mask)
            if th_prec > best_prec:
                best_prec = th_prec
    
    elapsed = time.time() - start
    breakthrough = auc > 0.635
    
    log(f'时间={elapsed:.0f}s AUC={auc:.4f} {"✅突破!" if breakthrough else ""} 精确率@90={best_prec:.4f}')
    
    if breakthrough:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_file = MODEL_DIR / f'ml_nn_v5_{config["name"]}_{timestamp}.pkl'
        with open(model_file, 'wb') as f:
            pickle.dump({'model': model, 'scaler': scaler, 'features': FEATURES}, f)
        log(f'已保存: {model_file}')
    
    del X_test, X_test_s, y_test
    gc.collect()
    
    return {'name': config['name'], 'layers': config['layers'], 'time': elapsed, 'auc': auc, 'best_prec': best_prec, 'breakthrough': breakthrough}

def main():
    with open(LOG_FILE, 'w') as f:
        f.write(f'V5快速版 - {datetime.now()}\n')
    
    log('='*50)
    log('神经网络 V5 快速突破版')
    log('目标: 10分钟完成6配置')
    log('='*50)
    
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    # 使用更少批次加速
    train_files = batch_files[:6]  # 只用6个批次
    test_file = batch_files[-2]
    
    log(f'训练批次: 6 | 测试: {test_file.name}')
    
    results = []
    for config in CONFIGS:
        try:
            r = train_config(config, train_files, test_file)
            results.append(r)
        except Exception as e:
            log(f'失败: {e}')
    
    # 汇总
    results.sort(key=lambda x: x['auc'], reverse=True)
    
    log('\n结果汇总:')
    log('| 配置 | AUC | 精确率@90 | 时间 | 突破 |')
    for r in results:
        log(f'| {r["name"]} | {r["auc"]:.4f} | {r["best_prec"]:.4f} | {r["time"]:.0f}s | {"✅" if r["breakthrough"] else ""} |')
    
    best = results[0] if results else None
    if best:
        log(f'\n最佳: {best["name"]} AUC={best["auc"]:.4f}')
    
    log(f'\n完成: {datetime.now()}')

if __name__ == '__main__':
    main()