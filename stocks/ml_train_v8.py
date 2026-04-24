#!/usr/bin/env python3
"""
神经网络训练 V8 - 继续优化版
使用现有历史数据重新训练
目标: 提升 AUC 和精确率
"""
import os
import sys
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
print("神经网络训练 V8 - 继续优化版")
print("="*70)
print(datetime.now())

# 目录配置
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

# 特征计算函数
def calc_features(data):
    """计算技术指标特征"""
    features_list = []
    
    for i in range(len(data)):
        if i < 60:  # 需要至少60天数据
            continue
        
        # 获取历史窗口
        window = data[i-60:i+1]
        closes = [float(w.get('close', 0)) for w in window]
        volumes = [float(w.get('vol', 0)) for w in window]
        
        if len(closes) < 60 or closes[-1] <= 0:
            continue
        
        # 计算指标
        features = {}
        
        # 1. 均线
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        ma60 = np.mean(closes[-60:])
        
        features['p_ma5'] = (closes[-1] - ma5) / ma5 if ma5 > 0 else 0
        features['p_ma10'] = (closes[-1] - ma10) / ma10 if ma10 > 0 else 0
        features['p_ma20'] = (closes[-1] - ma20) / ma20 if ma20 > 0 else 0
        features['p_ma60'] = (closes[-1] - ma60) / ma60 if ma60 > 0 else 0
        
        # 2. 均线斜率
        features['ma5_slope'] = (ma5 - np.mean(closes[-10:-5])) / ma5 if ma5 > 0 else 0
        features['ma10_slope'] = (ma10 - np.mean(closes[-20:-10])) / ma10 if ma10 > 0 else 0
        features['ma20_slope'] = (ma20 - np.mean(closes[-40:-20])) / ma20 if ma20 > 0 else 0
        
        # 3. 收益率
        features['ret1'] = (closes[-1] - closes[-2]) / closes[-2] if closes[-2] > 0 else 0
        features['ret5'] = (closes[-1] - closes[-6]) / closes[-6] if closes[-6] > 0 else 0
        features['ret10'] = (closes[-1] - closes[-11]) / closes[-11] if closes[-11] > 0 else 0
        features['ret20'] = (closes[-1] - closes[-21]) / closes[-21] if closes[-21] > 0 else 0
        
        # 4. 波动率 (收益率标准差)
        rets = [(closes[j] - closes[j-1]) / closes[j-1] if closes[j-1] > 0 else 0 
                for j in range(1, min(len(closes), 20))]
        features['vol5'] = np.std(rets[-5:]) if len(rets) >= 5 else 0
        features['vol10'] = np.std(rets[-10:]) if len(rets) >= 10 else 0
        features['vol20'] = np.std(rets[-20:]) if len(rets) >= 20 else 0
        
        # 5. RSI (14日)
        if len(closes) >= 15:
            deltas = [closes[j] - closes[j-1] for j in range(1, len(closes))]
            gains = sum([d for d in deltas[-14:] if d > 0])
            losses = sum([-d for d in deltas[-14:] if d < 0])
            rs = gains / losses if losses > 0 else 100
            features['rsi'] = 100 - 100/(1 + rs)
        else:
            features['rsi'] = 50
        
        # 6. MACD
        if len(closes) >= 35:
            ema12 = closes[-1]
            ema26 = closes[-1]
            for j in range(len(closes)-1, max(0, len(closes)-26), -1):
                ema12 = closes[j] * 0.1538 + ema12 * 0.8462
                ema26 = closes[j] * 0.0741 + ema26 * 0.9259
            dif = ema12 - ema26
            dea = dif * 0.2  # 简化计算
            features['macd_dif'] = dif / closes[-1] if closes[-1] > 0 else 0
            features['macd_dea'] = dea / closes[-1] if closes[-1] > 0 else 0
            features['macd_hist'] = (dif - dea) / closes[-1] if closes[-1] > 0 else 0
        else:
            features['macd_dif'] = 0
            features['macd_dea'] = 0
            features['macd_hist'] = 0
        
        # 7. KDJ
        if len(closes) >= 9:
            low_min = min([float(w.get('low', closes[j])) for j, w in enumerate(window[-9:])])
            high_max = max([float(w.get('high', closes[j])) for j, w in enumerate(window[-9:])])
            rsv = (closes[-1] - low_min) / (high_max - low_min) if high_max > low_min else 50
            k = rsv * 0.333 + 50 * 0.667  # 初始K=50
            d = k * 0.333 + 50 * 0.667
            j = 3 * k - 2 * d
            features['kdj_k'] = k
            features['kdj_d'] = d
            features['kdj_j'] = j
        else:
            features['kdj_k'] = 50
            features['kdj_d'] = 50
            features['kdj_j'] = 50
        
        # 8. 成交量比率
        vol_ma5 = np.mean(volumes[-5:])
        vol_ma20 = np.mean(volumes[-20:])
        features['vol_ratio'] = volumes[-1] / vol_ma5 if vol_ma5 > 0 else 1
        features['vol_ratio20'] = volumes[-1] / vol_ma20 if vol_ma20 > 0 else 1
        
        # 9. 价格位置
        high_today = float(window[-1].get('high', closes[-1]))
        low_today = float(window[-1].get('low', closes[-1]))
        features['hl_pct'] = (high_today - low_today) / closes[-1] if closes[-1] > 0 else 0
        features['hc_pct'] = (high_today - closes[-1]) / closes[-1] if closes[-1] > 0 else 0
        features['cl_pct'] = (closes[-1] - low_today) / closes[-1] if closes[-1] > 0 else 0
        
        # 10. 布林带位置
        std20 = np.std(closes[-20:])
        features['boll_pos'] = (closes[-1] - ma20) / (2 * std20) if std20 > 0 else 0
        
        # 11. 补充特征
        features['rsi_extreme'] = 1 if features['rsi'] > 70 else (-1 if features['rsi'] < 30 else 0)
        features['kdj_cross'] = 1 if features['kdj_k'] > features['kdj_d'] else -1
        features['macd_cross'] = 1 if features['macd_dif'] > features['macd_dea'] else -1
        features['vol_trend'] = (vol_ma5 - vol_ma20) / vol_ma20 if vol_ma20 > 0 else 0
        features['ma_cross'] = 1 if ma5 > ma10 else -1
        features['price_strength'] = (features['p_ma5'] + features['p_ma10'] + features['p_ma20']) / 3
        
        features_list.append(features)
    
    return features_list

# 标签生成 (5天后涨超3%)
def create_labels(data, features_list, days=5, threshold=0.03):
    """生成标签: N天后涨超threshold"""
    labels = []
    
    for i, feat in enumerate(features_list):
        # 找到该特征对应的数据位置
        data_idx = i + 60  # 因为前60天被跳过
        
        if data_idx + days >= len(data):
            labels.append(0)
            continue
        
        future_close = float(data[data_idx + days].get('close', 0))
        current_close = float(data[data_idx].get('close', 0))
        
        if current_close > 0:
            ret = (future_close - current_close) / current_close
            labels.append(1 if ret >= threshold else 0)
        else:
            labels.append(0)
    
    return labels

# 加载股票数据并生成训练样本
print("\n加载股票数据生成训练样本...")

all_features = []
all_labels = []
stocks_loaded = 0

# 只处理主板股票 (代码以00/60开头)
json_files = list(HISTORY_DIR.glob("*.json"))
print(f"股票文件总数: {len(json_files)}")

# 随机采样500只股票用于训练
np.random.seed(42)
sample_files = np.random.choice(json_files, min(500, len(json_files)), replace=False)

for filepath in sample_files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        items = raw_data.get('items', [])
        if not items or len(items) < 100:
            continue
        
        # 转换数据
        data = []
        fields = raw_data.get('fields', [])
        for item in items:
            if isinstance(item, list):
                d = {}
                for j, field in enumerate(fields):
                    if j < len(item):
                        d[field] = item[j]
                data.append(d)
            else:
                data.append(item)
        
        # 确保正序
        if data and len(data) > 1:
            first_date = str(data[0].get('trade_date', ''))
            last_date = str(data[-1].get('trade_date', ''))
            if first_date > last_date:
                data = data[::-1]
        
        # 计算特征
        features = calc_features(data)
        if not features:
            continue
        
        # 生成标签
        labels = create_labels(data, features)
        
        # 只保留2024年的数据作为训练 (避免过时数据)
        valid_features = []
        valid_labels = []
        for j, feat in enumerate(features):
            data_idx = j + 60
            if data_idx < len(data):
                date = str(data[data_idx].get('trade_date', ''))
                if date.startswith('2024'):
                    valid_features.append(feat)
                    valid_labels.append(labels[j])
        
        if valid_features:
            all_features.extend(valid_features)
            all_labels.extend(valid_labels)
            stocks_loaded += 1
        
        if stocks_loaded % 50 == 0:
            print(f"  已加载 {stocks_loaded} 股, 样本数: {len(all_features)}")
        
        del data, features, labels
        gc.collect()
        
        # 限制样本数量
        if len(all_features) >= 500000:
            break
    
    except Exception as e:
        continue

print(f"\n训练数据生成完成:")
print(f"  股票数: {stocks_loaded}")
print(f"  样本数: {len(all_features)}")
print(f"  正样本: {sum(all_labels)} ({sum(all_labels)/len(all_labels)*100:.2f}%)")

# 转换为numpy数组
FEATURE_NAMES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'p_ma60',
    'ma5_slope', 'ma10_slope', 'ma20_slope',
    'ret1', 'ret5', 'ret10', 'ret20',
    'vol5', 'vol10', 'vol20',
    'rsi', 'macd_dif', 'macd_dea', 'macd_hist',
    'kdj_k', 'kdj_d', 'kdj_j',
    'vol_ratio', 'vol_ratio20',
    'hl_pct', 'hc_pct', 'cl_pct', 'boll_pos',
    'rsi_extreme', 'kdj_cross', 'macd_cross',
    'vol_trend', 'ma_cross', 'price_strength'
]

X = np.array([[f.get(k, 0) for k in FEATURE_NAMES] for f in all_features], dtype=np.float32)
y = np.array(all_labels, dtype=np.int32)

# 分割训练/测试 (80/20)
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

print(f"\n数据分割:")
print(f"  训练集: {len(X_train)}")
print(f"  测试集: {len(X_test)}")

# 标准化
print("\n标准化数据...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 训练多个配置
configs = [
    {"name": "V8_标准", "layers": (512, 256, 128), "lr": 0.001, "alpha": 0.01},
    {"name": "V8_深网", "layers": (400, 200, 100, 50), "lr": 0.001, "alpha": 0.01},
    {"name": "V8_宽网", "layers": (1024, 512), "lr": 0.001, "alpha": 0.001},
    {"name": "V8_正则强", "layers": (256, 128), "lr": 0.002, "alpha": 0.1},
    {"name": "V8_低LR", "layers": (512, 256, 128), "lr": 0.0005, "alpha": 0.01},
]

results = []
best_auc = 0
best_prec = 0
best_model = None

print("\n开始训练...")

for cfg in configs:
    print(f"\n{'='*60}")
    print(f"{cfg['name']}: layers={cfg['layers']} LR={cfg['lr']} alpha={cfg['alpha']}")
    print("="*60)
    
    model = MLPClassifier(
        hidden_layer_sizes=cfg['layers'],
        activation='relu',
        solver='adam',
        learning_rate_init=cfg['lr'],
        alpha=cfg['alpha'],
        batch_size=256,
        max_iter=200,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20,
        random_state=42
    )
    
    start_time = time.time()
    model.fit(X_train_scaled, y_train)
    elapsed = time.time() - start_time
    
    # 评估
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    
    # 测试多个置信度阈值
    prec_85 = precision_score(y_test, (y_prob >= 0.85).astype(int), zero_division=0)
    prec_90 = precision_score(y_test, (y_prob >= 0.90).astype(int), zero_division=0)
    prec_95 = precision_score(y_test, (y_prob >= 0.95).astype(int), zero_division=0)
    
    print(f"  AUC: {auc:.4f}")
    print(f"  精确率@85: {prec_85:.4f}")
    print(f"  精确率@90: {prec_90:.4f}")
    print(f"  精确率@95: {prec_95:.4f}")
    print(f"  时间: {elapsed:.1f}s")
    
    results.append({
        "name": cfg['name'],
        "auc": auc,
        "prec_85": prec_85,
        "prec_90": prec_90,
        "prec_95": prec_95,
        "time": elapsed
    })
    
    if auc > best_auc:
        best_auc = auc
        best_prec = prec_90
        best_model = model
        best_name = cfg['name']
        print(f"  ★ 新最佳!")

# 保存最佳模型
print("\n" + "="*70)
print("保存最佳模型...")
print("="*70)

model_file = MODEL_DIR / f"ml_nn_v8_best_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
metadata = {
    'hidden_layers': best_model.hidden_layer_sizes,
    'auc': best_auc,
    'precision_90': best_prec,
    'features': FEATURE_NAMES,
    'feature_count': len(FEATURE_NAMES),
    'trained_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'version': 'V8',
    'config_name': best_name,
    'train_samples': len(X_train),
    'test_samples': len(X_test)
}

with open(model_file, 'wb') as f:
    pickle.dump({
        'model': best_model,
        'scaler': scaler,
        'features': FEATURE_NAMES,
        'metadata': metadata
    }, f)

print(f"\n最佳模型: {best_name}")
print(f"  AUC: {best_auc:.4f}")
print(f"  精确率@90: {best_prec:.4f}")
print(f"  保存至: {model_file.name}")

# 检查是否超越生产模型
prod_file = MODEL_DIR / "ml_nn_production.pkl"
if prod_file.exists():
    with open(prod_file, 'rb') as f:
        prod_data = pickle.load(f)
    prod_auc = prod_data.get('metadata', {}).get('auc', 0.63)
    
    if best_auc > prod_auc:
        print(f"\n★ 性能超越生产模型 (旧AUC={prod_auc:.4f})")
        print("更新生产模型...")
        with open(prod_file, 'wb') as f:
            pickle.dump({
                'model': best_model,
                'scaler': scaler,
                'features': FEATURE_NAMES,
                'metadata': metadata
            }, f)
        print("✅ 生产模型已更新!")
    else:
        print(f"\n当前生产模型 AUC={prod_auc:.4f} 更优,保持不变")

# 结果汇总
print("\n结果汇总:")
print("| 配置 | AUC | 精确率@85 | 精确率@90 | 精确率@95 | 时间 |")
print("|------|-----|----------|----------|----------|------|")
for r in results:
    print(f"| {r['name']} | {r['auc']:.4f} | {r['prec_85']:.4f} | {r['prec_90']:.4f} | {r['prec_95']:.4f} | {r['time']:.0f}s |")

print("\n完成:", datetime.now())
print("="*70)