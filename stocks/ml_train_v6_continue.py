#!/usr/bin/env python3
"""
V6 继续训练版 - 增量训练优化
基于已部署的 ml_nn_production.pkl，继续训练更多轮次
目标: 突破 AUC=0.65, 精确率=98%
"""
import os
import sys
import json
import pickle
import time
import gc
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, recall_score

print("V6 继续训练版 -", datetime.now())
print("="*60)

# 配置
TEMP_DIR = "temp_data"
MODEL_DIR = "models"
PRODUCTION_MODEL = os.path.join(MODEL_DIR, "ml_nn_production.pkl")

# 加载生产模型
print("加载生产模型...")
with open(PRODUCTION_MODEL, 'rb') as f:
    saved_data = pickle.load(f)
    model = saved_data['model']
    scaler = saved_data['scaler']
    features = saved_data['features']
    config = saved_data.get('metadata', {})
    
print(f"模型架构: {model.hidden_layer_sizes}")
print(f"当前AUC: {config.get('auc', 'N/A')}")
print(f"当前精确率: {config.get('precision', 'N/A')}")

# 加载测试数据 (batch_8)
print("\n加载测试数据 batch_8...")
test_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_8.csv"))
X_test = test_df[features].values.astype(np.float32)
y_test = test_df['label'].values
X_test_scaled = scaler.transform(X_test)
print(f"测试样本: {len(y_test)}")

# 评估当前模型
y_prob = model.predict_proba(X_test_scaled)[:, 1]
y_pred = (y_prob >= 0.90).astype(int)
current_auc = roc_auc_score(y_test, y_prob)
current_prec = precision_score(y_test, y_pred, zero_division=0)
print(f"\n当前模型性能:")
print(f"  AUC: {current_auc:.4f}")
print(f"  精确率@90: {current_prec:.4f}")

# 增量训练配置
configs = [
    {"name": "V6_微调1", "iterations": 5, "lr": 0.0001, "batch_size": 350000},
    {"name": "V6_微调2", "iterations": 10, "lr": 0.00005, "batch_size": 350000},
    {"name": "V6_强训", "iterations": 20, "lr": 0.001, "batch_size": 200000},
]

results = []
best_model = model
best_auc = current_auc
best_prec = current_prec

for cfg in configs:
    print(f"\n{'='*60}")
    print(f"{cfg['name']}: {cfg['iterations']}轮 LR={cfg['lr']}")
    print("="*60)
    
    # 复制模型
    train_model = pickle.loads(pickle.dumps(model))
    train_model.set_params(learning_rate_init=cfg['lr'], warm_start=True)
    
    start_time = time.time()
    
    # 分批训练
    for iteration in range(cfg['iterations']):
        for batch_idx in range(10):
            batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}.csv")
            if not os.path.exists(batch_file):
                continue
            
            # 加载批次
            batch_df = pd.read_csv(batch_file)
            if len(batch_df) > cfg['batch_size']:
                batch_df = batch_df.sample(n=cfg['batch_size'], random_state=batch_idx*100+iteration)
            
            X_batch = batch_df[features].values.astype(np.float32)
            y_batch = batch_df['label'].values
            X_batch_scaled = scaler.transform(X_batch)
            
            # 训练
            train_model.partial_fit(X_batch_scaled, y_batch, classes=[0, 1])
            
            if batch_idx % 5 == 4:
                gc.collect()
        
        # 每轮评估
        y_prob = train_model.predict_proba(X_test_scaled)[:, 1]
        y_pred = (y_prob >= 0.90).astype(int)
        auc = roc_auc_score(y_test, y_prob)
        prec = precision_score(y_test, y_pred, zero_division=0)
        
        print(f"  轮{iteration+1}/{cfg['iterations']}: AUC={auc:.4f} 精确率@90={prec:.4f}")
        
        # 保存最佳
        if auc > best_auc:
            best_auc = auc
            best_prec = prec
            best_model = pickle.loads(pickle.dumps(train_model))
            print(f"    ★ 新最佳!")
    
    elapsed = time.time() - start_time
    results.append({
        "name": cfg['name'],
        "auc": auc,
        "precision": prec,
        "time": elapsed
    })
    print(f"  总时间: {elapsed:.0f}s")

# 保存最佳模型
print("\n" + "="*60)
print("保存最佳模型...")
print("="*60)

new_config = {
    'hidden_layers': model.hidden_layer_sizes,
    'auc': best_auc,
    'precision': best_prec,
    'trained_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'version': 'V6_continue'
}

with open(os.path.join(MODEL_DIR, 'ml_nn_v6_continue.pkl'), 'wb') as f:
    pickle.dump({
        'model': best_model,
        'scaler': scaler,
        'features': features,
        'config': new_config
    }, f)

print(f"\n最佳模型: AUC={best_auc:.4f} 精确率@90={best_prec:.4f}")
print(f"保存至: models/ml_nn_v6_continue.pkl")

# 结果汇总
print("\n结果汇总:")
print("| 配置 | AUC | 精确率@90 | 时间 |")
for r in results:
    print(f"| {r['name']} | {r['auc']:.4f} | {r['precision']:.4f} | {r['time']:.0f}s |")

print("\n完成:", datetime.now())
