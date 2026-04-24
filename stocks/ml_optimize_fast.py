#!/usr/bin/env python3
"""
神经网络优化 - 快速版
采样200股 + 多网络配置对比
"""
import json
import pickle
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("神经网络优化 - 快速多配置对比")
print("="*70)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

files = sorted(HISTORY_DIR.glob("*.json"))[:200]
print(f"\n加载 {len(files)} 只股票...")

X_all = []
y_all = []

for fp in files:
    try:
        with open(fp) as f:
            raw = json.load(f)
        
        items = raw['items']
        fields = raw['fields']
        
        if len(items) < 100:
            continue
        
        data = []
        for item in items[::-1]:
            d = dict(zip(fields, item))
            c = float(d.get('close', 0))
            if c > 0:
                data.append({
                    'close': c, 'vol': float(d.get('vol', 0)),
                    'high': float(d.get('high', c)), 'low': float(d.get('low', c)),
                    'date': str(d.get('trade_date', ''))
                })
        
        idx_start = idx_end = None
        for i, d in enumerate(data):
            if d['date'].startswith('2024'):
                if idx_start is None:
                    idx_start = i
                idx_end = i
        
        if idx_start is None:
            continue
        
        closes = [d['close'] for d in data]
        volumes = [d['vol'] for d in data]
        highs = [d['high'] for d in data]
        lows = [d['low'] for d in data]
        
        valid_start = max(60, idx_start)
        valid_end = min(len(data) - 5, idx_end)
        
        if valid_end <= valid_start:
            continue
        
        for i in range(valid_start, valid_end):
            c = closes[i]
            ma5 = np.mean(closes[i-5:i+1])
            ma10 = np.mean(closes[i-10:i+1])
            ma20 = np.mean(closes[i-20:i+1])
            
            f = {}
            f['p_ma5'] = (c - ma5) / ma5
            f['p_ma10'] = (c - ma10) / ma10
            f['p_ma20'] = (c - ma20) / ma20
            f['ret5'] = (c - closes[i-5]) / closes[i-5]
            
            rets = [(closes[j] - closes[j-1]) / closes[j-1] for j in range(max(1, i-20), i)]
            f['vol5'] = np.std(rets[-5:]) if len(rets) >= 5 else 0
            
            deltas = [closes[j+1] - closes[j] for j in range(max(0, i-15), i)]
            gains = sum(d for d in deltas if d > 0)
            losses = sum(-d for d in deltas if d < 0)
            f['rsi'] = 100 - 100/(1 + gains/losses) if losses > 0 else 50
            
            vol5 = np.mean(volumes[i-5:i+1])
            f['vol_ratio'] = volumes[i] / vol5 if vol5 > 0 else 1
            f['hl_pct'] = (highs[i] - lows[i]) / c
            
            std20 = np.std(closes[i-20:i+1])
            f['boll_pos'] = (c - ma20) / (2*std20) if std20 > 0 else 0
            
            future = closes[i+5]
            label = 1 if (future - c) / c >= 0.03 else 0
            
            X_all.append([f.get(k, 0) for k in FEATURES])
            y_all.append(label)
    
    except:
        continue

print(f"样本: {len(X_all)}, 正样本: {sum(y_all)} ({sum(y_all)/len(y_all)*100:.1f}%)")

if len(X_all) < 30000:
    print("样本不足")
    exit(1)

X = np.array(X_all, dtype=np.float32)
y = np.array(y_all, dtype=np.int32)

split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"训练: {len(X_train)}, 测试: {len(X_test)}")

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# 多配置对比
configs = [
    ("标准_256x128", (256, 128), 0.001, 0.01),
    ("深网_512x256x128", (512, 256, 128), 0.001, 0.01),
    ("宽网_1024x512", (1024, 512), 0.001, 0.005),
    ("正则强_256x128", (256, 128), 0.002, 0.1),
    ("低LR_512x256", (512, 256), 0.0005, 0.01),
]

print("\n开始训练对比...")
results = []
best_auc = 0.6732
best_model = None
best_name = ""

for name, layers, lr, alpha in configs:
    print(f"\n{name}: {layers} lr={lr} α={alpha}")
    
    m = MLPClassifier(
        hidden_layer_sizes=layers,
        activation='relu',
        solver='adam',
        learning_rate_init=lr,
        alpha=alpha,
        max_iter=200,
        early_stopping=True,
        n_iter_no_change=20,
        random_state=42
    )
    
    t0 = time.time()
    m.fit(X_train_s, y_train)
    elapsed = time.time() - t0
    
    prob = m.predict_proba(X_test_s)[:, 1]
    auc = roc_auc_score(y_test, prob)
    p85 = precision_score(y_test, (prob >= 0.85).astype(int), zero_division=0)
    p90 = precision_score(y_test, (prob >= 0.90).astype(int), zero_division=0)
    
    print(f"  AUC={auc:.4f} P85={p85:.4f} P90={p90:.4f} {elapsed:.1f}s")
    
    results.append((name, auc, p85, p90, elapsed))
    
    if auc > best_auc:
        best_auc = auc
        best_model = m
        best_prec = p90
        best_name = name
        print("  ★ 新最佳!")

# 保存最佳
if best_model:
    print(f"\n最佳模型: {best_name}")
    print(f"  AUC: {best_auc:.4f} (V8=0.6732)")
    print(f"  精确率@90: {best_prec:.4f}")
    
    model_file = MODEL_DIR / f"ml_nn_opt_{best_name}_{datetime.now().strftime('%H%M')}.pkl"
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': best_model,
            'scaler': scaler,
            'features': FEATURES,
            'metadata': {
                'auc': best_auc,
                'precision_90': best_prec,
                'name': best_name,
                'version': 'Optimized'
            }
        }, f)
    
    print(f"保存: {model_file.name}")
    
    if best_auc > 0.6732:
        print("\n★ 性能超越V8!")
        with open(MODEL_DIR / 'ml_nn_production.pkl', 'wb') as f:
            pickle.dump({
                'model': best_model,
                'scaler': scaler,
                'features': FEATURES,
                'metadata': {
                    'auc': best_auc,
                    'precision_90': best_prec,
                    'name': best_name,
                    'version': 'Optimized'
                }
            }, f)
        print("✅ 生产模型已更新!")

print("\n结果汇总:")
for r in results:
    print(f"  {r[0]}: AUC={r[1]:.4f} P85={r[2]:.4f} P90={r[3]:.4f}")

print("\n完成:", datetime.now())