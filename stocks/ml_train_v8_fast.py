#!/usr/bin/env python3
"""
神经网络快速训练 V8 - 快速版
优化数据加载速度，减少样本量
"""
import os
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
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("神经网络快速训练 V8")
print("="*70)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

def calc_features_fast(closes, volumes, highs, lows):
    """快速特征计算"""
    n = len(closes)
    if n < 60:
        return None
    
    f = {}
    
    # 均线相对位置
    ma5 = np.mean(closes[-5:])
    ma10 = np.mean(closes[-10:])
    ma20 = np.mean(closes[-20:])
    ma60 = np.mean(closes[-60:])
    
    f['p_ma5'] = (closes[-1] - ma5) / ma5
    f['p_ma10'] = (closes[-1] - ma10) / ma10
    f['p_ma20'] = (closes[-1] - ma20) / ma20
    f['p_ma60'] = (closes[-1] - ma60) / ma60
    
    # 均线斜率
    f['ma5_slope'] = (ma5 - np.mean(closes[-10:-5])) / ma5
    f['ma10_slope'] = (ma10 - np.mean(closes[-20:-10])) / ma10
    f['ma20_slope'] = (ma20 - np.mean(closes[-40:-20])) / ma20
    
    # 收益率
    f['ret1'] = (closes[-1] - closes[-2]) / closes[-2]
    f['ret5'] = (closes[-1] - closes[-6]) / closes[-6]
    f['ret10'] = (closes[-1] - closes[-11]) / closes[-11]
    f['ret20'] = (closes[-1] - closes[-21]) / closes[-21]
    
    # 波动率
    rets = np.diff(closes[-20:]) / closes[-21:-1]
    f['vol5'] = np.std(rets[-5:])
    f['vol10'] = np.std(rets[-10:])
    f['vol20'] = np.std(rets)
    
    # RSI
    deltas = np.diff(closes[-15:])
    gains = np.sum(deltas[deltas > 0])
    losses = np.sum(-deltas[deltas < 0])
    f['rsi'] = 100 - 100/(1 + gains/losses) if losses > 0 else 50
    
    # 成交量比
    vol5 = np.mean(volumes[-5:])
    vol20 = np.mean(volumes[-20:])
    f['vol_ratio'] = volumes[-1] / vol5
    f['vol_ratio20'] = volumes[-1] / vol20
    
    # 价格位置
    f['hl_pct'] = (highs[-1] - lows[-1]) / closes[-1]
    f['hc_pct'] = (highs[-1] - closes[-1]) / closes[-1]
    f['cl_pct'] = (closes[-1] - lows[-1]) / closes[-1]
    
    # 布林带
    std20 = np.std(closes[-20:])
    f['boll_pos'] = (closes[-1] - ma20) / (2 * std20) if std20 > 0 else 0
    
    # 补充特征
    f['rsi_extreme'] = 1 if f['rsi'] > 70 else (-1 if f['rsi'] < 30 else 0)
    f['kdj_cross'] = 0  # 简化
    f['macd_cross'] = 0
    f['vol_trend'] = (vol5 - vol20) / vol20
    f['ma_cross'] = 1 if ma5 > ma10 else -1
    f['price_strength'] = (f['p_ma5'] + f['p_ma10'] + f['p_ma20']) / 3
    
    return f

print("\n快速加载股票数据...")

# 特征列表
FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'p_ma60',
    'ma5_slope', 'ma10_slope', 'ma20_slope',
    'ret1', 'ret5', 'ret10', 'ret20',
    'vol5', 'vol10', 'vol20',
    'rsi', 'vol_ratio', 'vol_ratio20',
    'hl_pct', 'hc_pct', 'cl_pct', 'boll_pos',
    'rsi_extreme', 'kdj_cross', 'macd_cross',
    'vol_trend', 'ma_cross', 'price_strength'
]

X_all = []
y_all = []
stocks_count = 0

# 加载所有股票文件
json_files = list(HISTORY_DIR.glob("*.json"))
print(f"找到 {len(json_files)} 个股票文件")

# 确保按数字排序
import re
json_files.sort(key=lambda x: int(re.search(r'\d+', x.stem).group() if re.search(r'\d+', x.stem) else 0))

# 只取前300只
json_files = json_files[:300]

for filepath in json_files:
    try:
        with open(filepath, 'r') as f:
            raw = json.load(f)
        
        items = raw.get('items', [])
        if len(items) < 100:
            continue
        
        fields = raw.get('fields', [])
        
        # 提取数据数组
        closes = []
        volumes = []
        highs = []
        lows = []
        dates = []
        
        for item in items:
            if isinstance(item, list):
                d = dict(zip(fields, item))
            else:
                d = item
            
            c = float(d.get('close', 0))
            if c > 0:
                closes.append(c)
                volumes.append(float(d.get('vol', 0)))
                highs.append(float(d.get('high', c)))
                lows.append(float(d.get('low', c)))
                dates.append(str(d.get('trade_date', '')))
        
        # 数据已经是倒序(从新到旧)，需要反转(从旧到新)
        if len(closes) > 1:
            closes = closes[::-1]
            volumes = volumes[::-1]
            highs = highs[::-1]
            lows = lows[::-1]
            dates = dates[::-1]
        
        # 计算特征 (只取2024年数据)
        for i in range(60, len(closes) - 5):
            if not dates[i].startswith('2024'):
                continue
            
            feat = calc_features_fast(closes[:i+1], volumes[:i+1], highs[:i+1], lows[:i+1])
            if feat is None:
                continue
            
            # 标签: 5天后涨超3%
            future_close = closes[i + 5]
            current_close = closes[i]
            label = 1 if (future_close - current_close) / current_close >= 0.03 else 0
            
            X_all.append([feat.get(k, 0) for k in FEATURES])
            y_all.append(label)
        
        stocks_count += 1
        if stocks_count % 20 == 0:
            print(f"  加载 {stocks_count} 股, 样本 {len(X_all)}")
        
        gc.collect()
        
        if len(X_all) >= 200000:
            break
    
    except Exception as e:
        continue

print(f"\n数据加载完成: {stocks_count}股, {len(X_all)}样本")

if len(X_all) < 1000:
    print("样本太少,退出")
    exit(1)

# 转换
X = np.array(X_all, dtype=np.float32)
y = np.array(y_all, dtype=np.int32)

# 分割
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"训练: {len(X_train)}, 测试: {len(X_test)}")
print(f"正样本: {sum(y_train)} ({sum(y_train)/len(y_train)*100:.1f}%)")

# 标准化
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# 快速训练配置
configs = [
    ("V8_快", (256, 128), 0.002, 100),
    ("V8_中", (512, 256), 0.001, 150),
    ("V8_深", (300, 150, 75), 0.001, 200),
]

results = []
best_auc = 0
best_model = None

print("\n开始训练...")

for name, layers, lr, max_iter in configs:
    print(f"\n{name}: layers={layers} LR={lr} iter={max_iter}")
    
    model = MLPClassifier(
        hidden_layer_sizes=layers,
        activation='relu',
        solver='adam',
        learning_rate_init=lr,
        alpha=0.01,
        batch_size=256,
        max_iter=max_iter,
        early_stopping=True,
        n_iter_no_change=15,
        random_state=42
    )
    
    t0 = time.time()
    model.fit(X_train_s, y_train)
    elapsed = time.time() - t0
    
    y_prob = model.predict_proba(X_test_s)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    prec90 = precision_score(y_test, (y_prob >= 0.90).astype(int), zero_division=0)
    prec85 = precision_score(y_test, (y_prob >= 0.85).astype(int), zero_division=0)
    
    print(f"  AUC={auc:.4f} 精确率@85={prec85:.4f} @90={prec90:.4f} 时间={elapsed:.1f}s")
    
    results.append((name, auc, prec85, prec90, elapsed))
    
    if auc > best_auc:
        best_auc = auc
        best_model = model
        best_prec = prec90
        best_name = name
        print("  ★ 最佳")

# 保存
print(f"\n最佳模型: {best_name} AUC={best_auc:.4f} 精确率@90={best_prec:.4f}")

model_file = MODEL_DIR / f"ml_nn_v8_{datetime.now().strftime('%Y%m%d_%H%M')}.pkl"
meta = {
    'auc': best_auc,
    'precision_90': best_prec,
    'features': FEATURES,
    'version': 'V8',
    'name': best_name
}

with open(model_file, 'wb') as f:
    pickle.dump({'model': best_model, 'scaler': scaler, 'features': FEATURES, 'metadata': meta}, f)

print(f"保存: {model_file.name}")

# 更新生产模型
prod_file = MODEL_DIR / "ml_nn_production.pkl"
if prod_file.exists():
    with open(prod_file, 'rb') as f:
        old = pickle.load(f)
    old_auc = old.get('metadata', {}).get('auc', 0.63)
    
    if best_auc > old_auc:
        print(f"\n★ 超越旧模型(AUC={old_auc:.4f})")
        with open(prod_file, 'wb') as f:
            pickle.dump({'model': best_model, 'scaler': scaler, 'features': FEATURES, 'metadata': meta}, f)
        print("✅ 生产模型已更新")

print("\n汇总:")
for r in results:
    print(f"  {r[0]}: AUC={r[1]:.4f} P85={r[2]:.4f} P90={r[3]:.4f} {r[4]:.1f}s")

print("\n完成:", datetime.now())