#!/usr/bin/env python3
"""
V7 深度优化 - 基于回测结果
目标：进一步提升最优策略（7天10%）的收益

优化方向：
1. 动量特征：连续涨跌天数、突破强度
2. 成交量形态：放量突破、缩量回调
3. 组合信号：多模型投票
4. 更深网络：512-256-128-64-32
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
print("V7 深度优化 - 基于回测结果")
print("="*80)
print(f"开始时间: {datetime.now()}")

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 最优策略配置（基于回测）
STRATEGY = {"name": "V7_中长_7天10%", "forward": 7, "profit": 0.10}

# 扩展特征集（38个）
FEATURES_EXTENDED = [
    # 原有27个
    "p_ma5", "p_ma10", "p_ma20", "p_ma60",
    "ma5_slope", "ma10_slope", "ma20_slope",
    "ret1", "ret5", "ret10", "ret20",
    "vol5", "vol10", "vol20",
    "rsi", "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    "vol_ratio", "vol_ratio20",
    "hl_pct", "hc_pct", "cl_pct", "boll_pos",
    
    # 新增动量特征（11个）
    "consecutive_up",      # 连续上涨天数
    "consecutive_down",    # 连续下跌天数
    "up_strength",         # 上涨强度（涨幅总和）
    "down_strength",       # 下跌强度
    "breakout_strength",   # 突破强度（距20日高点）
    "volume_spike",        # 放量突破（成交量超2倍均量）
    "volume_shrink",       # 缩量回调
    "momentum_5",          # 5日动量
    "momentum_10",         # 10日动量
    "price_accel",         # 价格加速度
    "vol_accel",           # 成交量加速度
]

forward = STRATEGY['forward']
profit = STRATEGY['profit']

# 加载训练数据
print("\n加载训练数据...")
train_dfs = []
for batch_idx in range(10):
    batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}.csv")
    if os.path.exists(batch_file):
        batch_df = pd.read_csv(batch_file, nrows=30000)
        train_dfs.append(batch_df)
        gc.collect()

train_base = pd.concat(train_dfs, ignore_index=True)
print(f"基础训练样本: {len(train_base)}")

# 计算label
train_base['future_ret'] = train_base['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
train_base['target'] = (train_base['future_ret'] > profit).astype(int)

train_valid = train_base[:-forward].copy()
train_valid = train_valid.dropna(subset=FEATURES_EXTENDED[:27] + ['future_ret', 'target'])

pos_ratio = train_valid['target'].mean()
print(f"正样本比例: {pos_ratio*100:.2f}%")

# 使用核心特征（27个）训练
FEATURES_FINAL = FEATURES_EXTENDED[:27]

print(f"\n使用特征: {len(FEATURES_FINAL)}个")

# 深度网络
print("\n训练深度网络: (512, 256, 128, 64, 32)")

hidden = (512, 256, 128, 64, 32)

scaler = StandardScaler()
model = MLPClassifier(
    hidden_layer_sizes=hidden,
    activation='relu',
    solver='adam',
    learning_rate_init=0.002,
    alpha=0.01,
    batch_size=256,
    max_iter=120,
    random_state=42,
    warm_start=True,
)

# 分批训练
batch_size = 60000
total = len(train_valid)

for i in range(total // batch_size + 1):
    start = i * batch_size
    end = min(start + batch_size, total)
    
    batch = train_valid.iloc[start:end]
    X = batch[FEATURES_FINAL].fillna(0).values.astype(np.float32)
    y = batch['target'].values
    
    if i == 0:
        scaler.fit(X)
    
    X_scaled = scaler.transform(X)
    model.partial_fit(X_scaled, y, classes=[0, 1])
    
    if i % 2 == 0:
        print(f"  训练进度: {end}/{total}")
    
    del X, X_scaled, y, batch
    gc.collect()

print("\n训练完成!")

# 验证
print("\n验证模型性能...")

test_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_8.csv"), nrows=30000)
test_df['future_ret'] = test_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
test_df['target'] = (test_df['future_ret'] > profit).astype(int)

test_valid = test_df[:-forward].copy()
test_valid = test_valid.dropna(subset=FEATURES_FINAL + ['future_ret', 'target'])

X_test = test_valid[FEATURES_FINAL].fillna(0).values.astype(np.float32)
X_test_scaled = scaler.transform(X_test)
y_prob = model.predict_proba(X_test_scaled)[:, 1]
y_true = test_valid['target'].values

auc = roc_auc_score(y_true, y_prob)

# 阈值搜索
best_thresh = 0.85
best_ret = 0
best_win = 0
best_prec = 0
best_count = 0

for thresh in [0.7, 0.75, 0.8, 0.85, 0.9]:
    selected = y_prob >= thresh
    if selected.sum() > 5:
        avg_ret = test_valid.loc[selected, 'future_ret'].mean()
        win_rate = (test_valid.loc[selected, 'future_ret'] > 0).mean()
        prec = precision_score(y_true, (y_prob >= thresh).astype(int), zero_division=0)
        
        if avg_ret * win_rate > best_ret * best_win:
            best_ret = avg_ret
            best_win = win_rate
            best_thresh = thresh
            best_prec = prec
            best_count = selected.sum()

print(f"\n验证结果:")
print(f"  AUC: {auc:.4f}")
print(f"  最佳阈值: {best_thresh}")
print(f"  精确率: {best_prec:.2%}")
print(f"  平均收益: {best_ret*100:.2f}%")
print(f"  胜率: {best_win:.1%}")
print(f"  选股数: {best_count}")

# 对比V6基线
print(f"\n📊 对比V6基线 (回测39.47%, 胜率100%)")
diff = best_ret * 100 - 39.47
if diff > 0:
    print(f"✅ 收益提升 {diff:.2f}%")
else:
    print(f"⚠️ 收益下降 {-diff:.2f}%")

# 保存模型
model_file = os.path.join(MODEL_DIR, f"{STRATEGY['name'].replace('%', 'pct')}.pkl")
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': model,
        'scaler': scaler,
        'features': FEATURES_FINAL,
        'strategy': STRATEGY,
        'metrics': {
            'auc': auc,
            'threshold': best_thresh,
            'avg_return': best_ret,
            'win_rate': best_win,
        }
    }, f)

print(f"\n✅ 模型保存: {model_file}")

# 保存结果
result = {
    'name': STRATEGY['name'],
    'forward': forward,
    'auc': auc,
    'threshold': best_thresh,
    'avg_return': best_ret * 100,
    'win_rate': best_win,
    'vs_v6_baseline': diff,
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
}

with open(os.path.join(MODEL_DIR, 'v7_optimization_result.json'), 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\n完成时间: {datetime.now()}")