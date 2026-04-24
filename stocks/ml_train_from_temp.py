#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从临时文件训练ML模型
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import warnings
from pathlib import Path
import time
import gc

warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import pickle

TEMP_DIR = Path('/home/admin/.openclaw/workspace/stocks/temp_data')
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


def main():
    print('='*80)
    print('从临时文件训练模型')
    print('='*80, flush=True)
    
    batch_files = sorted(TEMP_DIR.glob('batch_*.csv'))
    print(f'\n批次文件: {len(batch_files)}个', flush=True)
    
    # 加载所有数据
    print('\n加载数据...', flush=True)
    
    all_X = []
    all_y = []
    total_samples = 0
    
    for i, f in enumerate(batch_files):
        df = pd.read_csv(f)
        X = df[FEATURES].values
        y = df['label'].values
        
        total_samples += len(X)
        all_X.append(X)
        all_y.append(y)
        
        print(f'  [{i+1}/{len(batch_files)}] {f.name} | 样本:{len(X)} | 买入:{sum(y==1)}', flush=True)
        
        del df
        gc.collect()
    
    print(f'\n合并数据...', flush=True)
    X_all = np.vstack(all_X)
    y_all = np.concatenate(all_y)
    
    del all_X, all_y
    gc.collect()
    
    print(f'  总样本: {len(X_all)}', flush=True)
    print(f'  买入信号: {sum(y_all==1)} ({sum(y_all==1)/len(y_all)*100:.1f}%)', flush=True)
    
    # 划分训练测试
    print('\n划分数据...', flush=True)
    X_train, X_test, y_train, y_test = train_test_split(X_all, y_all, test_size=0.2, random_state=42)
    
    del X_all, y_all
    gc.collect()
    
    # 标准化
    print('标准化...', flush=True)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    
    # 训练
    print('\n训练XGBoost...', flush=True)
    start = time.time()
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='binary:logistic',
        eval_metric='auc',
        use_label_encoder=False,
        random_state=42,
        verbosity=0
    )
    
    model.fit(X_train_s, y_train)
    
    elapsed = time.time() - start
    print(f'  训练完成: {elapsed:.0f}s', flush=True)
    
    # 评估
    print('\n评估模型...', flush=True)
    y_pred = model.predict(X_test_s)
    y_prob = model.predict_proba(X_test_s)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    
    # 最佳阈值
    best_threshold = 0.65
    best_high_prec = 0
    
    for threshold in [0.55, 0.60, 0.65, 0.70, 0.75]:
        high_mask = y_prob > threshold
        if sum(high_mask) > 10:
            high_correct = sum(y_test[high_mask] == 1)
            high_prec = high_correct / sum(high_mask)
            if high_prec > best_high_prec:
                best_high_prec = high_prec
                best_threshold = threshold
    
    print(f'\n📊 模型性能:', flush=True)
    print(f'  准确率: {acc:.4f}', flush=True)
    print(f'  精确率: {prec:.4f}', flush=True)
    print(f'  最佳阈值: {best_threshold*100:.0f}%', flush=True)
    print(f'  高置信度精确率: {best_high_prec:.4f}', flush=True)
    
    # 特征重要性
    imp = model.feature_importances_
    imp_df = pd.DataFrame({'feature': FEATURES, 'importance': imp})
    imp_df = imp_df.sort_values('importance', ascending=False)
    
    print(f'\n📊 Top 10 特征:', flush=True)
    for i, row in imp_df.head(10).iterrows():
        print(f"  {row['feature']:12s} : {row['importance']:.4f}", flush=True)
    
    # 保存模型
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_file = MODEL_DIR / f'ml_selector_full_{timestamp}.pkl'
    
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': FEATURES,
            'threshold': best_threshold,
            'forward_days': 5,
            'profit_pct': 0.03,
            'high_precision': best_high_prec,
            'accuracy': acc,
            'precision': prec,
            'total_samples': total_samples
        }, f)
    
    print(f'\n💾 模型保存: {model_file}', flush=True)
    
    # 保存特征重要性
    imp_df.to_csv(RESULTS_DIR / f'feature_importance_full_{timestamp}.csv',
                  index=False, encoding='utf-8-sig')
    
    print('\n' + '='*80)
    print('✅ 全量训练完成!')
    print('='*80, flush=True)
    
    print(f"""
模型配置:
  预测周期: 5天
  盈利阈值: 3%
  置信度阈值: {best_threshold*100:.0f}%

性能指标:
  总样本数: {total_samples}
  准确率: {acc*100:.1f}%
  精确率: {prec*100:.1f}%
  高置信度精确率: {best_high_prec*100:.1f}%
""", flush=True)


if __name__ == '__main__':
    main()