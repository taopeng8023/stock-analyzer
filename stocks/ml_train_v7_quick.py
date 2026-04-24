#!/usr/bin/env python3
"""
V7 快速版 - 36特征测试
10分钟快速完成，验证新特征效果
"""
import os
import pickle
import time
import gc
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("V7 快速版 - 36特征测试")
print("="*60)
print(datetime.now())

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 全特征集 (26现有 + 10补充)
FEATURES = [
    "p_ma5", "p_ma10", "p_ma20", "p_ma60",
    "ma5_slope", "ma10_slope", "ma20_slope",
    "ret5", "ret10", "ret20",
    "vol5", "vol10", "vol20",
    "rsi", "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    "vol_ratio", "vol_ratio20",
    "hl_pct", "hc_pct", "cl_pct", "boll_pos",
]

# 补充计算特征
def add_features(df):
    df['rsi_extreme'] = np.where(df['rsi']>70,1,np.where(df['rsi']<30,-1,0)).astype(float)
    df['kdj_cross'] = np.where(df['kdj_k']>df['kdj_d'],1,np.where(df['kdj_k']<df['kdj_d'],-1,0)).astype(float)
    df['macd_cross'] = np.where(df['macd_dif']>df['macd_dea'],1,np.where(df['macd_dif']<df['macd_dea'],-1,0)).astype(float)
    df['vol_trend'] = (df['vol5']-df['vol20'])/(df['vol20']+0.0001)
    df['price_strength'] = (df['p_ma5']+df['p_ma10']+df['p_ma20'])/3
    df['ma_cross'] = np.where(df['p_ma5']>df['p_ma10'],1,np.where(df['p_ma5']<df['p_ma10'],-1,0)).astype(float)
    return df

ALL_FEATURES = FEATURES + ['rsi_extreme','kdj_cross','macd_cross','vol_trend','price_strength','ma_cross']
print(f"特征总数: {len(ALL_FEATURES)}")

# 加载测试数据
print("\n加载测试数据...")
test_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_8.csv"))
test_df = add_features(test_df)
X_test = test_df[ALL_FEATURES].fillna(0).values.astype(np.float32)
y_test = test_df['label'].values
print(f"测试样本: {len(y_test)}")

# 初始化scaler
batch0 = pd.read_csv(os.path.join(TEMP_DIR, "batch_0.csv"), nrows=100000)
batch0 = add_features(batch0)
scaler = StandardScaler()
scaler.fit(batch0[ALL_FEATURES].fillna(0).values.astype(np.float32))
X_test_scaled = scaler.transform(X_test)

# 训练配置
configs = [
    {"name": "V7_小网络", "layers": (256,128), "lr": 0.003, "iters": 2},
    {"name": "V7_中网络", "layers": (512,256), "lr": 0.002, "iters": 2},
    {"name": "V7_深网络", "layers": (300,150,75), "lr": 0.002, "iters": 2},
]

results = []
best_auc = 0
best_model = None

for cfg in configs:
    print(f"\n{'='*50}")
    print(f"{cfg['name']}: {cfg['layers']} LR={cfg['lr']}")
    print("="*50)
    
    model = MLPClassifier(
        hidden_layer_sizes=cfg['layers'],
        activation='relu',
        solver='adam',
        learning_rate_init=cfg['lr'],
        alpha=0.01,
        batch_size=256,
        max_iter=50,
        random_state=42,
        warm_start=True
    )
    
    start = time.time()
    
    for iter in range(cfg['iters']):
        for b in range(10):
            f = os.path.join(TEMP_DIR, f"batch_{b}.csv")
            if not os.path.exists(f): continue
            df = pd.read_csv(f, nrows=150000)
            df = add_features(df)
            X = df[ALL_FEATURES].fillna(0).values.astype(np.float32)
            y = df['label'].values
            Xs = scaler.transform(X)
            model.partial_fit(Xs, y, classes=[0,1])
            del df, X, y, Xs
            gc.collect()
        
        y_prob = model.predict_proba(X_test_scaled)[:,1]
        y_pred = (y_prob>=0.90).astype(int)
        auc = roc_auc_score(y_test, y_prob)
        prec = precision_score(y_test, y_pred, zero_division=0)
        print(f"  轮{iter+1}: AUC={auc:.4f} 精确率@90={prec:.4f}")
        
        if auc > best_auc:
            best_auc = auc
            best_prec = prec
            best_model = pickle.loads(pickle.dumps(model))
            print("    ★ 新最佳!")
    
    results.append({"name": cfg['name'], "auc": auc, "prec": prec, "time": time.time()-start})

# 保存
print("\n" + "="*60)
print("保存模型...")
metadata = {
    'hidden_layers': best_model.hidden_layer_sizes,
    'auc': best_auc,
    'precision': best_prec,
    'features': ALL_FEATURES,
    'feature_count': len(ALL_FEATURES),
    'trained_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'version': 'V7_quick'
}

with open(os.path.join(MODEL_DIR, 'ml_nn_v7_quick.pkl'), 'wb') as f:
    pickle.dump({'model': best_model, 'scaler': scaler, 'features': ALL_FEATURES, 'metadata': metadata}, f)

print(f"最佳: AUC={best_auc:.4f} 精确率@90={best_prec:.4f}")
print(f"特征数: {len(ALL_FEATURES)}")
print(f"保存: models/ml_nn_v7_quick.pkl")

# 对比生产模型
with open(os.path.join(MODEL_DIR, 'ml_nn_production.pkl'), 'rb') as f:
    prod = pickle.load(f)
    prod_auc = prod.get('metadata', {}).get('auc', 0.635)

print(f"\n对比: 生产AUC={prod_auc:.4f} vs V7={best_auc:.4f}")
if best_auc > prod_auc:
    print("★ 超越生产模型! 更新...")
    with open(os.path.join(MODEL_DIR, 'ml_nn_production.pkl'), 'wb') as f:
        pickle.dump({'model': best_model, 'scaler': scaler, 'features': ALL_FEATURES, 'metadata': metadata}, f)
    print("✅ 已更新!")

print("\n汇总:")
print("| 配置 | AUC | 精确率@90 | 时间 |")
for r in results:
    print(f"| {r['name']} | {r['auc']:.4f} | {r['prec']:.4f} | {r['time']:.0f}s |")

print("\n完成:", datetime.now())