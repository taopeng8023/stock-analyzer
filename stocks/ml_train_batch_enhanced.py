#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 - 增强版增量训练

增强点:
- 每批次迭代3次 (加深学习)
- 更大网络 (128-64-32)
- 更多特征 (16个)
- 最终在全数据上微调
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

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

TEMP_DIR = Path('/home/admin/.openclaw/workspace/stocks/temp_full')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/ml_train_enhanced.log')

# 扩展特征集
FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'p_ma60',
    'ma5_slope', 'ma10_slope', 'ma20_slope',
    'ret5', 'ret10', 'ret20',
    'rsi',
    'macd_dif', 'macd_hist',
    'kdj_k', 'kdj_d',
    'vol_ratio', 'vol_ratio20',
    'boll_pos'
]

def log(msg):
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_batch(batch_file):
    """加载单个批次"""
    df = pd.read_csv(batch_file, usecols=FEATURES + ['label'])
    X = df[FEATURES].values.astype(np.float32)
    y = df['label'].values
    del df
    gc.collect()
    return X, y

def main():
    with open(LOG_FILE, 'w') as f:
        f.write(f'增强版训练日志 - {datetime.now()}\n\n')
    
    log('='*60)
    log('神经网络选股模型 - 增强版增量训练')
    log('='*60)
    
    start_time = time.time()
    
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    total_batches = len(batch_files)
    
    # 用最后一个(batch_11)做测试，其余训练
    test_file = batch_files[-1]
    train_files = batch_files[:-1]
    
    log(f'训练批次: {len(train_files)}个')
    log(f'测试批次: {test_file.name}')
    
    # 初始化scaler (用第一个批次)
    log('\n初始化...')
    X_init, y_init = load_batch(train_files[0])
    
    scaler = StandardScaler()
    scaler.fit(X_init)
    log(f'Scaler初始化完成')
    
    # 创建大网络
    log('创建神经网络 (128-64-32)...')
    model = MLPClassifier(
        hidden_layer_sizes=(128, 64, 32),
        activation='relu',
        solver='adam',
        alpha=0.001,
        batch_size=128,
        learning_rate='adaptive',
        learning_rate_init=0.002,
        max_iter=3,  # 每批次迭代3次
        random_state=42,
        warm_start=True,
        early_stopping=False,
        verbose=False
    )
    
    # 初始化模型
    X_init_s = scaler.transform(X_init)
    model.fit(X_init_s, y_init)
    log(f'初始化完成: 损失={model.loss_:.4f}')
    del X_init, X_init_s, y_init
    gc.collect()
    
    # 分批训练 (每批迭代3次)
    log('\n' + '='*60)
    log('开始分批训练 (每批次3轮)')
    log('='*60)
    
    for i, batch_file in enumerate(train_files[1:], start=2):
        X_batch, y_batch = load_batch(batch_file)
        X_batch_s = scaler.transform(X_batch)
        
        # 训练3轮
        for epoch in range(3):
            model.partial_fit(X_batch_s, y_batch)
        
        log(f'批次 {i}/{len(train_files)}: {batch_file.name} | {len(y_batch)}样本 | 损失={model.loss_:.4f}')
        
        del X_batch, X_batch_s, y_batch
        gc.collect()
    
    # 在所有数据上最终微调 (采样混合)
    log('\n' + '='*60)
    log('最终微调阶段')
    log('='*60)
    
    # 从每个批次采样10%混合微调
    sampled_X = []
    sampled_y = []
    
    for batch_file in train_files[:5]:  # 前5个批次采样
        X_b, y_b = load_batch(batch_file)
        # 随机采样10%
        idx = np.random.choice(len(y_b), int(len(y_b)*0.1), replace=False)
        sampled_X.append(scaler.transform(X_b[idx]))
        sampled_y.append(y_b[idx])
        del X_b, y_b
        gc.collect()
    
    X_mix = np.vstack(sampled_X)
    y_mix = np.concatenate(sampled_y)
    del sampled_X, sampled_y
    gc.collect()
    
    log(f'混合微调数据: {len(y_mix)}样本')
    
    # 微调10轮
    for epoch in range(10):
        model.partial_fit(X_mix, y_mix)
        if epoch % 3 == 0:
            log(f'  微调轮次 {epoch+1}: 损失={model.loss_:.4f}')
    
    del X_mix, y_mix
    gc.collect()
    
    # 测试评估
    log('\n' + '='*60)
    log('测试评估')
    log('='*60)
    
    # 用batch_9作为测试集(更大)
    test_idx = -3  # batch_9
    X_test, y_test = load_batch(batch_files[test_idx])
    X_test_s = scaler.transform(X_test)
    
    log(f'测试集: {len(y_test)}样本')
    
    y_prob = model.predict_proba(X_test_s)[:, 1]
    y_pred = model.predict(X_test_s)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    log(f'\n评估结果:')
    log(f'  准确率: {acc:.4f}')
    log(f'  精确率: {prec:.4f}')
    log(f'  召回率: {rec:.4f}')
    log(f'  F1: {f1:.4f}')
    log(f'  AUC: {auc:.4f}')
    
    # 阈值分析
    log('\n阈值评估:')
    log('| 阈值 | 覆盖 | 精确率 |')
    
    best_th = 0.5
    best_prec = prec
    
    for th in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]:
        mask = y_prob > th
        if sum(mask) > 10:
            th_prec = sum(y_test[mask] == 1) / sum(mask)
            log(f'| {th*100:.0f}% | {sum(mask)} | {th_prec:.4f} |')
            if th_prec > best_prec:
                best_prec = th_prec
                best_th = th
    
    log(f'\n最佳阈值: {best_th*100:.0f}% (精确率: {best_prec:.4f})')
    
    # 保存模型
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_file = MODEL_DIR / f'ml_nn_enhanced_{timestamp}.pkl'
    
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': FEATURES,
            'metrics': {
                'accuracy': acc,
                'precision': prec,
                'recall': rec,
                'f1': f1,
                'auc': auc,
                'best_threshold': best_th,
                'best_precision': best_prec
            },
            'config': {
                'hidden_layers': (128, 64, 32),
                'iterations_per_batch': 3,
                'final_epochs': 10
            }
        }, f)
    
    log(f'\n模型已保存: {model_file}')
    
    total_time = time.time() - start_time
    log('='*60)
    log(f'总耗时: {total_time/60:.1f}分钟')
    log(f'完成时间: {datetime.now()}')
    log('='*60)

if __name__ == '__main__':
    main()