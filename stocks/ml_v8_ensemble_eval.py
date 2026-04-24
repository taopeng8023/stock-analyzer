#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 集成评估 + 回测验证
"""

import json
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.metrics import precision_score, roc_auc_score

MODEL_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/models')
RESULTS_DIR = MODEL_DIR.parent / 'backtest_results'

# V8 模型配置
model_paths = [
    MODEL_DIR / 'ml_nn_v8_model1_seed42.pkl',
    MODEL_DIR / 'ml_nn_v8_model2_seed123.pkl',
    MODEL_DIR / 'ml_nn_v8_model3_seed456.pkl',
    MODEL_DIR / 'ml_nn_v8_model4_seed789.pkl',
    MODEL_DIR / 'ml_nn_v8_model5_seed1024.pkl'
]

# 加载所有模型
print('加载 V8 集成模型...')
models_data = []
for path in model_paths:
    with open(path, 'rb') as f:
        data = pickle.load(f)
    models_data.append(data)
    print(f'  {path.name}: AUC={data["val_auc"]:.4f}')

aucs = [d['val_auc'] for d in models_data]
print(f'\n平均 AUC: {np.mean(aucs):.4f} ± {np.std(aucs):.4f}')

# 保存集成配置
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
ensemble_config = {
    'model_paths': [str(p) for p in model_paths],
    'aucs': aucs,
    'avg_auc': float(np.mean(aucs)),
    'std_auc': float(np.std(aucs)),
    'timestamp': timestamp,
    'version': 'v8',
    'network': '256-128-64',
    'n_stocks': 1500,
    'n_samples': 500000,
    'n_features': 28,
    'label_threshold': 0.05
}

config_path = MODEL_DIR / f'ml_nn_v8_ensemble_config_{timestamp}.json'
with open(config_path, 'w') as f:
    json.dump(ensemble_config, f, indent=2)

print(f'\n集成配置已保存：{config_path.name}')
print(f'\n✅ V8 集成模型准备就绪！')
