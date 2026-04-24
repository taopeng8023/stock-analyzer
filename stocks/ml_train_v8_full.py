#!/usr/bin/env python3
"""
神经网络训练 V8 - 全量优化版
扩大训练规模 + 多配置对比
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

print("="*70)
print("神经网络训练 V8 - 全量优化版")
print("="*70)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'p_ma60', 
            'ret5', 'ret10', 'vol5', 'vol10', 'vol20',
            'rsi', 'vol_ratio', 'vol_ratio20', 
            'hl_pct', 'hc_pct', 'cl_pct', 'boll_pos', 
            'price_strength', 'ma_cross']

# 加载500只股票
files = sorted(HISTORY_DIR.glob("*.json"))[:500]
print(f"\n加载 {len(files)} 只股票...")

X_all = []
y_all = []
stocks_ok = 0

for fp in files:
    try:
        with open(fp) as f:
            raw = json.load(f)
        
        items = raw['items']
        fields = raw['fields']
        
        if len(items) < 100:
            continue
        
        # 反转（正序）
        data = []
        for item in items[::-1]:
            d = dict(zip(fields, item))
            c = float(d.get('close', 0))
            if c > 0:
                data.append({
                    'close': c,
                    'vol': float(d.get('vol', 0)),
                    'high': float(d.get('high', c)),
                    'low': float(d.get('low', c)),
                    'date': str(d.get('trade_date', ''))
                })
        
        # 找2024年范围
        idx_start = None
        idx_end = None
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
        
        # 计算特征
        for i in range(valid_start, valid_end):
            c = closes[i]
            
            ma5 = np.mean(closes[i-5:i+1])
            ma10 = np.mean(closes[i-10:i+1])
            ma20 = np.mean(closes[i-20:i+1])
            ma60 = np.mean(closes[i-60:i+1])
            
            f = {}
            f['p_ma5'] = (c - ma5) / ma5
            f['p_ma10'] = (c - ma10) / ma10
            f['p_ma20'] = (c - ma20) / ma20
            f['p_ma60'] = (c - ma60) / ma60
            
            f['ret5'] = (c - closes[i-5]) / closes[i-5]
            f['ret10'] = (c - closes[i-10]) / closes[i-10]
            
            rets = [(closes[j] - closes[j-1]) / closes[j-1] 
                    for j in range(max(1, i-20), i)]
            f['vol5'] = np.std(rets[-5:]) if len(rets) >= 5 else 0
            f['vol10'] = np.std(rets[-10:]) if len(rets) >= 10 else 0
            f['vol20'] = np.std(rets) if len(rets) >= 20 else 0
            
            deltas = [closes[j+1] - closes[j] for j in range(max(0, i-15), i)]
            gains = sum(d for d in deltas if d > 0)
            losses = sum(-d for d in deltas if d < 0)
            f['rsi'] = 100 - 100/(1 + gains/losses) if losses > 0 else 50
            
            vol5 = np.mean(volumes[i-5:i+1])
            vol10 = np.mean(volumes[i-10:i+1])
            vol20 = np.mean(volumes[i-20:i+1])
            f['vol_ratio'] = volumes[i] / vol5 if vol5 > 0 else 1
            f['vol_ratio20'] = volumes[i] / vol20 if vol20 > 0 else 1
            
            f['hl_pct'] = (highs[i] - lows[i]) / c
            f['hc_pct'] = (highs[i] - c) / c
            f['cl_pct'] = (c - lows[i]) / c
            
            std20 = np.std(closes[i-20:i+1])
            f['boll_pos'] = (c - ma20) / (2*std20) if std20 > 0 else 0
            
            f['price_strength'] = (f['p_ma5'] + f['p_ma10'] + f['p_ma20']) / 3
            f['ma_cross'] = 1 if ma5 > ma10 else -1
            
            # 标签: 5天后涨超3%
            future = closes[i+5]
            label = 1 if (future - c) / c >= 0.03 else 0
            
            X_all.append([f.get(k, 0) for k in FEATURES])
            y_all.append(label)
        
        stocks_ok += 1
        if stocks_ok % 50 == 0:
            print(f"  {stocks_ok}股, {len(X_all)}样本")
        
        if len(X_all) >= 100000:
            break
    
    except Exception as e:
        continue

print(f"\n数据完成: {stocks_ok}股, {len(X_all)}样本")
print(f"正样本: {sum(y_all)} ({sum(y_all)/len(y_all)*100:.1f}%)")

if len(X_all) < 10000:
    print("样本不足")
    exit(1)

X = np.array(X_all, dtype=np.float32)
y = np.array(y_all, dtype=np.int32)

# 分割
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"\n训练集: {len(X_train)}, 测试集: {len(X_test)}")

# 标准化
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# 训练多配置
print("\n开始训练多配置对比...")

configs = [
    ("V8_标准", (256, 128), 0.001, 200),
    ("V8_深网", (512, 256, 128), 0.001, 250),
    ("V8_宽网", (1024, 512), 0.001, 200),
    ("V8_正则", (256, 128), 0.001, 200, 0.1),  # 强正则
    ("V8_低LR", (512, 256, 128), 0.0005, 300),
]

results = []
best_auc = 0
best_model = None
best_scaler = scaler
best_name = ""

for cfg in configs:
    name, layers, lr, max_iter = cfg[:4]
    alpha = cfg[4] if len(cfg) > 4 else 0.01
    
    print(f"\n{name}: layers={layers} lr={lr} alpha={alpha}")
    
    m = MLPClassifier(
        hidden_layer_sizes=layers,
        activation='relu',
        solver='adam',
        learning_rate_init=lr,
        alpha=alpha,
        max_iter=max_iter,
        early_stopping=True,
        n_iter_no_change=25,
        random_state=42
    )
    
    t0 = time.time()
    m.fit(X_train_s, y_train)
    elapsed = time.time() - t0
    
    prob = m.predict_proba(X_test_s)[:, 1]
    auc = roc_auc_score(y_test, prob)
    p85 = precision_score(y_test, (prob >= 0.85).astype(int), zero_division=0)
    p90 = precision_score(y_test, (prob >= 0.90).astype(int), zero_division=0)
    p95 = precision_score(y_test, (prob >= 0.95).astype(int), zero_division=0)
    
    print(f"  AUC={auc:.4f} P85={p85:.4f} P90={p90:.4f} P95={p95:.4f} 时间={elapsed:.1f}s")
    
    results.append((name, auc, p85, p90, p95, elapsed))
    
    if auc > best_auc:
        best_auc = auc
        best_model = m
        best_prec = p90
        best_name = name
        print("  ★ 新最佳!")

# 保存最佳模型
print(f"\n{'='*70}")
print("保存最佳模型")
print("="*70)
print(f"最佳: {best_name}")
print(f"  AUC: {best_auc:.4f}")
print(f"  精确率@90: {best_prec:.4f}")

model_file = MODEL_DIR / f"ml_nn_v8_best_{datetime.now().strftime('%Y%m%d_%H%M')}.pkl"
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': best_model,
        'scaler': best_scaler,
        'features': FEATURES,
        'metadata': {
            'auc': best_auc,
            'precision_90': best_prec,
            'name': best_name,
            'version': 'V8',
            'train_samples': len(X_train),
            'stocks': stocks_ok
        }
    }, f)

print(f"保存: {model_file.name}")

# 更新生产模型
prod_file = MODEL_DIR / "ml_nn_production.pkl"
if prod_file.exists():
    with open(prod_file, 'rb') as f:
        old = pickle.load(f)
    old_auc = old.get('metadata', {}).get('auc', 0.63)
    
    if best_auc > old_auc:
        print(f"\n★ 性能超越生产模型 (旧AUC={old_auc:.4f})")
        with open(prod_file, 'wb') as f:
            pickle.dump({
                'model': best_model,
                'scaler': best_scaler,
                'features': FEATURES,
                'metadata': {
                    'auc': best_auc,
                    'precision_90': best_prec,
                    'name': best_name,
                    'version': 'V8',
                    'train_samples': len(X_train)
                }
            }, f)
        print("✅ 生产模型已更新!")
    else:
        print(f"\n生产模型更优 (AUC={old_auc:.4f})")

# 结果汇总
print("\n结果汇总:")
print("| 配置 | AUC | P85 | P90 | P95 | 时间 |")
print("|------|-----|-----|-----|-----|------|")
for r in results:
    print(f"| {r[0]} | {r[1]:.4f} | {r[2]:.4f} | {r[3]:.4f} | {r[4]:.4f} | {r[5]:.1f}s |")

print("\n完成: " + str(datetime.now()))