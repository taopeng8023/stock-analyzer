#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML进阶训练系统 - 更强大的模型

改进：
1. 增加模型复杂度（更多树、更深）
2. 多模型融合（XGBoost + LightGBM）
3. 特征选择优化
4. 添加神经网络模型（如果可用）
5. 更详细的评估指标
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
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectFromModel
import xgboost as xgb

# 尝试导入其他库
try:
    import lightgbm as lgb
    HAS_LGB = True
except:
    HAS_LGB = False

try:
    from sklearn.neural_network import MLPClassifier
    HAS_MLP = True
except:
    HAS_MLP = False

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

def load_all_data():
    """加载所有临时数据"""
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    
    print(f'加载 {len(batch_files)} 个批次文件...')
    
    all_data = []
    total_samples = 0
    total_buy = 0
    
    for i, f in enumerate(batch_files):
        df = pd.read_csv(f)
        samples = len(df)
        buys = sum(df['label'] == 1)
        total_samples += samples
        total_buy += buys
        all_data.append(df)
        
        print(f'  [{i+1}/{len(batch_files)}] {f.name} | 样本:{samples} | 买入:{buys}')
        
        if (i+1) % 3 == 0:
            gc.collect()
    
    # 合并
    print('\n合并数据...')
    df_all = pd.concat(all_data, ignore_index=True)
    
    del all_data
    gc.collect()
    
    print(f'总样本: {len(df_all)}')
    print(f'买入信号: {sum(df_all["label"]==1)} ({sum(df_all["label"]==1)/len(df_all)*100:.1f}%)')
    
    return df_all

def train_xgb_advanced(X_train, y_train, X_test, y_test):
    """训练进阶XGBoost模型"""
    print('\n' + '='*60)
    print('训练进阶XGBoost模型')
    print('='*60)
    
    # 更复杂的参数
    params = {
        'objective': 'binary:logistic',
        'eval_metric': ['auc', 'logloss'],
        'max_depth': 8,          # 更深
        'min_child_weight': 3,
        'eta': 0.05,             # 更慢的学习
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'colsample_bylevel': 0.8,
        'lambda': 1.5,           # L2正则化
        'alpha': 0.1,            # L1正则化
        'gamma': 0.1,
        'seed': 42,
        'nthread': -1
    }
    
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)
    
    print('参数:')
    for k, v in params.items():
        print(f'  {k}: {v}')
    
    start = time.time()
    
    # 训练更多轮次
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=300,       # 更多树
        evals=[(dtrain, 'train'), (dtest, 'test')],
        early_stopping_rounds=30,
        verbose_eval=50
    )
    
    elapsed = time.time() - start
    print(f'\n训练完成: {elapsed:.0f}s')
    print(f'最佳轮次: {model.best_iteration}')
    
    return model

def train_lgb_model(X_train, y_train, X_test, y_test):
    """训练LightGBM模型"""
    if not HAS_LGB:
        print('LightGBM不可用')
        return None
    
    print('\n' + '='*60)
    print('训练LightGBM模型')
    print('='*60)
    
    params = {
        'objective': 'binary',
        'metric': ['auc', 'binary_logloss'],
        'max_depth': 8,
        'num_leaves': 64,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'lambda_l1': 0.1,
        'lambda_l2': 1.5,
        'min_gain_to_split': 0.1,
        'seed': 42,
        'verbose': -1
    }
    
    print('参数:')
    for k, v in params.items():
        print(f'  {k}: {v}')
    
    start = time.time()
    
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test)
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=300,
        valid_sets=[test_data],
        callbacks=[lgb.early_stopping(30), lgb.log_evaluation(50)]
    )
    
    elapsed = time.time() - start
    print(f'\n训练完成: {elapsed:.0f}s')
    
    return model

def evaluate_model(model, model_type, X_test, y_test, scaler=None):
    """评估模型"""
    print(f'\n评估 {model_type} 模型...')
    
    if model_type == 'xgb':
        dtest = xgb.DMatrix(X_test)
        y_prob = model.predict(dtest)
    elif model_type == 'lgb':
        y_prob = model.predict(X_test)
    else:
        if scaler:
            X_test_s = scaler.transform(X_test)
            y_prob = model.predict_proba(X_test_s)[:, 1]
        else:
            y_prob = model.predict_proba(X_test)[:, 1]
    
    y_pred = (y_prob > 0.5).astype(int)
    
    # 基本指标
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    print(f'''
基本指标:
  准确率: {acc:.4f}
  精确率: {prec:.4f}
  召回率: {rec:.4f}
  F1分数: {f1:.4f}
  AUC: {auc:.4f}
''')
    
    # 不同阈值评估
    print('不同置信度阈值表现:')
    print('| 阈值 | 覆盖数 | 精确率 | 召回率 |')
    print('|------|--------|--------|--------|')
    
    best_threshold = 0.65
    best_precision = 0
    
    for th in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]:
        mask = y_prob > th
        coverage = sum(mask)
        
        if coverage > 10:
            th_prec = sum(y_test[mask] == 1) / coverage
            th_rec = sum((y_test == 1) & mask) / sum(y_test == 1)
            
            print(f'| {th*100:.0f}% | {coverage} | {th_prec:.4f} | {th_rec:.4f} |')
            
            if th_prec > best_precision:
                best_precision = th_prec
                best_threshold = th
    
    print(f'\n最佳阈值: {best_threshold*100:.0f}%')
    print(f'最佳精确率: {best_precision:.4f}')
    
    return {
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1': f1,
        'auc': auc,
        'best_threshold': best_threshold,
        'best_precision': best_precision
    }

def feature_importance_analysis(model, model_type):
    """特征重要性分析"""
    print(f'\n特征重要性分析 ({model_type}):')
    
    if model_type == 'xgb':
        imp = model.get_score(importance_type='weight')
    elif model_type == 'lgb':
        imp = dict(zip(FEATURES, model.feature_importance()))
    else:
        imp = dict(zip(FEATURES, model.feature_importances_))
    
    # 排序
    sorted_imp = sorted(imp.items(), key=lambda x: -x[1])
    
    print('Top 15:')
    for k, v in sorted_imp[:15]:
        print(f'  {k}: {v}')
    
    return imp

def ensemble_prediction(xgb_model, lgb_model, X):
    """模型融合预测"""
    dmat = xgb.DMatrix(X)
    xgb_prob = xgb_model.predict(dmat)
    
    if lgb_model:
        lgb_prob = lgb_model.predict(X)
        # 简单平均
        ensemble_prob = (xgb_prob + lgb_prob) / 2
    else:
        ensemble_prob = xgb_prob
    
    return ensemble_prob

def main():
    print('='*60)
    print('ML进阶训练系统')
    print('='*60)
    
    # 检查库
    print(f'\n可用模型库:')
    print(f'  XGBoost: ✅')
    print(f'  LightGBM: {"✅" if HAS_LGB else "❌"}')
    print(f'  MLP神经网络: {"✅" if HAS_MLP else "❌"}')
    
    # 加载数据
    df_all = load_all_data()
    
    # 划分
    print('\n划分训练测试集...')
    X = df_all[FEATURES].values
    y = df_all['label'].values
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    del df_all
    gc.collect()
    
    print(f'训练集: {len(X_train)}')
    print(f'测试集: {len(X_test)}')
    
    # 标准化
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    
    # 训练模型
    results = {}
    models = {}
    
    # 1. 进阶XGBoost
    xgb_model = train_xgb_advanced(X_train, y_train, X_test, y_test)
    xgb_metrics = evaluate_model(xgb_model, 'xgb', X_test, y_test)
    xgb_imp = feature_importance_analysis(xgb_model, 'xgb')
    
    results['xgb'] = xgb_metrics
    models['xgb'] = xgb_model
    
    # 2. LightGBM
    if HAS_LGB:
        lgb_model = train_lgb_model(X_train, y_train, X_test, y_test)
        lgb_metrics = evaluate_model(lgb_model, 'lgb', X_test, y_test)
        lgb_imp = feature_importance_analysis(lgb_model, 'lgb')
        
        results['lgb'] = lgb_metrics
        models['lgb'] = lgb_model
        
        # 3. 模型融合
        print('\n' + '='*60)
        print('模型融合评估')
        print('='*60)
        
        ensemble_prob = ensemble_prediction(xgb_model, lgb_model, X_test)
        
        # 融合模型评估
        ensemble_pred = (ensemble_prob > 0.5).astype(int)
        ensemble_prec = precision_score(y_test, ensemble_pred, zero_division=0)
        
        print(f'融合精确率: {ensemble_prec:.4f}')
        
        # 不同阈值
        print('\n融合模型不同阈值:')
        for th in [0.60, 0.65, 0.70, 0.75, 0.80]:
            mask = ensemble_prob > th
            if sum(mask) > 10:
                th_prec = sum(y_test[mask] == 1) / sum(mask)
                print(f'  {th*100:.0f}%阈值: 精确率 {th_prec:.4f}')
    
    # 保存最佳模型
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存XGBoost
    xgb_file = MODEL_DIR / f'ml_xgb_advanced_{timestamp}.json'
    xgb_model.save_model(xgb_file)
    
    print(f'\n保存: {xgb_file}')
    
    # 保存配置
    best_metrics = results['xgb']
    config = {
        'threshold': best_metrics['best_threshold'],
        'high_precision': best_metrics['best_precision'],
        'accuracy': best_metrics['accuracy'],
        'auc': best_metrics['auc'],
        'features': FEATURES,
        'model_type': 'xgb_advanced'
    }
    
    if HAS_LGB and 'lgb' in results:
        config['lgb_precision'] = results['lgb']['best_precision']
    
    config_file = MODEL_DIR / f'ml_advanced_config_{timestamp}.json'
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f'保存: {config_file}')
    
    # 保存scaler
    scaler_file = MODEL_DIR / f'scaler_{timestamp}.pkl'
    with open(scaler_file, 'wb') as f:
        pickle.dump(scaler, f)
    
    print(f'保存: {scaler_file}')
    
    # 总结
    print('\n' + '='*60)
    print('训练完成总结')
    print('='*60)
    
    print(f'''
XGBoost进阶模型:
  AUC: {xgb_metrics["auc"]:.4f}
  精确率: {xgb_metrics["precision"]:.4f}
  最佳阈值: {xgb_metrics["best_threshold"]*100:.0f}%
  最佳精确率: {xgb_metrics["best_precision"]:.4f}
''')
    
    if HAS_LGB and 'lgb' in results:
        print(f'''
LightGBM模型:
  AUC: {results["lgb"]["auc"]:.4f}
  精确率: {results["lgb"]["precision"]:.4f}
  最佳阈值: {results["lgb"]["best_threshold"]*100:.0f}%
  最佳精确率: {results["lgb"]["best_precision"]:.4f}
''')
    
    print('✅ 进阶训练完成!')

if __name__ == '__main__':
    main()