#!/usr/bin/env python3
"""
全量训练 - 不采样版本
使用全部数据（约2.9百万样本）
采用增量训练策略避免超时
"""
import json, pickle, time, numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score
import warnings, gc
warnings.filterwarnings('ignore')

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

def load_batch_data(files, batch_id, batch_size=500):
    """分批次加载股票数据（不采样）"""
    start_idx = batch_id * batch_size
    end_idx = min(start_idx + batch_size, len(files))
    
    X_batch, y_batch = [], []
    stocks_ok = 0
    
    for fp in files[start_idx:end_idx]:
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
            
            # 全量数据：不采样
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
                X_batch.append([f.get(k, 0) for k in FEATURES])
                y_batch.append(1 if future_ret5 > 0.03 else 0)
            
            stocks_ok += 1
        except: continue
    
    return np.array(X_batch), np.array(y_batch), stocks_ok

print("="*70, flush=True)
print("神经网络全量训练 - 不采样版本（约2.9百万样本）", flush=True)
print("="*70, flush=True)

files = sorted(HISTORY_DIR.glob("*.json"))
total_files = len(files)
print(f"总股票数: {total_files}", flush=True)
print(f"策略: 每500股一批，全量数据，增量训练", flush=True)

# 初始化模型和标准化器（超激进参数）
model = MLPClassifier(hidden_layer_sizes=(16, 8), activation='relu', solver='adam',
                      learning_rate_init=0.1, max_iter=2, warm_start=True,
                      random_state=42, alpha=0.02)

scaler = StandardScaler()

# 分批次训练
total_samples = 0
total_stocks = 0
batch_results = []
test_X_all, test_y_all = [], []  # 收集测试数据

start_total = time.time()

num_batches = (total_files + 499) // 500

for batch_id in range(num_batches):
    batch_start = time.time()
    
    print(f"\n批次 {batch_id+1}/{num_batches}: 加载股票 {batch_id*500+1}-{min((batch_id+1)*500, total_files)}...", flush=True)
    
    X_batch, y_batch, stocks_ok = load_batch_data(files, batch_id, batch_size=500)
    
    if len(X_batch) == 0:
        print(f"  无数据，跳过", flush=True)
        continue
    
    batch_load_time = time.time() - batch_start
    
    # 分离训练/测试（80/20）
    n_train = int(len(X_batch) * 0.8)
    X_train = X_batch[:n_train]
    X_test = X_batch[n_train:]
    y_train = y_batch[:n_train]
    y_test = y_batch[n_train:]
    
    # 标准化
    if batch_id == 0:
        X_train_s = scaler.fit_transform(X_train)
    else:
        X_train_s = scaler.transform(X_train)
    
    # 增量训练
    train_start = time.time()
    model.fit(X_train_s, y_train)
    batch_train_time = time.time() - train_start
    
    total_samples += len(X_batch)
    total_stocks += stocks_ok
    
    # 收集测试数据（用于最终评估）
    test_X_all.extend(X_test)
    test_y_all.extend(y_test)
    
    batch_time = time.time() - batch_start
    
    print(f"  样本: {len(X_batch)}, 股票: {stocks_ok}, 加载: {batch_load_time:.1f}s, 训练: {batch_train_time:.1f}s", flush=True)
    
    batch_results.append({
        'batch': batch_id+1,
        'samples': len(X_batch),
        'stocks': stocks_ok,
        'load_time': batch_load_time,
        'train_time': batch_train_time
    })
    
    # 及时释放内存
    del X_batch, y_batch, X_train, y_train
    gc.collect()

total_time = time.time() - start_total

print(f"\n训练汇总:", flush=True)
print(f"  总股票: {total_stocks}", flush=True)
print(f"  总样本: {total_samples}", flush=True)
print(f"  测试样本: {len(test_X_all)}", flush=True)
print(f"  总耗时: {total_time:.1f}s", flush=True)

# 最终评估
print(f"\n最终评估（测试集）:", flush=True)
test_X = np.array(test_X_all)
test_y = np.array(test_y_all)
test_X_s = scaler.transform(test_X)

proba = model.predict_proba(test_X_s)[:, 1]
auc = roc_auc_score(test_y, proba)
print(f"  AUC: {auc:.4f}", flush=True)

for t in [0.6, 0.7, 0.8, 0.85, 0.9]:
    pred = (proba >= t).astype(int)
    p = precision_score(test_y, pred, zero_division=0)
    print(f"  P@{t}: {p:.4f} ({sum(pred)}股)", flush=True)

# 保存模型
ts = datetime.now().strftime('%Y%m%d_%H%M')
model_data = {
    'model': model, 'scaler': scaler, 'features': FEATURES,
    'metadata': {
        'auc': auc, 'version': 'V10_全量不采样',
        'total_stocks': total_stocks, 'total_samples': total_samples,
        'test_samples': len(test_y_all), 'total_time': total_time,
        'batches': batch_results, 'strategy': '全量不采样',
        'network': '16-8', 'max_iter': 2
    }
}

for p in [MODEL_DIR / f"ml_nn_full_nosample_{ts}.pkl", MODEL_DIR / "ml_nn_production.pkl"]:
    with open(p, 'wb') as f: pickle.dump(model_data, f)

print(f"\n保存: ml_nn_full_nosample_{ts}.pkl", flush=True)
print("="*70, flush=True)