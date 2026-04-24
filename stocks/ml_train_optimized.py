#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 - 优化版测试

基于上轮结果优化:
- 低学习率效果最好 -> 测试更小学习率
- 大网络AUC最高 -> 测试更大网络
- 核心特征时间短 -> 测试更多特征组合
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
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/ml_train_optimized.log')

# 不同特征集
FEATURES_V1 = ['p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 'ret5', 'ret10', 'ret20', 'rsi', 'macd_hist', 'kdj_k', 'kdj_d', 'vol_ratio', 'boll_pos']
FEATURES_V2 = ['p_ma5', 'p_ma10', 'p_ma20', 'p_ma60', 'ret5', 'ret10', 'ret20', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos']
FEATURES_V3 = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'ret10', 'rsi', 'macd_hist', 'vol_ratio', 'boll_pos', 'hl_pct', 'hc_pct']

# 优化配置
CONFIGS = [
    {'name': '超大网络', 'layers': (512, 256, 128), 'lr': 0.0005, 'features': FEATURES_V1, 'batch_iter': 2},
    {'name': '超低学习率', 'layers': (256, 128, 64), 'lr': 0.0001, 'features': FEATURES_V1, 'batch_iter': 4},
    {'name': '极致深度', 'layers': (64, 64, 64, 64, 32), 'lr': 0.001, 'features': FEATURES_V1, 'batch_iter': 2},
    {'name': '特征V2', 'layers': (256, 128, 64), 'lr': 0.001, 'features': FEATURES_V2, 'batch_iter': 2},
    {'name': '特征V3', 'layers': (128, 64), 'lr': 0.002, 'features': FEATURES_V3, 'batch_iter': 3},
    {'name': '快速配置', 'layers': (100, 50), 'lr': 0.005, 'features': FEATURES_V2, 'batch_iter': 2},
]

def log(msg):
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_batch(batch_file, features):
    cols = features + ['label']
    df = pd.read_csv(batch_file, usecols=cols)
    X = df[features].values.astype(np.float32)
    y = df['label'].values
    del df
    gc.collect()
    return X, y

def train_config(config, train_files, test_file):
    log('='*60)
    log(f'配置: {config["name"]}')
    log(f'  网络: {config["layers"]} | LR: {config["lr"]} | 特征: {len(config["features"])}')
    log('='*60)
    
    start = time.time()
    features = config['features']
    
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
    
    for batch_file in train_files[1:]:
        X_batch, y_batch = load_batch(batch_file, features)
        X_batch_s = scaler.transform(X_batch)
        for _ in range(config['batch_iter']):
            model.partial_fit(X_batch_s, y_batch)
        del X_batch, X_batch_s, y_batch
        gc.collect()
    
    X_test, y_test = load_batch(test_file, features)
    X_test_s = scaler.transform(X_test)
    
    y_prob = model.predict_proba(X_test_s)[:, 1]
    y_pred = model.predict(X_test_s)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    best_th = 0.85
    best_prec = 0
    for th in [0.80, 0.85, 0.90]:
        mask = y_prob > th
        if sum(mask) > 10:
            th_prec = sum(y_test[mask] == 1) / sum(mask)
            if th_prec > best_prec:
                best_prec = th_prec
                best_th = th
    
    elapsed = time.time() - start
    
    log(f'结果: 时间={elapsed:.0f}s | AUC={auc:.4f} | 精确率={prec:.4f}')
    log(f'最佳阈值: {best_th*100:.0f}% -> {best_prec:.4f}')
    
    # 保存最佳模型
    if auc > 0.63:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_file = MODEL_DIR / f'ml_nn_opt_{config["name"]}_{timestamp}.pkl'
        with open(model_file, 'wb') as f:
            pickle.dump({'model': model, 'scaler': scaler, 'features': features}, f)
        log(f'已保存: {model_file}')
    
    del X_test, X_test_s, y_test
    gc.collect()
    
    return {
        'name': config['name'],
        'layers': config['layers'],
        'lr': config['lr'],
        'features': len(features),
        'time': elapsed,
        'auc': auc,
        'best_threshold': best_th,
        'best_precision': best_prec
    }

def main():
    with open(LOG_FILE, 'w') as f:
        f.write(f'优化测试 - {datetime.now()}\n\n')
    
    log('='*60)
    log('神经网络选股模型 - 优化版测试')
    log('='*60)
    
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    test_file = batch_files[-2]
    train_files = batch_files[:-2]
    
    log(f'训练批次: {len(train_files)} | 测试: {test_file.name}')
    
    results = []
    for config in CONFIGS:
        try:
            r = train_config(config, train_files, test_file)
            results.append(r)
            log('')
        except Exception as e:
            log(f'失败: {e}\n')
    
    # 汇总
    log('='*60)
    log('结果汇总 (按AUC排序)')
    log('='*60)
    
    results.sort(key=lambda x: x['auc'], reverse=True)
    
    log('| 排名 | 配置 | 网络 | 时间 | AUC | 最佳精确率 |')
    log('|------|------|------|------|-----|-----------|')
    
    for i, r in enumerate(results, 1):
        layers_str = '-'.join(str(x) for x in r['layers'])
        medal = '🥇' if i==1 else ('🥈' if i==2 else ('🥉' if i==3 else f'{i}'))
        log(f'| {medal} | {r["name"]} | {layers_str} | {r["time"]:.0f}s | {r["auc"]:.4f} | {r["best_precision"]:.4f} |')
    
    if results:
        best = results[0]
        log(f'\n🏆 最佳: {best["name"]} (AUC={best["auc"]:.4f}, 精确率={best["best_precision"]:.4f})')
    
    log(f'\n完成: {datetime.now()}')

if __name__ == '__main__':
    main()