#!/usr/bin/env python3
"""
全量训练 - 5500股终极版
使用全部可用数据
"""
import json, pickle, time, numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score
import warnings
warnings.filterwarnings('ignore')

print("="*70, flush=True)
print("神经网络训练 - 全量5500股终极版", flush=True)
print("="*70, flush=True)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

files = sorted(HISTORY_DIR.glob("*.json"))
print(f"加载全部 {len(files)} 只股票...", flush=True)

X_all, y_all = [], []
stocks_ok = 0

start = time.time()

for fp in files:
    try:
        with open(fp) as f:
            raw = json.load(f)
        items, fields = raw['items'], raw['fields']
        if len(items) < 100: continue
        
        data = []
        for item in items:
            d = dict(zip(fields, item))
            c = float(d.get('close', 0))
            if c > 0:
                data.append({'close': c, 'vol': float(d.get('vol', 0)),
                            'high': float(d.get('high', c)), 'low': float(d.get('low', c)),
                            'date': str(d.get('trade_date', ''))})
        
        closes, volumes, highs, lows, dates = [d['close'] for d in data], [d['vol'] for d in data], [d['high'] for d in data], [d['low'] for d in data], [d['date'] for d in data]
        
        for i in range(60, len(data) - 5):
            date = dates[i]
            if not (date.startswith('2024') or date.startswith('2025') or date.startswith('2026')): continue
            
            c = closes[i]
            ma5, ma10, ma20 = np.mean(closes[i-5:i+1]), np.mean(closes[i-10:i+1]), np.mean(closes[i-20:i+1])
            
            f = {
                'p_ma5': (c - ma5) / ma5, 'p_ma10': (c - ma10) / ma10, 'p_ma20': (c - ma20) / ma20,
                'vol5': np.std([closes[j] - closes[j-1] for j in range(i-4, i+1)]) / c
            }
            
            deltas = [closes[j] - closes[j-1] for j in range(i-13, i+1)]
            gains, losses = sum(d for d in deltas if d > 0), sum(-d for d in deltas if d < 0)
            f['rsi'] = 100 - 100/(1 + gains/(losses+0.001)) if losses > 0 else 100
            
            vol5 = np.mean(volumes[i-5:i+1])
            f['vol_ratio'] = volumes[i] / (vol5 + 0.001)
            f['hl_pct'] = (highs[i] - lows[i]) / c
            f['boll_pos'] = (c - ma20) / (2 * np.std(closes[i-20:i+1]) + 0.001)
            
            future_ret5 = (closes[i+5] - c) / c if i+5 < len(closes) else 0
            X_all.append([f.get(k, 0) for k in FEATURES])
            y_all.append(1 if future_ret5 > 0.03 else 0)
        
        stocks_ok += 1
        if stocks_ok % 1000 == 0:
            print(f"  {stocks_ok}股 {len(X_all)}样本", flush=True)
    except: continue

load_time = time.time() - start
print(f"\n数据: {stocks_ok}股 {len(X_all)}样本 加载:{load_time:.1f}s", flush=True)
print(f"正样本: {sum(y_all)/len(y_all)*100:.2f}%", flush=True)

X, y = np.array(X_all), np.array(y_all)
n = int(len(X) * 0.8)
X_train, X_test, y_train, y_test = X[:n], X[n:], y[:n], y[n:]

scaler = StandardScaler()
X_train_s, X_test_s = scaler.fit_transform(X_train), scaler.transform(X_test)

print(f"训练:{len(X_train)} 测试:{len(X_test)}", flush=True)
t0 = time.time()

model = MLPClassifier(hidden_layer_sizes=(32, 16), activation='relu', solver='adam',
                      learning_rate_init=0.05, max_iter=5, early_stopping=True,
                      validation_fraction=0.05, n_iter_no_change=1, random_state=42, alpha=0.01)

model.fit(X_train_s, y_train)
train_time = time.time() - t0
print(f"训练: {train_time:.1f}s", flush=True)

proba = model.predict_proba(X_test_s)[:, 1]
auc = roc_auc_score(y_test, proba)

print(f"\nAUC: {auc:.4f}", flush=True)
for t in [0.7, 0.8, 0.85, 0.9]:
    pred = (proba >= t).astype(int)
    p = precision_score(y_test, pred, zero_division=0)
    print(f"  P@{t}: {p:.4f} ({sum(pred)}股)", flush=True)

total_time = load_time + train_time
print(f"\n总耗时: {total_time:.1f}s", flush=True)

ts = datetime.now().strftime('%Y%m%d_%H%M')
model_data = {
    'model': model, 'scaler': scaler, 'features': FEATURES,
    'metadata': {'auc': auc, 'version': 'V10_全量5500股', 'stocks': stocks_ok,
                 'train_samples': len(X_train), 'load_time': load_time, 'train_time': train_time}
}

for p in [MODEL_DIR / f"ml_nn_full_{ts}.pkl", MODEL_DIR / "ml_nn_production.pkl"]:
    with open(p, 'wb') as f: pickle.dump(model_data, f)

print(f"\n保存: ml_nn_full_{ts}.pkl", flush=True)
print("="*70, flush=True)