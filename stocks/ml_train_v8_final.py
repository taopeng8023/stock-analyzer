#!/usr/bin/env python3
"""
神经网络训练 V8 - 正确版
正确处理数据顺序和日期范围
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
print("神经网络训练 V8")
print("="*70)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'ret10', 'vol5', 'vol10', 'rsi', 
            'vol_ratio', 'hl_pct', 'boll_pos', 'price_strength']

print("\n加载股票数据...")

X_all = []
y_all = []
stocks_count = 0

files = sorted(HISTORY_DIR.glob("*.json"))[:300]

for fp in files:
    try:
        with open(fp) as f:
            raw = json.load(f)
        
        items = raw['items']
        fields = raw['fields']
        
        if len(items) < 100:
            continue
        
        # 解析并反转（从旧到新）
        data = []
        for item in items[::-1]:  # 反转一次
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
        
        # 现在data是正序（从20221219到20260415）
        
        # 找2024年数据的范围
        idx_2024_start = None
        idx_2024_end = None
        
        for i, d in enumerate(data):
            date = d['date']
            if date.startswith('2024'):
                if idx_2024_start is None:
                    idx_2024_start = i
                idx_2024_end = i
        
        if idx_2024_start is None:
            continue
        
        # 确保范围有效（需要有足够的历史数据）
        # 需要60天历史 + 5天未来
        valid_start = max(60, idx_2024_start)
        valid_end = min(len(data) - 5, idx_2024_end)
        
        if valid_end <= valid_start:
            continue
        
        closes = [d['close'] for d in data]
        volumes = [d['vol'] for d in data]
        highs = [d['high'] for d in data]
        lows = [d['low'] for d in data]
        
        # 计算特征
        for i in range(valid_start, valid_end):
            c = closes[i]
            
            # 均线
            ma5 = np.mean(closes[i-5:i+1])
            ma10 = np.mean(closes[i-10:i+1])
            ma20 = np.mean(closes[i-20:i+1])
            
            f = {}
            f['p_ma5'] = (c - ma5) / ma5
            f['p_ma10'] = (c - ma10) / ma10
            f['p_ma20'] = (c - ma20) / ma20
            
            # 收益率
            f['ret5'] = (c - closes[i-5]) / closes[i-5]
            f['ret10'] = (c - closes[i-10]) / closes[i-10]
            
            # 波动率
            rets = [(closes[j] - closes[j-1]) / closes[j-1] 
                    for j in range(max(1, i-20), i)]
            f['vol5'] = np.std(rets[-5:]) if len(rets) >= 5 else 0
            f['vol10'] = np.std(rets[-10:]) if len(rets) >= 10 else 0
            
            # RSI
            deltas = [closes[j+1] - closes[j] for j in range(max(0, i-15), i)]
            gains = sum(d for d in deltas if d > 0)
            losses = sum(-d for d in deltas if d < 0)
            f['rsi'] = 100 - 100/(1 + gains/losses) if losses > 0 else 50
            
            # 成交量
            vol5 = np.mean(volumes[i-5:i+1])
            f['vol_ratio'] = volumes[i] / vol5 if vol5 > 0 else 1
            
            # 价格范围
            f['hl_pct'] = (highs[i] - lows[i]) / c
            
            # 布林带
            std20 = np.std(closes[i-20:i+1])
            f['boll_pos'] = (c - ma20) / (2*std20) if std20 > 0 else 0
            
            f['price_strength'] = (f['p_ma5'] + f['p_ma10'] + f['p_ma20']) / 3
            
            # 标签: 5天后涨超3%
            future = closes[i+5]
            label = 1 if (future - c) / c >= 0.03 else 0
            
            X_all.append([f.get(k, 0) for k in FEATURES])
            y_all.append(label)
        
        stocks_count += 1
        if stocks_count % 30 == 0:
            print(f"  {stocks_count}股, {len(X_all)}样本")
        
        if len(X_all) >= 100000:
            break
    
    except Exception as e:
        continue

print(f"\n数据完成: {stocks_count}股, {len(X_all)}样本, 正样本: {sum(y_all)} ({sum(y_all)/len(y_all)*100:.1f}%)")

if len(X_all) < 1000:
    print("样本不足，退出")
    exit(1)

X = np.array(X_all, dtype=np.float32)
y = np.array(y_all, dtype=np.int32)

# 分割
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")

# 标准化
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# 训练
print("\n开始训练...")

configs = [
    ("V8_小", (128, 64), 0.002),
    ("V8_中", (256, 128), 0.001),
    ("V8_大", (512, 256), 0.001),
]

results = []
best_auc = 0
best_model = None
best_name = ""

for name, layers, lr in configs:
    print(f"\n{name}: layers={layers} lr={lr}")
    
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
    elapsed = time.time() - t0
    
    prob = m.predict_proba(X_test_s)[:, 1]
    auc = roc_auc_score(y_test, prob)
    p85 = precision_score(y_test, (prob >= 0.85).astype(int), zero_division=0)
    p90 = precision_score(y_test, (prob >= 0.90).astype(int), zero_division=0)
    
    print(f"  AUC={auc:.4f} P85={p85:.4f} P90={p90:.4f} 时间={elapsed:.1f}s")
    
    results.append((name, auc, p85, p90, elapsed))
    
    if auc > best_auc:
        best_auc = auc
        best_model = m
        best_prec = p90
        best_name = name
        print("  ★ 最佳!")

# 保存
print(f"\n最佳模型: {best_name}")
print(f"  AUC: {best_auc:.4f}")
print(f"  精确率@90: {best_prec:.4f}")

model_file = MODEL_DIR / f"ml_nn_v8_{datetime.now().strftime('%Y%m%d_%H%M')}.pkl"
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': best_model,
        'scaler': scaler,
        'features': FEATURES,
        'metadata': {
            'auc': best_auc,
            'precision_90': best_prec,
            'name': best_name,
            'version': 'V8',
            'train_samples': len(X_train),
            'features_count': len(FEATURES)
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
                'scaler': scaler,
                'features': FEATURES,
                'metadata': {
                    'auc': best_auc,
                    'precision_90': best_prec,
                    'name': best_name,
                    'version': 'V8'
                }
            }, f)
        print("✅ 生产模型已更新!")
    else:
        print(f"\n生产模型更优 (AUC={old_auc:.4f}),保持不变")

print("\n结果汇总:")
for r in results:
    print(f"  {r[0]}: AUC={r[1]:.4f} P85={r[2]:.4f} P90={r[3]:.4f} {r[4]:.1f}s")

print("\n完成: " + str(datetime.now()))