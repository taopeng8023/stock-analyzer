#!/usr/bin/env python3
"""
神经网络快速训练 V8 - 简化版
"""
import json
import pickle
import time
import gc
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score

print("="*70)
print("神经网络快速训练 V8 - 简化版")
print("="*70)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'ret10', 'vol5', 'vol10', 'rsi', 
            'vol_ratio', 'hl_pct', 'boll_pos', 'price_strength']

print("\n加载数据...")
X_all = []
y_all = []
count = 0

json_files = sorted(HISTORY_DIR.glob("*.json"))[:300]

for fp in json_files:
    try:
        with open(fp) as f:
            raw = json.load(f)
        
        items = raw.get('items', [])
        fields = raw.get('fields', [])
        
        if len(items) < 100:
            continue
        
        # 解析数据
        data = []
        for item in items:
            if isinstance(item, list):
                d = dict(zip(fields, item))
            else:
                d = item
            
            c = float(d.get('close', 0))
            if c > 0:
                data.append({
                    'close': c,
                    'vol': float(d.get('vol', 0)),
                    'high': float(d.get('high', c)),
                    'low': float(d.get('low', c)),
                    'date': str(d.get('trade_date', ''))
                })
        
        # 反转（正序）
        data = data[::-1]
        
        # 计算特征
        closes = [d['close'] for d in data]
        volumes = [d['vol'] for d in data]
        highs = [d['high'] for d in data]
        lows = [d['low'] for d in data]
        dates = [d['date'] for d in data]
        
        for i in range(60, min(len(data)-5, 300)):  # 限制每个股票最多240个样本
            # 只取2024年数据
            if not dates[i].startswith('2024'):
                continue
            
            # 计算特征
            c = closes[i]
            ma5 = np.mean(closes[i-5:i+1])
            ma10 = np.mean(closes[i-10:i+1])
            ma20 = np.mean(closes[i-20:i+1])
            
            f = {}
            f['p_ma5'] = (c - ma5) / ma5
            f['p_ma10'] = (c - ma10) / ma10
            f['p_ma20'] = (c - ma20) / ma20
            
            f['ret5'] = (c - closes[i-5]) / closes[i-5]
            f['ret10'] = (c - closes[i-10]) / closes[i-10]
            
            rets = [(closes[j] - closes[j-1]) / closes[j-1] for j in range(i-20, i)]
            f['vol5'] = np.std(rets[-5:])
            f['vol10'] = np.std(rets[-10:])
            
            deltas = [closes[j+1] - closes[j] for j in range(i-15, i)]
            gains = sum(d for d in deltas if d > 0)
            losses = sum(-d for d in deltas if d < 0)
            f['rsi'] = 100 - 100/(1 + gains/losses) if losses > 0 else 50
            
            vol5 = np.mean(volumes[i-5:i+1])
            vol20 = np.mean(volumes[i-20:i+1])
            f['vol_ratio'] = volumes[i] / vol5 if vol5 > 0 else 1
            
            f['hl_pct'] = (highs[i] - lows[i]) / c
            std20 = np.std(closes[i-20:i+1])
            f['boll_pos'] = (c - ma20) / (2*std20) if std20 > 0 else 0
            
            f['price_strength'] = (f['p_ma5'] + f['p_ma10'] + f['p_ma20']) / 3
            
            # 标签: 5天后涨超3%
            future = closes[i+5]
            label = 1 if (future - c) / c >= 0.03 else 0
            
            X_all.append([f.get(k, 0) for k in FEATURES])
            y_all.append(label)
        
        count += 1
        if count % 30 == 0:
            print(f"  {count}股, {len(X_all)}样本")
        
        gc.collect()
        
        if len(X_all) >= 150000:
            break
    
    except Exception as e:
        print(f"  {fp.stem}: {e}")
        continue

print(f"\n加载完成: {count}股, {len(X_all)}样本")

if len(X_all) < 5000:
    print("样本不足")
    exit(1)

X = np.array(X_all, dtype=np.float32)
y = np.array(y_all, dtype=np.int32)

split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"训练: {len(X_train)}, 测试: {len(X_test)}, 正样本: {sum(y_train)} ({sum(y_train)/len(y_train)*100:.1f}%)")

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# 训练
print("\n训练神经网络...")

models = [
    ("V8_小", (128, 64), 0.002),
    ("V8_中", (256, 128), 0.001),
    ("V8_大", (512, 256), 0.001),
]

results = []
best_auc = 0
best_model = None

for name, layers, lr in models:
    print(f"\n{name}: {layers} lr={lr}")
    
    m = MLPClassifier(
        hidden_layer_sizes=layers,
        activation='relu',
        solver='adam',
        learning_rate_init=lr,
        alpha=0.01,
        max_iter=150,
        early_stopping=True,
        n_iter_no_change=15,
        random_state=42
    )
    
    t0 = time.time()
    m.fit(X_train_s, y_train)
    
    prob = m.predict_proba(X_test_s)[:, 1]
    auc = roc_auc_score(y_test, prob)
    p85 = precision_score(y_test, (prob >= 0.85).astype(int), zero_division=0)
    p90 = precision_score(y_test, (prob >= 0.90).astype(int), zero_division=0)
    
    elapsed = time.time() - t0
    print(f"  AUC={auc:.4f} P85={p85:.4f} P90={p90:.4f} {elapsed:.1f}s")
    
    results.append((name, auc, p85, p90))
    
    if auc > best_auc:
        best_auc = auc
        best_model = m
        best_prec = p90
        best_name = name

# 保存
print(f"\n最佳: {best_name} AUC={best_auc:.4f} P90={best_prec:.4f}")

model_file = MODEL_DIR / f"ml_nn_v8_{datetime.now().strftime('%Y%m%d_%H%M')}.pkl"
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': best_model,
        'scaler': scaler,
        'features': FEATURES,
        'metadata': {'auc': best_auc, 'precision_90': best_prec, 'name': best_name}
    }, f)

print(f"保存: {model_file.name}")

# 更新生产模型
prod = MODEL_DIR / "ml_nn_production.pkl"
if prod.exists():
    with open(prod, 'rb') as f:
        old = pickle.load(f)
    old_auc = old.get('metadata', {}).get('auc', 0.63)
    
    if best_auc > old_auc:
        print(f"超越旧模型(AUC={old_auc:.4f})")
        with open(prod, 'wb') as f:
            pickle.dump({
                'model': best_model,
                'scaler': scaler,
                'features': FEATURES,
                'metadata': {'auc': best_auc, 'precision_90': best_prec, 'name': best_name}
            }, f)
        print("✅ 已更新生产模型")

print("\n汇总:")
for r in results:
    print(f"  {r[0]}: AUC={r[1]:.4f} P85={r[2]:.4f} P90={r[3]:.4f}")

print("\n完成:", datetime.now())