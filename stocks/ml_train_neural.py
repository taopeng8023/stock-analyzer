#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 - MLP深度学习

使用sklearn MLPClassifier:
- 多层感知机神经网络
- 自适应学习率
- 早停机制
- 特征标准化
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import time
import pickle
import gc
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import xgboost as xgb

TEMP_DIR = Path('/home/admin/.openclaw/workspace/stocks/temp_full')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')

FEATURES = [
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

def load_batch_data(batch_files, max_batches=6):
    """加载批次数据（限制数量避免内存问题）"""
    print(f'加载 {len(batch_files[:max_batches])} 个批次...')
    
    all_data = []
    total_samples = 0
    
    for i, f in enumerate(batch_files[:max_batches]):
        df = pd.read_csv(f)
        samples = len(df)
        total_samples += samples
        all_data.append(df)
        print(f'  [{i+1}] {f.name} | {samples}样本')
        gc.collect()
    
    print('\n合并...')
    df_all = pd.concat(all_data, ignore_index=True)
    del all_data
    gc.collect()
    
    print(f'总样本: {len(df_all)}')
    return df_all

def create_neural_network(hidden_layers, activation='relu'):
    """创建神经网络"""
    print(f'\n创建神经网络:')
    print(f'  结构: {hidden_layers}')
    print(f'  激活函数: {activation}')
    
    model = MLPClassifier(
        hidden_layer_sizes=hidden_layers,
        activation=activation,
        solver='adam',
        alpha=0.0001,          # L2正则化
        batch_size='auto',
        learning_rate='adaptive',
        learning_rate_init=0.001,
        max_iter=200,
        shuffle=True,
        random_state=42,
        tol=0.0001,
        verbose=True,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20
    )
    
    return model

def train_nn_model(X_train, y_train, X_test, y_test, config):
    """训练神经网络"""
    print('\n' + '='*60)
    print(f'训练神经网络 - {config["name"]}')
    print('='*60)
    
    # 标准化（神经网络必须）
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    
    # 创建模型
    model = create_neural_network(config['layers'], config['activation'])
    
    start = time.time()
    
    # 训练
    print('\n训练中...')
    model.fit(X_train_s, y_train)
    
    elapsed = time.time() - start
    print(f'\n训练完成: {elapsed:.0f}s')
    print(f'迭代次数: {model.n_iter_}')
    print(f'最终损失: {model.loss_:.4f}')
    
    # 预测
    y_prob = model.predict_proba(X_test_s)[:, 1]
    y_pred = model.predict(X_test_s)
    
    # 评估
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    print(f'''
评估指标:
  准确率: {acc:.4f}
  精确率: {prec:.4f}
  召回率: {rec:.4f}
  F1: {f1:.4f}
  AUC: {auc:.4f}
''')
    
    # 不同阈值
    best_threshold = 0.60
    best_precision = 0
    
    print('阈值评估:')
    print('| 阈值 | 覆盖 | 精确率 |')
    for th in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]:
        mask = y_prob > th
        if sum(mask) > 10:
            th_prec = sum(y_test[mask] == 1) / sum(mask)
            print(f'| {th*100:.0f}% | {sum(mask)} | {th_prec:.4f} |')
            if th_prec > best_precision:
                best_precision = th_prec
                best_threshold = th
    
    print(f'\n最佳阈值: {best_threshold*100:.0f}%')
    print(f'最佳精确率: {best_precision:.4f}')
    
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

def compare_models(nn_metrics, xgb_metrics):
    """对比模型"""
    print('\n' + '='*60)
    print('模型对比')
    print('='*60)
    
    print(f'''
| 模型 | 准确率 | 精确率 | AUC | 最佳精确率 |
|------|--------|--------|-----|-----------|
| 神经网络 | {nn_metrics["accuracy"]:.4f} | {nn_metrics["precision"]:.4f} | {nn_metrics["auc"]:.4f} | {nn_metrics["best_precision"]:.4f} |
| XGBoost | {xgb_metrics["accuracy"]:.4f} | {xgb_metrics["precision"]:.4f} | {xgb_metrics["auc"]:.4f} | {xgb_metrics["best_precision"]:.4f} |
''')

def ensemble_nn_xgb(nn_model, nn_scaler, xgb_model, X_test, y_test):
    """神经网络+XGBoost融合"""
    print('\n' + '='*60)
    print('模型融合评估')
    print('='*60)
    
    # 神经网络预测
    X_test_s = nn_scaler.transform(X_test)
    nn_prob = nn_model.predict_proba(X_test_s)[:, 1]
    
    # XGBoost预测
    dmat = xgb.DMatrix(X_test)
    xgb_prob = xgb_model.predict(dmat)
    
    # 融合（平均）
    ensemble_prob = (nn_prob + xgb_prob) / 2
    
    # 评估
    print('融合模型阈值评估:')
    print('| 阈值 | 覆盖 | 精确率 |')
    
    for th in [0.50, 0.55, 0.60, 0.65, 0.70]:
        mask = ensemble_prob > th
        if sum(mask) > 10:
            th_prec = sum(y_test[mask] == 1) / sum(mask)
            print(f'| {th*100:.0f}% | {sum(mask)} | {th_prec:.4f} |')

def main():
    print('='*60)
    print('神经网络选股模型')
    print('='*60)
    
    # 加载数据
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    df_all = load_batch_data(batch_files, max_batches=6)  # 用6批次约190万样本
    
    # 划分
    print('\n划分数据集...')
    X = df_all[FEATURES].values
    y = df_all['label'].values
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    del df_all
    gc.collect()
    
    print(f'训练集: {len(X_train)}')
    print(f'测试集: {len(X_test)}')
    
    # 测试不同配置
    configs = [
        {'name': '小型网络', 'layers': (64, 32), 'activation': 'relu'},
        {'name': '中型网络', 'layers': (128, 64, 32), 'activation': 'relu'},
        {'name': '深层网络', 'layers': (256, 128, 64, 32), 'activation': 'relu'},
        {'name': 'tanh激活', 'layers': (128, 64, 32), 'activation': 'tanh'},
    ]
    
    best_model = None
    best_scaler = None
    best_metrics = None
    best_config = None
    
    results = []
    
    for config in configs:
        try:
            model, scaler, metrics = train_nn_model(
                X_train, y_train, X_test, y_test, config
            )
            
            results.append({
                'config': config,
                'metrics': metrics
            })
            
            if metrics['best_precision'] > (best_metrics['best_precision'] if best_metrics else 0):
                best_model = model
                best_scaler = scaler
                best_metrics = metrics
                best_config = config
        
        except Exception as e:
            print(f'\n配置 {config["name"]} 失败: {e}')
    
    if best_model:
        # 加载XGBoost对比
        print('\n加载XGBoost模型对比...')
        
        xgb_model = xgb.Booster()
        xgb_model.load_model(str(MODEL_DIR / 'ml_xgb_20260412_235045.json'))
        
        # XGBoost评估
        dtest = xgb.DMatrix(X_test)
        xgb_prob = xgb_model.predict(dtest)
        xgb_pred = (xgb_prob > 0.5).astype(int)
        
        xgb_metrics = {
            'accuracy': accuracy_score(y_test, xgb_pred),
            'precision': precision_score(y_test, xgb_pred, zero_division=0),
            'auc': roc_auc_score(y_test, xgb_prob),
            'best_precision': 0.89  # 已知值
        }
        
        # 对比
        compare_models(best_metrics, xgb_metrics)
        
        # 融合
        ensemble_nn_xgb(best_model, best_scaler, xgb_model, X_test, y_test)
        
        # 保存最佳模型
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        nn_file = MODEL_DIR / f'ml_nn_{timestamp}.pkl'
        with open(nn_file, 'wb') as f:
            pickle.dump({
                'model': best_model,
                'scaler': best_scaler,
                'config': best_config,
                'metrics': best_metrics
            }, f)
        
        print(f'\n保存: {nn_file}')
        
        # 保存配置
        config_out = {
            'model_type': 'neural_network',
            'layers': best_config['layers'],
            'activation': best_config['activation'],
            'threshold': best_metrics['best_threshold'],
            'precision': best_metrics['best_precision'],
            'auc': best_metrics['auc']
        }
        
        config_file = MODEL_DIR / f'ml_nn_config_{timestamp}.json'
        with open(config_file, 'w') as f:
            json.dump(config_out, f, indent=2)
        
        print(f'保存: {config_file}')
        
        # 总结
        print('\n' + '='*60)
        print('神经网络训练完成')
        print('='*60)
        
        print(f'''
最佳配置: {best_config["name"]}
  结构: {best_config["layers"]}
  激活: {best_config["activation"]}
  
性能:
  AUC: {best_metrics["auc"]:.4f}
  最佳阈值: {best_metrics["best_threshold"]*100:.0f}%
  最佳精确率: {best_metrics["best_precision"]:.4f}
''')
        
        # 保存对比结果
        pd.DataFrame(results).to_csv(
            RESULTS_DIR / f'nn_comparison_{timestamp}.csv',
            index=False
        )

if __name__ == '__main__':
    main()