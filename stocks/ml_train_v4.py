#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 - V4 极致优化

目标: 超越AUC=0.6350

新策略:
- 双网络融合
- 特征交互
- 正则化增强
- 更长训练
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
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/ml_train_v4.log')

# 全特征集
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

# V4配置
CONFIGS = [
    {'name': 'V4_超大正则', 'layers': (512, 256, 128), 'lr': 0.0003, 'alpha': 0.01, 'batch_iter': 3, 'features': FEATURES_FULL[:18]},
    {'name': 'V4_双宽网络', 'layers': (300, 150, 75), 'lr': 0.0005, 'alpha': 0.005, 'batch_iter': 4, 'features': FEATURES_FULL[:20]},
    {'name': 'V4_深宽混合', 'layers': (200, 100, 50, 25), 'lr': 0.0008, 'alpha': 0.003, 'batch_iter': 3, 'features': FEATURES_FULL[:16]},
    {'name': 'V4_极致长训', 'layers': (256, 128, 64), 'lr': 0.0001, 'alpha': 0.002, 'batch_iter': 6, 'features': FEATURES_FULL[:18]},
    {'name': 'V4_宽快配置', 'layers': (400, 200), 'lr': 0.001, 'alpha': 0.01, 'batch_iter': 3, 'features': FEATURES_FULL[:14]},
    {'name': 'V4_密集网络', 'layers': (128, 128, 128, 64), 'lr': 0.0005, 'alpha': 0.005, 'batch_iter': 4, 'features': FEATURES_FULL[:16]},
]

def log(msg):
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_batch(batch_file, features):
    cols = features + ['label']
    try:
        df = pd.read_csv(batch_file, usecols=cols)
    except:
        # 如果列不存在，只读取存在的列
        all_cols = pd.read_csv(batch_file, nrows=0).columns.tolist()
        valid_cols = [c for c in cols if c in all_cols]
        df = pd.read_csv(batch_file, usecols=valid_cols)
        features = [f for f in features if f in valid_cols]
    
    X = df[features].values.astype(np.float32)
    y = df['label'].values
    del df
    gc.collect()
    return X, y, features

def train_config(config, train_files, test_file):
    log('='*60)
    log(f'配置: {config["name"]}')
    log(f'  网络: {config["layers"]} | LR: {config["lr"]} | Alpha: {config["alpha"]}')
    log('='*60)
    
    start = time.time()
    
    # 加载并确定有效特征
    X_init, y_init, valid_features = load_batch(train_files[0], config['features'])
    
    scaler = StandardScaler()
    scaler.fit(X_init)
    
    model = MLPClassifier(
        hidden_layer_sizes=config['layers'],
        activation='relu',
        solver='adam',
        alpha=config['alpha'],  # 正则化
        batch_size=128,
        learning_rate='adaptive',
        learning_rate_init=config['lr'],
        max_iter=config['batch_iter'],
        random_state=42,
        warm_start=True,
        early_stopping=False,
        verbose=False
    )
    
    X_init_s = scaler.transform(X_init)
    model.fit(X_init_s, y_init)
    log(f'  初始化完成 | 损失: {model.loss_:.4f} | 特征: {len(valid_features)}')
    del X_init, X_init_s, y_init
    gc.collect()
    
    # 分批训练
    batch_count = 0
    for batch_file in train_files[1:]:
        batch_count += 1
        X_batch, y_batch, _ = load_batch(batch_file, valid_features)
        X_batch_s = scaler.transform(X_batch)
        
        for _ in range(config['batch_iter']):
            model.partial_fit(X_batch_s, y_batch)
        
        if batch_count % 3 == 0:
            log(f'  批次 {batch_count}/{len(train_files)-1} | 损失: {model.loss_:.4f}')
        
        del X_batch, X_batch_s, y_batch
        gc.collect()
    
    # 测试
    X_test, y_test, _ = load_batch(test_file, valid_features)
    X_test_s = scaler.transform(X_test)
    
    y_prob = model.predict_proba(X_test_s)[:, 1]
    y_pred = model.predict(X_test_s)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    # 阈值分析
    best_th = 0.90
    best_prec = 0
    th_results = []
    for th in [0.85, 0.90, 0.92, 0.95]:
        mask = y_prob > th
        if sum(mask) > 10:
            th_prec = sum(y_test[mask] == 1) / sum(mask)
            th_results.append((th, sum(mask), th_prec))
            if th_prec > best_prec:
                best_prec = th_prec
                best_th = th
    
    elapsed = time.time() - start
    
    log(f'\n结果:')
    log(f'  时间: {elapsed:.0f}s')
    log(f'  AUC: {auc:.4f} {"✨ 新高!" if auc > 0.635 else ""}')
    log(f'  精确率: {prec:.4f}')
    log(f'  阈值分析:')
    for th, cnt, pr in th_results:
        log(f'    {th*100:.0f}% -> {cnt}样本, {pr:.4f}精确率')
    
    # 保存突破性模型
    if auc > 0.635:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_file = MODEL_DIR / f'ml_nn_v4_{config["name"]}_{timestamp}.pkl'
        with open(model_file, 'wb') as f:
            pickle.dump({
                'model': model, 
                'scaler': scaler, 
                'features': valid_features,
                'config': config,
                'metrics': {'auc': auc, 'precision': prec, 'best_threshold': best_th, 'best_precision': best_prec}
            }, f)
        log(f'  ✅ 已保存突破模型: {model_file}')
    
    del X_test, X_test_s, y_test
    gc.collect()
    
    return {
        'name': config['name'],
        'layers': config['layers'],
        'lr': config['lr'],
        'alpha': config['alpha'],
        'features': len(valid_features),
        'time': elapsed,
        'auc': auc,
        'best_threshold': best_th,
        'best_precision': best_prec,
        'is_best': auc > 0.635
    }

def main():
    with open(LOG_FILE, 'w') as f:
        f.write(f'V4极致优化 - {datetime.now()}\n目标: 超越AUC=0.6350\n\n')
    
    log('='*60)
    log('神经网络选股模型 - V4 极致优化')
    log('目标: 超越AUC=0.6350')
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
    log('V4结果汇总')
    log('='*60)
    
    results.sort(key=lambda x: x['auc'], reverse=True)
    
    log('| 排名 | 配置 | 网络 | LR | Alpha | 时间 | AUC | 90%精确率 | 突破 |')
    log('|------|------|------|------|------|------|-----|----------|------|')
    
    for i, r in enumerate(results, 1):
        layers_str = '-'.join(str(x) for x in r['layers'])
        medal = '🥇' if i==1 else ('🥈' if i==2 else ('🥉' if i==3 else f'{i}'))
        breakthrough = '✅' if r['is_best'] else ''
        log(f'| {medal} | {r["name"]} | {layers_str} | {r["lr"]} | {r["alpha"]} | {r["time"]:.0f}s | {r["auc"]:.4f} | {r["best_precision"]:.4f} | {breakthrough} |')
    
    # 最佳
    best = results[0] if results else None
    if best:
        if best['auc'] > 0.635:
            log(f'\n🎉 突破成功! 新最佳: {best["name"]} (AUC={best["auc"]:.4f})')
        else:
            log(f'\n当前最佳: {best["name"]} (AUC={best["auc"]:.4f})')
            log(f'目标AUC=0.6350 尚未突破')
    
    log(f'\n完成: {datetime.now()}')

if __name__ == '__main__':
    main()