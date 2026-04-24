#!/usr/bin/env python3
"""
轻量级训练 - 使用XGBoost外存模式
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
import time
import pickle
import xgboost as xgb

TEMP_DIR = Path('/home/admin/.openclaw/workspace/stocks/temp_data')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')

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

def main():
    print('='*60)
    print('轻量级XGBoost训练')
    print('='*60)
    
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    print(f'批次文件: {len(batch_files)}个')
    
    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'max_depth': 5,
        'eta': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': 42
    }
    
    print('\n增量训练...')
    start = time.time()
    
    model = None
    
    for i, f in enumerate(batch_files):
        df = pd.read_csv(f)
        X = df[FEATURES].values
        y = df['label'].values
        
        dmat = xgb.DMatrix(X, label=y)
        
        if model is None:
            # 第一批：初始训练
            model = xgb.train(params, dmat, num_boost_round=100)
        else:
            # 后续批：增量训练
            model = xgb.train(params, dmat, num_boost_round=20, xgb_model=model)
        
        print(f'  [{i+1}/{len(batch_files)}] {f.name} | 样本:{len(X)}')
        
        del df, X, y, dmat
    
    elapsed = time.time() - start
    print(f'\n训练完成: {elapsed:.0f}s')
    
    # 评估（用最后一个batch）
    df_test = pd.read_csv(batch_files[-1])
    X_test = df_test[FEATURES].values
    y_test = df_test['label'].values
    
    dtest = xgb.DMatrix(X_test)
    y_prob = model.predict(dtest)
    y_pred = (y_prob > 0.5).astype(int)
    
    acc = sum(y_pred == y_test) / len(y_test)
    
    # 最佳阈值
    best_th = 0.65
    best_prec = 0
    
    for th in [0.55, 0.60, 0.65, 0.70, 0.75]:
        mask = y_prob > th
        if sum(mask) > 10:
            prec = sum(y_test[mask] == 1) / sum(mask)
            if prec > best_prec:
                best_prec = prec
                best_th = th
    
    print(f'\n📊 性能:')
    print(f'  准确率: {acc:.4f}')
    print(f'  最佳阈值: {best_th*100:.0f}%')
    print(f'  高置信度精确率: {best_prec:.4f}')
    
    # 特征重要性
    imp = model.get_score(importance_type='weight')
    print('\n📊 Top 10 特征:')
    for k, v in sorted(imp.items(), key=lambda x: -x[1])[:10]:
        print(f'  {k}: {v}')
    
    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_file = MODEL_DIR / f'ml_xgb_{timestamp}.json'
    model.save_model(model_file)
    
    # 保存配置
    config = {
        'model_file': str(model_file),
        'features': FEATURES,
        'threshold': best_th,
        'high_precision': best_prec,
        'accuracy': acc
    }
    
    with open(MODEL_DIR / f'ml_config_{timestamp}.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f'\n💾 保存: {model_file}')

if __name__ == '__main__':
    main()