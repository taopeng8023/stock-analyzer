#!/usr/bin/env python3
"""
快速训练 - 增量更新
使用更多股票数据提升模型
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

print("="*70, flush=True)
print("神经网络快速训练 V10 - 增量更新", flush=True)
print("="*70, flush=True)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
MODEL_DIR.mkdir(exist_ok=True)

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

# 使用更多股票（500股）
files = sorted(HISTORY_DIR.glob("*.json"))[:500]
print(f"\n加载 {len(files)} 只股票...", flush=True)

X_all = []
y_all = []
stocks_ok = 0
samples_2024 = 0
samples_2025 = 0
samples_2026 = 0

start_time = time.time()

for fp in files:
    try:
        with open(fp) as f:
            raw = json.load(f)
        
        items = raw['items']
        fields = raw['fields']
        
        if len(items) < 100:
            continue
        
        # 数据从旧到新
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
            
            # 5日收益率
            ret5 = (closes[i+5] - c) / c if i+5 < len(closes) else 0
            f['ret5'] = ret5
            
            # 5日波动率
            f['vol5'] = np.std([closes[j] - closes[j-1] for j in range(i-4, i+1)]) / c
            
            # RSI
            deltas = [closes[j] - closes[j-1] for j in range(i-13, i+1)]
            gains = sum(d for d in deltas if d > 0)
            losses = sum(-d for d in deltas if d < 0)
            f['rsi'] = 100 - 100/(1 + gains/(losses+0.001)) if losses > 0 else 100
            
            # 量比
            vol5 = np.mean(volumes[i-5:i+1])
            f['vol_ratio'] = volumes[i] / (vol5 + 0.001)
            
            # 振幅
            f['hl_pct'] = (highs[i] - lows[i]) / c
            
            # 布林带位置
            std20 = np.std(closes[i-20:i+1])
            f['boll_pos'] = (c - ma20) / (2 * std20 + 0.001)
            
            X_all.append([f.get(k, 0) for k in FEATURES])
            
            # 标签：5日涨超3%
            y_all.append(1 if ret5 > 0.03 else 0)
            
            if date.startswith('2024'):
                samples_2024 += 1
            elif date.startswith('2025'):
                samples_2025 += 1
            elif date.startswith('2026'):
                samples_2026 += 1
        
        stocks_ok += 1
        
        if stocks_ok % 100 == 0:
            print(f"已处理 {stocks_ok} 股，样本数: {len(X_all)}", flush=True)
    
    except Exception as e:
        continue

print(f"\n数据加载完成:", flush=True)
print(f"  成功股票: {stocks_ok}", flush=True)
print(f"  总样本: {len(X_all)}", flush=True)
print(f"  2024年: {samples_2024}", flush=True)
print(f"  2025年: {samples_2025}", flush=True)
print(f"  2026年: {samples_2026}", flush=True)
print(f"  正样本比例: {sum(y_all)/len(y_all)*100:.2f}%", flush=True)
print(f"  加载耗时: {time.time()-start_time:.1f}秒", flush=True)

# 划分训练集和测试集
X = np.array(X_all)
y = np.array(y_all)

n_train = int(len(X) * 0.8)
X_train, X_test = X[:n_train], X[n_train:]
y_train, y_test = y[:n_train], y[n_train:]

print(f"\n训练集: {len(X_train)}", flush=True)
print(f"测试集: {len(X_test)}", flush=True)

# 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print("\n开始训练模型...", flush=True)
train_start = time.time()

# 使用更深的网络
model = MLPClassifier(
    hidden_layer_sizes=(512, 256, 128),
    activation='relu',
    solver='adam',
    learning_rate_init=0.001,
    max_iter=200,
    early_stopping=True,
    validation_fraction=0.1,
    n_iter_no_change=20,
    random_state=42,
    alpha=0.01,
    verbose=True
)

model.fit(X_train_scaled, y_train)

print(f"\n训练耗时: {time.time()-train_start:.1f}秒", flush=True)

# 评估
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
auc = roc_auc_score(y_test, y_pred_proba)

print(f"\n模型评估:", flush=True)
print(f"  AUC: {auc:.4f}", flush=True)

# 分阈值精确率
for thresh in [0.5, 0.6, 0.7]:
    y_pred = (y_pred_proba >= thresh).astype(int)
    prec = precision_score(y_test, y_pred, zero_division=0)
    print(f"  精确率@{thresh}: {prec:.4f}", flush=True)

# 保存模型
timestamp = datetime.now().strftime('%Y%m%d_%H%M')
model_path = MODEL_DIR / f"ml_nn_v10_{timestamp}.pkl"

model_data = {
    'model': model,
    'scaler': scaler,
    'features': FEATURES,
    'metadata': {
        'auc': auc,
        'precision_50': precision_score(y_test, (y_pred_proba >= 0.5).astype(int), zero_division=0),
        'precision_60': precision_score(y_test, (y_pred_proba >= 0.6).astype(int), zero_division=0),
        'precision_70': precision_score(y_test, (y_pred_proba >= 0.7).astype(int), zero_division=0),
        'version': 'V10_增量500股',
        'train_samples': len(X_train),
        'stocks': stocks_ok,
        'samples_2024': samples_2024,
        'samples_2025': samples_2025,
        'samples_2026': samples_2026
    }
}

with open(model_path, 'wb') as f:
    pickle.dump(model_data, f)

# 更新生产模型
prod_path = MODEL_DIR / "ml_nn_production.pkl"
with open(prod_path, 'wb') as f:
    pickle.dump(model_data, f)

print(f"\n模型已保存:", flush=True)
print(f"  {model_path}", flush=True)
print(f"  {prod_path} (生产模型)", flush=True)
print("="*70, flush=True)
print("训练完成!", flush=True)
print("="*70, flush=True)