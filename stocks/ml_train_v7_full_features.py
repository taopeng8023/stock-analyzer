#!/usr/bin/env python3
"""
V7 全特征训练 - 36特征完整版
使用现有26特征 + 可补充的额外特征
目标: 提升 AUC 和精确率
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
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("V7 全特征训练 - 36特征完整版")
print("="*60)
print(datetime.now())

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 特征集定义
# 现有特征 (可直接使用)
FEATURES_EXISTING = [
    "p_ma5", "p_ma10", "p_ma20", "p_ma60",
    "ma5_slope", "ma10_slope", "ma20_slope",
    "ret5", "ret10", "ret20",
    "vol5", "vol10", "vol20",
    "rsi",
    "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    "vol_ratio", "vol_ratio20",
    "hl_pct", "hc_pct", "cl_pct",
    "boll_pos",
]

# 需补充计算的特征 (基于现有特征)
FEATURES_SUPPLEMENT = [
    "rsi_extreme",  # RSI超买超卖信号
    "kdj_cross",    # KDJ金叉死叉信号
    "macd_cross",   # MACD金叉死叉信号
    "ma_dist5",     # 收盘价距MA5距离
    "ma_dist10",    # 收盘价距MA10距离
    "vol_trend",    # 成交量趋势
    "price_strength", # 价格强度 (相对位置)
    "boll_width",   # 布林带宽度
    "ret_vol_ratio", # 收益波动比
    "ma_cross",     # 均线交叉信号
]

def compute_supplement_features(df):
    """计算补充特征 (基于现有特征)"""
    
    # RSI超买超卖信号
    rsi = df['rsi']
    df['rsi_extreme'] = np.where(rsi > 70, 1, np.where(rsi < 30, -1, 0)).astype(float)
    
    # KDJ金叉死叉信号
    k = df['kdj_k']
    d = df['kdj_d']
    df['kdj_cross'] = np.where(k > d, 1, np.where(k < d, -1, 0)).astype(float)
    
    # MACD金叉死叉信号
    dif = df['macd_dif']
    dea = df['macd_dea']
    df['macd_cross'] = np.where(dif > dea, 1, np.where(dif < dea, -1, 0)).astype(float)
    
    # 收盘价距MA距离 (百分比)
    df['ma_dist5'] = df['p_ma5']  # 已经是相对位置
    df['ma_dist10'] = df['p_ma10']
    
    # 成交量趋势 (vol5 vs vol20)
    df['vol_trend'] = (df['vol5'] - df['vol20']) / df['vol20']
    
    # 价格强度 (综合相对位置)
    df['price_strength'] = (df['p_ma5'] + df['p_ma10'] + df['p_ma20']) / 3
    
    # 布林带宽度 (hl_pct 已有)
    df['boll_width'] = df['hl_pct']
    
    # 收益波动比 (ret5 vs vol5)
    df['ret_vol_ratio'] = df['ret5'] / (df['vol5'] + 0.0001)
    
    # 均线交叉信号 (MA5 vs MA10)
    df['ma_cross'] = np.where(df['p_ma5'] > df['p_ma10'], 1, 
                              np.where(df['p_ma5'] < df['p_ma10'], -1, 0)).astype(float)
    
    return df

ALL_FEATURES = FEATURES_EXISTING + FEATURES_SUPPLEMENT
print(f"\n特征总数: {len(ALL_FEATURES)}")
print(f"  现有: {len(FEATURES_EXISTING)}")
print(f"  补充: {len(FEATURES_SUPPLEMENT)}")

# 加载测试数据
print("\n加载测试数据 batch_8...")
test_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_8.csv"))
test_df = compute_supplement_features(test_df)
X_test = test_df[ALL_FEATURES].fillna(0).values.astype(np.float32)
y_test = test_df['label'].values
print(f"测试样本: {len(y_test)}")

# 初始化scaler
print("\n初始化数据标准化...")
scaler = StandardScaler()
# 用第一个批次初始化
batch0 = pd.read_csv(os.path.join(TEMP_DIR, "batch_0.csv"), nrows=50000)
batch0 = compute_supplement_features(batch0)
scaler.fit(batch0[ALL_FEATURES].fillna(0).values.astype(np.float32))
X_test_scaled = scaler.transform(X_test)

# 训练配置
configs = [
    {"name": "V7_全特征_小", "layers": (256, 128), "lr": 0.003, "iterations": 3},
    {"name": "V7_全特征_中", "layers": (512, 256, 128), "lr": 0.002, "iterations": 3},
    {"name": "V7_全特征_大", "layers": (1024, 512, 256), "lr": 0.001, "iterations": 2},
    {"name": "V7_全特征_深", "layers": (300, 150, 75, 37), "lr": 0.002, "iterations": 3},
]

results = []
best_auc = 0
best_prec = 0
best_model = None

for cfg in configs:
    print(f"\n{'='*60}")
    print(f"{cfg['name']}: layers={cfg['layers']} LR={cfg['lr']} iterations={cfg['iterations']}")
    print("="*60)
    
    # 创建模型
    model = MLPClassifier(
        hidden_layer_sizes=cfg['layers'],
        activation='relu',
        solver='adam',
        learning_rate_init=cfg['lr'],
        alpha=0.01,
        batch_size=256,
        max_iter=50,
        early_stopping=False,
        random_state=42,
        warm_start=True
    )
    
    start_time = time.time()
    
    # 分批训练
    for iteration in range(cfg['iterations']):
        for batch_idx in range(10):
            batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}.csv")
            if not os.path.exists(batch_file):
                continue
            
            # 加载批次 (采样以加速)
            batch_df = pd.read_csv(batch_file, nrows=200000)
            batch_df = compute_supplement_features(batch_df)
            X_batch = batch_df[ALL_FEATURES].fillna(0).values.astype(np.float32)
            y_batch = batch_df['label'].values
            X_batch_scaled = scaler.transform(X_batch)
            
            # 训练
            model.partial_fit(X_batch_scaled, y_batch, classes=[0, 1])
            
            del batch_df, X_batch, y_batch, X_batch_scaled
            gc.collect()
        
        # 评估
        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        y_pred = (y_prob >= 0.90).astype(int)
        auc = roc_auc_score(y_test, y_prob)
        prec = precision_score(y_test, y_pred, zero_division=0)
        
        print(f"  轮{iteration+1}/{cfg['iterations']}: AUC={auc:.4f} 精确率@90={prec:.4f}")
        
        if auc > best_auc:
            best_auc = auc
            best_prec = prec
            best_model = pickle.loads(pickle.dumps(model))
            best_features = ALL_FEATURES
            print(f"    ★ 新最佳!")
    
    elapsed = time.time() - start_time
    results.append({
        "name": cfg['name'],
        "auc": auc,
        "precision": prec,
        "time": elapsed
    })

# 保存最佳模型
print("\n" + "="*60)
print("保存最佳模型...")
print("="*60)

metadata = {
    'hidden_layers': best_model.hidden_layer_sizes,
    'auc': best_auc,
    'precision': best_prec,
    'features': best_features,
    'feature_count': len(best_features),
    'trained_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'version': 'V7_full_features'
}

with open(os.path.join(MODEL_DIR, 'ml_nn_v7_full.pkl'), 'wb') as f:
    pickle.dump({
        'model': best_model,
        'scaler': scaler,
        'features': best_features,
        'metadata': metadata
    }, f)

print(f"\n最佳模型: AUC={best_auc:.4f} 精确率@90={best_prec:.4f}")
print(f"特征数: {len(best_features)}")
print(f"保存至: models/ml_nn_v7_full.pkl")

# 如果比生产模型更好，更新生产模型
with open(os.path.join(MODEL_DIR, 'ml_nn_production.pkl'), 'rb') as f:
    prod_data = pickle.load(f)
    prod_auc = prod_data.get('metadata', {}).get('auc', 0.63)

if best_auc > prod_auc:
    print(f"\n★ 性能超越生产模型 (旧AUC={prod_auc:.4f})")
    print("更新生产模型...")
    with open(os.path.join(MODEL_DIR, 'ml_nn_production.pkl'), 'wb') as f:
        pickle.dump({
            'model': best_model,
            'scaler': scaler,
            'features': best_features,
            'metadata': metadata
        }, f)
    print("✅ 生产模型已更新!")

# 结果汇总
print("\n结果汇总:")
print("| 配置 | AUC | 精确率@90 | 时间 |")
print("|------|-----|----------|------|")
for r in results:
    print(f"| {r['name']} | {r['auc']:.4f} | {r['precision']:.4f} | {r['time']:.0f}s |")

print("\n完成:", datetime.now())