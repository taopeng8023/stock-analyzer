#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 - 分批增量训练

使用partial_fit实现增量学习:
- 分批加载全量数据 (12批次约360万样本)
- 每批训练后释放内存
- 最终在测试集评估
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
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/ml_train_batch_incremental.log')

# 核心特征集
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

def load_batch_for_training(batch_file, scaler=None, fit_scaler=False):
    """加载单个批次并标准化"""
    df = pd.read_csv(batch_file, usecols=FEATURES + ['label'])
    
    X = df[FEATURES].values.astype(np.float32)
    y = df['label'].values
    
    del df
    gc.collect()
    
    # 标准化
    if fit_scaler:
        X_scaled = scaler.fit_transform(X)
    else:
        X_scaled = scaler.transform(X)
    
    del X
    gc.collect()
    
    return X_scaled, y

def main():
    # 清空日志
    with open(LOG_FILE, 'w') as f:
        f.write(f'分批增量训练日志 - {datetime.now()}\n\n')
    
    log('='*60)
    log('神经网络选股模型 - 分批增量训练')
    log('='*60)
    
    start_time = time.time()
    
    # 获取所有批次文件
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    total_batches = len(batch_files)
    
    log(f'发现 {total_batches} 个批次文件')
    for f in batch_files:
        lines = sum(1 for _ in open(f))
        log(f'  {f.name}: {lines}行')
    
    # 分离测试集 (使用最后一个批次作为测试)
    test_file = batch_files[-1]  # batch_11.csv作为测试集
    train_files = batch_files[:-1]  # 前11个用于训练
    
    log(f'\n训练批次: {len(train_files)}个')
    log(f'测试批次: {test_file.name}')
    
    # 先加载第一个批次初始化scaler
    log('\n初始化标准化器...')
    scaler = StandardScaler()
    
    # 用第一个批次fit scaler
    X_first, y_first = load_batch_for_training(train_files[0], scaler, fit_scaler=True)
    log(f'初始化批次: {len(y_first)}样本')
    
    # 创建模型 (使用partial_fit需要warm_start=True)
    log('\n创建神经网络模型...')
    model = MLPClassifier(
        hidden_layer_sizes=(64, 32, 16),
        activation='relu',
        solver='adam',
        alpha=0.005,
        batch_size=256,
        learning_rate='adaptive',
        learning_rate_init=0.001,
        max_iter=1,  # 每批只迭代1次
        random_state=42,
        warm_start=True,  # 关键：启用增量训练
        verbose=False
    )
    
    # 在第一个批次上初始化模型
    log('初始化模型...')
    model.fit(X_first, y_first)
    del X_first, y_first
    gc.collect()
    
    # 分批增量训练
    log('\n' + '='*60)
    log('开始分批增量训练')
    log('='*60)
    
    batch_num = 1
    total_samples = 0
    
    for batch_file in train_files[1:]:  # 跳过第一个(已用于初始化)
        batch_num += 1
        
        # 加载并标准化
        X_batch, y_batch = load_batch_for_training(batch_file, scaler, fit_scaler=False)
        batch_samples = len(y_batch)
        total_samples += batch_samples
        
        # 增量训练 (partial_fit)
        log(f'批次 {batch_num}/{len(train_files)}: {batch_file.name} | {batch_samples}样本')
        
        train_start = time.time()
        model.partial_fit(X_batch, y_batch)
        batch_time = time.time() - train_start
        
        log(f'  训练耗时: {batch_time:.1f}s | 当前损失: {model.loss_:.4f}')
        
        # 释放内存
        del X_batch, y_batch
        gc.collect()
        
        # 每3批显示内存状态
        if batch_num % 3 == 0:
            import os
            mem = os.popen('free -h | grep Mem').read().strip()
            log(f'  内存: {mem}')
    
    log(f'\n总训练样本: {total_samples + len(train_files[0].name)}')
    
    # 加载测试集
    log('\n' + '='*60)
    log('加载测试集评估')
    log('='*60)
    
    X_test, y_test = load_batch_for_training(test_file, scaler, fit_scaler=False)
    log(f'测试集: {len(y_test)}样本')
    
    # 预测
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    
    # 评估指标
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
    
    for th in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
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
    model_file = MODEL_DIR / f'ml_nn_incremental_{timestamp}.pkl'
    
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
                'hidden_layers': (64, 32, 16),
                'total_batches': len(train_files),
                'training_samples': total_samples
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