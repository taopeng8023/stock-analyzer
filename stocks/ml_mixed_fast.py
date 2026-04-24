#!/usr/bin/env python3
"""
快速混合训练 - 后台运行
采样少量股票快速验证
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

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
LOG = MODEL_DIR / "train_mixed.log"

def log(msg):
    with open(LOG, 'a') as f:
        f.write(f"{datetime.now()}: {msg}\n")
    print(msg)

log("="*50)
log("混合数据快速训练")
log("="*50)

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

files = sorted(HISTORY_DIR.glob("*.json"))[:100]
log(f"加载 {len(files)} 股")

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
        
        closes = [d['close'] for d in data]
        volumes = [d['vol'] for d in data]
        highs = [d['high'] for d in data]
        lows = [d['low'] for d in data]
        dates = [d['date'] for d in data]
        
        # 混合2024+2025
        for i in range(60, min(len(data)-5, 300)):
            date = dates[i]
            if not (date.startswith('2024') or date.startswith('2025')):
                continue
            
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

log(f"样本: {len(X_all)}, 正样本: {sum(y_all)} ({sum(y_all)/len(y_all)*100:.1f}%)")

if len(X_all) < 20000:
    log("样本不足")
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

log("训练模型...")
t0 = time.time()

m = MLPClassifier(
    hidden_layer_sizes=(256, 128),
    activation='relu',
    solver='adam',
    learning_rate_init=0.001,
    alpha=0.01,
    max_iter=150,
    early_stopping=True,
    n_iter_no_change=15,
    random_state=42
)

m.fit(X_train_s, y_train)

prob = m.predict_proba(X_test_s)[:, 1]
auc = roc_auc_score(y_test, prob)
p90 = precision_score(y_test, (prob >= 0.90).astype(int), zero_division=0)

log(f"AUC={auc:.4f} P90={p90:.4f} 时间={time.time()-t0:.1f}s")

model_file = MODEL_DIR / f"ml_nn_mixed_{datetime.now().strftime('%H%M')}.pkl"
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': m, 'scaler': scaler, 'features': FEATURES,
        'metadata': {'auc': auc, 'precision_90': p90, 'version': 'Mixed'}
    }, f)

log(f"保存: {model_file.name}")

if auc > 0.56:
    log("泛化能力提升!")
    with open(MODEL_DIR / 'ml_nn_production.pkl', 'wb') as f:
        pickle.dump({
            'model': m, 'scaler': scaler, 'features': FEATURES,
            'metadata': {'auc': auc, 'precision_90': p90, 'version': 'Mixed'}
        }, f)
    log("生产模型已更新!")

log("完成")