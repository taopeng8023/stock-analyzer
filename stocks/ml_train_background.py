#!/usr/bin/env python3
"""
神经网络优化 - 单次深度训练
后台运行，避免超时
"""
import json
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score
import warnings
warnings.filterwarnings('ignore')

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
LOG_FILE = MODEL_DIR / "train_log.txt"

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now()}: {msg}\n")
    print(msg)

log("="*50)
log("神经网络优化启动")
log("="*50)

files = sorted(HISTORY_DIR.glob("*.json"))[:200]
log(f"加载 {len(files)} 只股票...")

X_all = []
y_all = []

for i, fp in enumerate(files):
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
        for j, d in enumerate(data):
            if d['date'].startswith('2024'):
                if idx_start is None:
                    idx_start = j
                idx_end = j
        
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
        
        for k in range(valid_start, valid_end):
            c = closes[k]
            ma5 = np.mean(closes[k-5:k+1])
            ma10 = np.mean(closes[k-10:k+1])
            ma20 = np.mean(closes[k-20:k+1])
            
            f = {}
            f['p_ma5'] = (c - ma5) / ma5
            f['p_ma10'] = (c - ma10) / ma10
            f['p_ma20'] = (c - ma20) / ma20
            f['ret5'] = (c - closes[k-5]) / closes[k-5]
            
            rets = [(closes[j] - closes[j-1]) / closes[j-1] for j in range(max(1, k-20), k)]
            f['vol5'] = np.std(rets[-5:]) if len(rets) >= 5 else 0
            
            deltas = [closes[j+1] - closes[j] for j in range(max(0, k-15), k)]
            gains = sum(d for d in deltas if d > 0)
            losses = sum(-d for d in deltas if d < 0)
            f['rsi'] = 100 - 100/(1 + gains/losses) if losses > 0 else 50
            
            vol5 = np.mean(volumes[k-5:k+1])
            f['vol_ratio'] = volumes[k] / vol5 if vol5 > 0 else 1
            f['hl_pct'] = (highs[k] - lows[k]) / c
            
            std20 = np.std(closes[k-20:k+1])
            f['boll_pos'] = (c - ma20) / (2*std20) if std20 > 0 else 0
            
            future = closes[k+5]
            label = 1 if (future - c) / c >= 0.03 else 0
            
            X_all.append([f.get(k, 0) for k in FEATURES])
            y_all.append(label)
        
        if i % 50 == 0:
            log(f"已加载 {i} 股, {len(X_all)} 样本")
    
    except Exception as e:
        continue

log(f"数据完成: {len(X_all)} 样本")

if len(X_all) < 30000:
    log("样本不足，退出")
    exit(1)

X = np.array(X_all, dtype=np.float32)
y = np.array(y_all, dtype=np.int32)

split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

log(f"训练: {len(X_train)}, 测试: {len(X_test)}")

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# 深度网络训练
log("训练深网 (512,256,128)...")

m = MLPClassifier(
    hidden_layer_sizes=(512, 256, 128),
    activation='relu',
    solver='adam',
    learning_rate_init=0.001,
    alpha=0.01,
    max_iter=200,
    early_stopping=True,
    n_iter_no_change=20,
    random_state=42
)

m.fit(X_train_s, y_train)

prob = m.predict_proba(X_test_s)[:, 1]
auc = roc_auc_score(y_test, prob)
p90 = precision_score(y_test, (prob >= 0.90).astype(int), zero_division=0)

log(f"结果: AUC={auc:.4f} P90={p90:.4f}")

# 保存
model_file = MODEL_DIR / f"ml_nn_deep_{datetime.now().strftime('%H%M')}.pkl"
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': m,
        'scaler': scaler,
        'features': FEATURES,
        'metadata': {
            'auc': auc,
            'precision_90': p90,
            'version': 'Deep',
            'samples': len(X_train)
        }
    }, f)

log(f"保存: {model_file.name}")

if auc > 0.6732:
    log("★ 性能超越V8!")
    with open(MODEL_DIR / 'ml_nn_production.pkl', 'wb') as f:
        pickle.dump({
            'model': m,
            'scaler': scaler,
            'features': FEATURES,
            'metadata': {
                'auc': auc,
                'precision_90': p90,
                'version': 'Deep'
            }
        }, f)
    log("✅ 生产模型已更新!")

log("完成: " + str(datetime.now()))