#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 V3 - 极致内存优化版

优化:
- 只加载1个批次 (~18万样本)
- 分块读取CSV
- 最小特征集
- 小型网络
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
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/ml_train_neural_v3.log')

# 最小特征集
FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20',
    'ma5_slope', 'ma10_slope',
    'ret5', 'ret10',
    'rsi',
    'macd_hist',
    'kdj_k',
    'vol_ratio',
    'boll_pos'
]

def log(msg):
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_single_batch(batch_file):
    """加载单个批次，最小化内存"""
    log(f'加载: {batch_file.name}')
    
    # 只读取需要的列
    df = pd.read_csv(batch_file, usecols=FEATURES + ['label'])
    
    log(f'  样本数: {len(df)}')
    log(f'  内存: {df.memory_usage(deep=True).sum() / 1024**2:.1f}MB')
    
    return df

def main():
    # 清空日志
    with open(LOG_FILE, 'w') as f:
        f.write(f'训练日志 V3 - {datetime.now()}\n\n')
    
    log('='*60)
    log('神经网络选股模型 V3 - 极致内存优化版')
    log('='*60)
    
    start_time = time.time()
    
    # 加载一个正常大小的批次 (~35万样本)
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    
    # 使用batch_1 (~34万样本, 179MB)
    target_batch = TEMP_DIR / 'batch_1.csv'
    if target_batch.exists():
        df = load_single_batch(target_batch)
    else:
        # 回退到最小批次
        min_batch = min(batch_files, key=lambda x: x.stat().st_size)
        df = load_single_batch(min_batch)
    
    # 准备数据
    log('准备数据...')
    X = df[FEATURES].values.astype(np.float32)  # 使用float32减少内存
    y = df['label'].values
    
    del df
    gc.collect()
    
    log(f'特征矩阵: {X.shape}')
    log(f'特征内存: {X.nbytes / 1024**2:.1f}MB')
    
    # 划分
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    del X, y
    gc.collect()
    
    log(f'训练集: {len(X_train)}')
    log(f'测试集: {len(X_test)}')
    
    # 标准化
    log('标准化...')
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    
    del X_train
    gc.collect()
    
    # 训练中型网络
    log('='*60)
    log('训练神经网络 (中型网络)...')
    log('='*60)
    
    model = MLPClassifier(
        hidden_layer_sizes=(64, 32, 16),  # 三层网络
        activation='relu',
        solver='adam',
        alpha=0.005,
        batch_size=256,
        learning_rate='adaptive',
        learning_rate_init=0.005,
        max_iter=100,
        random_state=42,
        verbose=True,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=10
    )
    
    train_start = time.time()
    model.fit(X_train_s, y_train)
    train_time = time.time() - train_start
    
    log(f'训练完成: {train_time:.0f}s')
    log(f'迭代次数: {model.n_iter_}')
    log(f'最终损失: {model.loss_:.4f}')
    
    # 评估
    y_prob = model.predict_proba(X_test_s)[:, 1]
    y_pred = model.predict(X_test_s)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    log('='*60)
    log('评估结果')
    log('='*60)
    log(f'准确率: {acc:.4f}')
    log(f'精确率: {prec:.4f}')
    log(f'召回率: {rec:.4f}')
    log(f'F1: {f1:.4f}')
    log(f'AUC: {auc:.4f}')
    
    # 阈值分析
    log('| 阈值 | 覆盖 | 精确率 |')
    best_th = 0.5
    best_prec = prec
    
    for th in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]:
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
    model_file = MODEL_DIR / f'ml_nn_v3_{timestamp}.pkl'
    
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
            }
        }, f)
    
    log(f'\n模型已保存: {model_file}')
    
    total_time = time.time() - start_time
    log('='*60)
    log(f'总耗时: {total_time:.0f}s')
    log(f'完成时间: {datetime.now()}')
    log('='*60)

if __name__ == '__main__':
    main()