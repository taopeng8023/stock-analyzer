#!/usr/bin/env python3
"""
轻量优化 - 短攻_3天3pct 策略
内存优化版，避免OOM

优化：
1. 减少样本量 (每批50k)
2. 中等网络 (256,128,64)
3. 增加迭代次数补偿
"""
import os
import pickle
import json
import gc
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("轻量优化 - 短攻_3天3pct 策略")
print("="*80)
print(f"开始时间: {datetime.now()}")

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

STRATEGY = {"name": "短攻_轻量V4", "forward": 3, "profit": 0.03}

FEATURES = [
    "p_ma5", "p_ma10", "p_ma20", "p_ma60",
    "ma5_slope", "ma10_slope", "ma20_slope",
    "ret1", "ret5", "ret10", "ret20",
    "vol5", "vol10", "vol20",
    "rsi", "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    "vol_ratio", "vol_ratio20",
    "hl_pct", "hc_pct", "cl_pct", "boll_pos",
]

forward = STRATEGY['forward']
profit = STRATEGY['profit']

# 加载训练数据 (减少样本)
print("\n加载训练数据...")
train_dfs = []
for batch_idx in range(10):
    batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}.csv")
    if os.path.exists(batch_file):
        batch_df = pd.read_csv(batch_file, nrows=50000)  # 每批50k
        
        batch_df['future_ret'] = batch_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
        batch_df['target'] = (batch_df['future_ret'] > profit).astype(int)
        
        train_dfs.append(batch_df)
        print(f"  batch_{batch_idx}: {len(batch_df)} samples")
        
        gc.collect()

train_df = pd.concat(train_dfs, ignore_index=True)
print(f"训练样本总数: {len(train_df)}")

train_valid = train_df[:-forward].copy()
train_valid = train_valid.dropna(subset=FEATURES + ['future_ret', 'target'])

print(f"有效样本: {len(train_valid)}")
print(f"正样本比例: {train_valid['target'].mean()*100:.2f}%")

# 中等网络
print("\n训练中等深度网络...")
print("网络结构: (256, 128, 64)")

hidden_layers = (256, 128, 64)

scaler = StandardScaler()
model = MLPClassifier(
    hidden_layer_sizes=hidden_layers,
    activation='relu',
    solver='adam',
    learning_rate_init=0.002,
    alpha=0.01,
    batch_size=256,
    max_iter=200,
    random_state=42,
    warm_start=True,
)

# 分批训练
batch_size = 100000
total_batches = len(train_valid) // batch_size + 1

for i in range(total_batches):
    start = i * batch_size
    end = min(start + batch_size, len(train_valid))
    
    batch = train_valid.iloc[start:end]
    
    X = batch[FEATURES].fillna(0).values.astype(np.float32)
    y = batch['target'].values
    
    if i == 0:
        scaler.fit(X)
    
    X_scaled = scaler.transform(X)
    
    model.partial_fit(X_scaled, y, classes=[0, 1])
    
    print(f"  训练进度: {end}/{len(train_valid)}")
    
    del X, X_scaled, y, batch
    gc.collect()

print("\n训练完成!")

# 验证
print("\n验证性能...")

test_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_8.csv"), nrows=50000)
test_df['future_ret'] = test_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
test_df['target'] = (test_df['future_ret'] > profit).astype(int)

test_valid = test_df[:-forward].copy()
test_valid = test_valid.dropna(subset=FEATURES + ['future_ret', 'target'])

X_test = test_valid[FEATURES].fillna(0).values.astype(np.float32)
X_test_scaled = scaler.transform(X_test)
y_prob = model.predict_proba(X_test_scaled)[:, 1]
y_true = test_valid['target'].values

auc = roc_auc_score(y_true, y_prob)

# 阈值搜索
results = []
for thresh in [0.6, 0.7, 0.8, 0.85, 0.9]:
    selected = y_prob >= thresh
    if selected.sum() > 5:
        avg_ret = test_valid.loc[selected, 'future_ret'].mean()
        win_rate = (test_valid.loc[selected, 'future_ret'] > 0).mean()
        prec = precision_score(y_true, (y_prob >= thresh).astype(int), zero_division=0)
        results.append({
            'thresh': thresh,
            'avg_ret': avg_ret,
            'win_rate': win_rate,
            'prec': prec,
            'count': selected.sum(),
        })

# 最佳阈值
best = max(results, key=lambda x: x['avg_ret'] * x['win_rate'])

print(f"\n验证结果:")
print(f"  AUC: {auc:.4f}")
print(f"  最佳阈值: {best['thresh']}")
print(f"  精确率: {best['prec']:.2%}")
print(f"  平均收益: {best['avg_ret']*100:.2f}%")
print(f"  胜率: {best['win_rate']:.1%}")
print(f"  选股数: {best['count']}")

print(f"\n对比基线: 平均收益 12.11%, 胜率 71.4%")
diff = best['avg_ret']*100 - 12.11
if diff > 0:
    print(f"✅ 收益提升 {diff:.2f}%")
else:
    print(f"⚠️ 收益下降 {-diff:.2f}%")

# 保存
model_file = os.path.join(MODEL_DIR, f"ml_light_{STRATEGY['name']}.pkl")
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': model,
        'scaler': scaler,
        'features': FEATURES,
        'strategy': STRATEGY,
        'metrics': {
            'auc': auc,
            'threshold': best['thresh'],
            'avg_return': best['avg_ret'],
            'win_rate': best['win_rate'],
        }
    }, f)

print(f"\n✅ 模型保存: {model_file}")

# 结果记录
result = {
    'name': STRATEGY['name'],
    'auc': auc,
    'threshold': best['thresh'],
    'avg_return': best['avg_ret'] * 100,
    'win_rate': best['win_rate'],
    'vs_baseline': diff,
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
}

with open(os.path.join(MODEL_DIR, 'light_optimization_result.json'), 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\n完成时间: {datetime.now()}")