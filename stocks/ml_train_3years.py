#!/usr/bin/env python3
"""
神经网络训练 - 2024+2025+2026三年混合
提升模型时效性和泛化能力
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
print("神经网络训练 - 2024+2025+2026三年混合")
print("="*70)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

files = sorted(HISTORY_DIR.glob("*.json"))[:200]
print(f"\n加载 {len(files)} 只股票...")

X_all = []
y_all = []
stocks_ok = 0
samples_2024 = 0
samples_2025 = 0
samples_2026 = 0

for fp in files:
    try:
        with open(fp) as f:
            raw = json.load(f)
        
        items = raw['items']
        fields = raw['fields']
        
        if len(items) < 100:
            continue
        
        # 数据从旧到新，无需反转
        data = []
        for item in items:
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
        
        # 2024+2025+2026三年数据
        for i in range(60, len(data) - 5):
            date = dates[i]
            
            # 只取2024/2025/2026年数据
            if not (date.startswith('2024') or date.startswith('2025') or date.startswith('2026')):
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
            
            if date.startswith('2024'):
                samples_2024 += 1
            elif date.startswith('2025'):
                samples_2025 += 1
            else:
                samples_2026 += 1
        
        stocks_ok += 1
        if stocks_ok % 50 == 0:
            print(f"  {stocks_ok}股, {len(X_all)}样本 (2024:{samples_2024}, 2025:{samples_2025}, 2026:{samples_2026})")
    
    except:
        continue

print(f"\n数据完成: {stocks_ok}股")
print(f"  总样本: {len(X_all)}")
print(f"  2024年: {samples_2024} ({samples_2024/len(X_all)*100:.1f}%)")
print(f"  2025年: {samples_2025} ({samples_2025/len(X_all)*100:.1f}%)")
print(f"  2026年: {samples_2026} ({samples_2026/len(X_all)*100:.1f}%)")
print(f"  正样本: {sum(y_all)} ({sum(y_all)/len(y_all)*100:.1f}%)")

if len(X_all) < 50000:
    print("样本不足")
    exit(1)

X = np.array(X_all, dtype=np.float32)
y = np.array(y_all, dtype=np.int32)

# 分割：80%训练，20%测试
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"\n训练集: {len(X_train)}, 测试集: {len(X_test)}")

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

print("\n训练三年混合模型...")
print("网络结构: (512, 256, 128)")

t0 = time.time()
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
elapsed = time.time() - t0

prob = m.predict_proba(X_test_s)[:, 1]
auc = roc_auc_score(y_test, prob)
p50 = precision_score(y_test, (prob >= 0.50).astype(int), zero_division=0)
p60 = precision_score(y_test, (prob >= 0.60).astype(int), zero_division=0)
p70 = precision_score(y_test, (prob >= 0.70).astype(int), zero_division=0)

print(f"\n训练结果:")
print(f"  AUC: {auc:.4f}")
print(f"  精确率@50: {p50:.4f}")
print(f"  确率@60: {p60:.4f}")
print(f"  确率@70: {p70:.4f}")
print(f"  时间: {elapsed:.1f}s")

# 置信度分布分析
high_conf_50 = np.sum(prob >= 0.50)
high_conf_60 = np.sum(prob >= 0.60)
high_conf_70 = np.sum(prob >= 0.70)

print(f"\n置信度分布:")
print(f"  ≥50%: {high_conf_50} ({high_conf_50/len(y_test)*100:.1f}%)")
print(f"  ≥60%: {high_conf_60} ({high_conf_60/len(y_test)*100:.1f}%)")
print(f"  ≥70%: {high_conf_70} ({high_conf_70/len(y_test)*100:.1f}%)")

# 保存
model_file = MODEL_DIR / f"ml_nn_3years_{datetime.now().strftime('%H%M')}.pkl"
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': m,
        'scaler': scaler,
        'features': FEATURES,
        'metadata': {
            'auc': auc,
            'precision_50': p50,
            'precision_60': p60,
            'precision_70': p70,
            'version': 'Mixed2024+2025+2026',
            'train_samples': len(X_train),
            'samples_2024': samples_2024,
            'samples_2025': samples_2025,
            'samples_2026': samples_2026
        }
    }, f)

print(f"\n保存: {model_file.name}")

# 对比之前模型
print("\n"+"="*70)
print("模型对比:")
print("="*70)
print(f"仅2024: AUC=0.6732 (验证2025: 0.56)")
print(f"2024+2025: AUC=0.6279 (验证2025: 0.63)")
print(f"三年混合: AUC={auc:.4f}")

if auc > 0.60:
    print("\n✅ 三年混合模型训练成功!")
    
    # 更新生产模型
    print("更新生产模型...")
    with open(MODEL_DIR / 'ml_nn_production.pkl', 'wb') as f:
        pickle.dump({
            'model': m,
            'scaler': scaler,
            'features': FEATURES,
            'metadata': {
                'auc': auc,
                'precision_50': p50,
                'precision_60': p60,
                'precision_70': p70,
                'version': 'Mixed2024+2025+2026',
                'train_samples': len(X_train)
            }
        }, f)
    print("✅ 生产模型已更新!")
    
    # 推荐阈值
    print("\n推荐置信度阈值:")
    if p50 > 0.30:
        print(f"  ≥50%: 精确率{p50:.2%} (覆盖率{high_conf_50/len(y_test)*100:.1f}%)")
    if p60 > 0.35:
        print(f"  ≥60%: 精确率{p60:.2%} (覆盖率{high_conf_60/len(y_test)*100:.1f}%) ⭐推荐")
    if p70 > 0.40:
        print(f"  ≥70%: 确率{p70:.2%} (覆盖率{high_conf_70/len(y_test)*100:.1f}%)")

print("\n完成:", datetime.now())