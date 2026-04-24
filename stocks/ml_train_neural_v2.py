#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 V2 - 内存优化版

优化点:
- 减少批次加载量 (2批次约60万样本)
- 增量式垃圾回收
- 更小的网络结构
- 分批训练
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
import xgboost as xgb

TEMP_DIR = Path('/home/admin/.openclaw/workspace/stocks/temp_full')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')
LOG_FILE = Path('/home/admin/.openclaw/workspace/stocks/ml_train_neural_v2.log')

# 减少特征数量 (只保留最重要的)
FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20',
    'ma5_slope', 'ma10_slope',
    'ret5', 'ret10', 'ret20',
    'rsi',
    'macd_dif', 'macd_hist',
    'kdj_k', 'kdj_d',
    'vol_ratio',
    'boll_pos'
]

def log(msg):
    """同时输出到控制台和日志文件"""
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_batch_data(batch_files, max_batches=2):
    """加载批次数据（减少数量避免OOM）"""
    log(f'加载 {max_batches} 个批次...')
    
    all_data = []
    total_samples = 0
    
    for i, f in enumerate(batch_files[:max_batches]):
        # 分块读取减少内存峰值
        df = pd.read_csv(f, usecols=FEATURES + ['label', 'code', 'date'])
        samples = len(df)
        total_samples += samples
        all_data.append(df)
        log(f'  [{i+1}] {f.name} | {samples}样本')
        gc.collect()
    
    log('合并数据...')
    df_all = pd.concat(all_data, ignore_index=True)
    del all_data
    gc.collect()
    
    log(f'总样本: {len(df_all)}')
    return df_all

def create_neural_network(hidden_layers, activation='relu'):
    """创建神经网络"""
    model = MLPClassifier(
        hidden_layer_sizes=hidden_layers,
        activation=activation,
        solver='adam',
        alpha=0.001,          # 增强正则化防止过拟合
        batch_size=256,       # 固定batch size
        learning_rate='adaptive',
        learning_rate_init=0.001,
        max_iter=100,         # 减少迭代次数
        shuffle=True,
        random_state=42,
        tol=0.0001,
        verbose=True,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=10
    )
    
    return model

def train_nn_model(X_train, y_train, X_test, y_test, config):
    """训练神经网络"""
    log('='*60)
    log(f'训练神经网络 - {config["name"]}')
    log(f'结构: {config["layers"]}')
    log('='*60)
    
    # 标准化
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    
    del X_train
    gc.collect()
    
    # 创建模型
    model = create_neural_network(config['layers'], config['activation'])
    
    start = time.time()
    
    # 训练
    log('训练中...')
    model.fit(X_train_s, y_train)
    
    elapsed = time.time() - start
    log(f'训练完成: {elapsed:.0f}s | 迭代: {model.n_iter_} | 损失: {model.loss_:.4f}')
    
    # 预测
    y_prob = model.predict_proba(X_test_s)[:, 1]
    y_pred = model.predict(X_test_s)
    
    # 评估
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    log(f'评估: ACC={acc:.4f} PREC={prec:.4f} REC={rec:.4f} F1={f1:.4f} AUC={auc:.4f}')
    
    # 阈值评估
    best_threshold = 0.60
    best_precision = 0
    
    log('| 阈值 | 覆盖 | 精确率 |')
    for th in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]:
        mask = y_prob > th
        if sum(mask) > 10:
            th_prec = sum(y_test[mask] == 1) / sum(mask)
            log(f'| {th*100:.0f}% | {sum(mask)} | {th_prec:.4f} |')
            if th_prec > best_precision:
                best_precision = th_prec
                best_threshold = th
    
    log(f'最佳阈值: {best_threshold*100:.0f}% | 精确率: {best_precision:.4f}')
    
    return model, scaler, {
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1': f1,
        'auc': auc,
        'best_threshold': best_threshold,
        'best_precision': best_precision,
        'n_iter': model.n_iter_,
        'loss': model.loss_
    }

def train_xgboost(X_train, y_train, X_test, y_test):
    """训练XGBoost对比"""
    log('='*60)
    log('训练XGBoost对比模型')
    log('='*60)
    
    start = time.time()
    
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)
    
    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'max_depth': 5,
        'eta': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': 42
    }
    
    model = xgb.train(params, dtrain, num_boost_round=100)
    
    elapsed = time.time() - start
    log(f'训练完成: {elapsed:.0f}s')
    
    y_prob = model.predict(dtest)
    y_pred = (y_prob > 0.5).astype(int)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    log(f'评估: ACC={acc:.4f} PREC={prec:.4f} REC={rec:.4f} F1={f1:.4f} AUC={auc:.4f}')
    
    # 阈值评估
    best_threshold = 0.50
    best_precision = 0
    
    log('| 阈值 | 覆盖 | 精确率 |')
    for th in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]:
        mask = y_prob > th
        if sum(mask) > 10:
            th_prec = sum(y_test[mask] == 1) / sum(mask)
            log(f'| {th*100:.0f}% | {sum(mask)} | {th_prec:.4f} |')
            if th_prec > best_precision:
                best_precision = th_prec
                best_threshold = th
    
    return model, {
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1': f1,
        'auc': auc,
        'best_threshold': best_threshold,
        'best_precision': best_precision
    }

def main():
    # 清空日志
    with open(LOG_FILE, 'w') as f:
        f.write(f'神经网络训练日志 - {datetime.now()}\n\n')
    
    log('='*60)
    log('神经网络选股模型 V2 - 内存优化版')
    log('='*60)
    log(f'开始时间: {datetime.now()}')
    
    # 检查内存
    import os
    mem_info = os.popen('free -h').read()
    log(f'内存状态:\n{mem_info}')
    
    # 加载数据 (减少到2批次)
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    df_all = load_batch_data(batch_files, max_batches=2)
    
    # 划分
    log('划分数据集...')
    X = df_all[FEATURES].values
    y = df_all['label'].values
    
    # 保存代码和日期用于后续分析
    codes = df_all['code'].values
    dates = df_all['date'].values
    
    del df_all
    gc.collect()
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    del X, y
    gc.collect()
    
    log(f'训练集: {len(X_train)}')
    log(f'测试集: {len(X_test)}')
    
    # 只测试两个配置
    configs = [
        {'name': '小型网络', 'layers': (64, 32), 'activation': 'relu'},
        {'name': '中型网络', 'layers': (128, 64), 'activation': 'relu'},
    ]
    
    best_model = None
    best_scaler = None
    best_metrics = None
    best_config = None
    
    for config in configs:
        try:
            model, scaler, metrics = train_nn_model(
                X_train.copy(), y_train.copy(),
                X_test.copy(), y_test.copy(),
                config
            )
            
            if best_metrics is None or metrics['best_precision'] > best_metrics['best_precision']:
                best_model = model
                best_scaler = scaler
                best_metrics = metrics
                best_config = config
            
            gc.collect()
            
        except Exception as e:
            log(f'配置 {config["name"]} 训练失败: {e}')
    
    # XGBoost对比
    try:
        xgb_model, xgb_metrics = train_xgboost(
            X_train.copy(), y_train.copy(),
            X_test.copy(), y_test.copy()
        )
    except Exception as e:
        log(f'XGBoost训练失败: {e}')
        xgb_model = None
        xgb_metrics = None
    
    # 对比
    if best_metrics and xgb_metrics:
        log('='*60)
        log('模型对比')
        log('='*60)
        log(f'| 模型 | 准确率 | 精确率 | AUC | 最佳精确率 |')
        log(f'|------|--------|--------|-----|-----------|')
        log(f'| 神经网络({best_config["name"]}) | {best_metrics["accuracy"]:.4f} | {best_metrics["precision"]:.4f} | {best_metrics["auc"]:.4f} | {best_metrics["best_precision"]:.4f} |')
        log(f'| XGBoost | {xgb_metrics["accuracy"]:.4f} | {xgb_metrics["precision"]:.4f} | {xgb_metrics["auc"]:.4f} | {xgb_metrics["best_precision"]:.4f} |')
    
    # 保存模型
    if best_model is not None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存NN模型
        nn_file = MODEL_DIR / f'ml_nn_{timestamp}.pkl'
        with open(nn_file, 'wb') as f:
            pickle.dump({'model': best_model, 'scaler': best_scaler, 'features': FEATURES}, f)
        log(f'神经网络模型已保存: {nn_file}')
        
        # 保存XGBoost模型
        if xgb_model:
            xgb_file = MODEL_DIR / f'ml_nn_xgb_{timestamp}.json'
            xgb_model.save_model(str(xgb_file))
            log(f'XGBoost模型已保存: {xgb_file}')
        
        # 保存配置
        config_data = {
            'nn_config': best_config,
            'nn_metrics': best_metrics,
            'xgb_metrics': xgb_metrics,
            'features': FEATURES,
            'timestamp': timestamp
        }
        config_file = MODEL_DIR / f'ml_nn_config_{timestamp}.json'
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        log(f'配置已保存: {config_file}')
    
    log('='*60)
    log(f'完成时间: {datetime.now()}')
    log('='*60)

if __name__ == '__main__':
    main()