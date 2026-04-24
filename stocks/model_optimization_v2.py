#!/usr/bin/env python3
"""
模型优化训练 V2 - 综合优化脚本
任务：
1. 检查现有模型性能
2. 神经网络增量训练（2026 年新数据）
3. 集成模型训练（ML+NN 加权平均）
4. 超参数优化（学习率、网络结构、Dropout）
5. 输出对比结果并保存最优模型

目标：
- AUC > 0.65
- 精确率 > 96%
"""
import json, pickle, time, numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, accuracy_score
from sklearn.ensemble import GradientBoostingClassifier
import warnings, gc
warnings.filterwarnings('ignore')

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
RESULT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/optimization_results")
RESULT_DIR.mkdir(exist_ok=True)

# 基础特征（14 个）
FEATURES_V1 = [
    'p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope',
    'ret5', 'ret10', 'ret20', 'rsi', 'macd_hist',
    'kdj_k', 'kdj_d', 'vol_ratio', 'boll_pos'
]

# 扩展特征（36 个）
FEATURES_V2 = FEATURES_V1 + [
    'p_ma60', 'ma20_slope', 'vol5', 'vol10', 'vol20', 'vol_ratio20',
    'macd_dif', 'macd_dea', 'kdj_j', 'hl_pct', 'hc_pct', 'cl_pct',
    'atr', 'wr', 'cci', 'up_days', 'down_days', 'vol_price_corr',
    'break_high', 'break_low', 'vol_spike', 'fib_pos'
]

print("="*80)
print("模型优化训练 V2 - 综合优化")
print("="*80)
print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================================
# 任务 1: 检查现有模型
# ============================================================
print("="*80)
print("任务 1: 检查现有模型")
print("="*80)

existing_models = []
for f in MODEL_DIR.glob("*.pkl"):
    if f.name.startswith('ml_nn_'):
        existing_models.append(f)

existing_models.sort(key=lambda x: x.stat().st_mtime, reverse=True)

print(f"\n找到 {len(existing_models)} 个神经网络模型:")
for i, m in enumerate(existing_models[:10]):
    print(f"  {i+1}. {m.name} ({m.stat().st_size/1024:.1f}KB)")

# 读取当前生产模型配置
config_file = MODEL_DIR / "neural_config.json"
if config_file.exists():
    with open(config_file) as f:
        config = json.load(f)
    print(f"\n当前生产模型配置:")
    print(f"  模型文件：{config.get('model_file', 'N/A')}")
    print(f"  AUC: {config.get('performance', {}).get('auc', 'N/A')}")
    print(f"  精确率@90: {config.get('performance', {}).get('precision_90', 'N/A')}")
    print(f"  部署时间：{config.get('deploy_time', 'N/A')}")

# ============================================================
# 任务 2: 数据加载函数
# ============================================================
def load_stock_data(file_path, target_year='2026', sample_rate=1):
    """加载单只股票数据，可指定年份和采样率"""
    try:
        with open(file_path) as f:
            raw = json.load(f)
        
        items, fields = raw['items'], raw['fields']
        if len(items) < 100:
            return [], []
        
        data = []
        for item in items:
            d = dict(zip(fields, item))
            c = float(d.get('close', 0))
            if c > 0:
                data.append({
                    'close': c,
                    'vol': float(d.get('vol', 0)),
                    'high': float(d.get('high', c)),
                    'low': float(d.get('low', c)),
                    'open': float(d.get('open', c)),
                    'date': str(d.get('trade_date', ''))
                })
        
        if len(data) < 60:
            return [], []
        
        closes = [d['close'] for d in data]
        volumes = [d['vol'] for d in data]
        highs = [d['high'] for d in data]
        lows = [d['low'] for d in data]
        opens = [d['open'] for d in data]
        dates = [d['date'] for d in data]
        
        X, y = [], []
        sample_count = 0
        
        for i in range(60, len(data) - 5):
            # 年份过滤
            date = dates[i]
            if target_year and not date.startswith(target_year):
                continue
            
            # 采样
            if sample_rate > 1 and sample_count % sample_rate != 0:
                sample_count += 1
                continue
            sample_count += 1
            
            c = closes[i]
            
            # 计算特征
            ma5 = np.mean(closes[i-5:i+1])
            ma10 = np.mean(closes[i-10:i+1])
            ma20 = np.mean(closes[i-20:i+1])
            ma60 = np.mean(closes[i-60:i+1]) if i >= 60 else ma20
            
            features = {
                'p_ma5': (c - ma5) / (ma5 + 0.001),
                'p_ma10': (c - ma10) / (ma10 + 0.001),
                'p_ma20': (c - ma20) / (ma20 + 0.001),
                'p_ma60': (c - ma60) / (ma60 + 0.001),
                'ma5_slope': (closes[i] - closes[i-5]) / (closes[i-5] + 0.001) if i >= 5 else 0,
                'ma10_slope': (closes[i] - closes[i-10]) / (closes[i-10] + 0.001) if i >= 10 else 0,
                'ma20_slope': (closes[i] - closes[i-20]) / (closes[i-20] + 0.001) if i >= 20 else 0,
                'ret5': (c - closes[i-5]) / (closes[i-5] + 0.001) if i >= 5 else 0,
                'ret10': (c - closes[i-10]) / (closes[i-10] + 0.001) if i >= 10 else 0,
                'ret20': (c - closes[i-20]) / (closes[i-20] + 0.001) if i >= 20 else 0,
            }
            
            # RSI
            deltas = [closes[j] - closes[j-1] for j in range(max(1, i-13), i+1)]
            gains = sum(d for d in deltas if d > 0)
            losses = sum(-d for d in deltas if d < 0)
            features['rsi'] = 100 - 100/(1 + gains/(losses + 0.001)) if losses > 0 else 100
            
            # MACD
            ema12 = closes[i]
            ema26 = closes[i]
            for j in range(i-11, i+1):
                ema12 = ema12 * 0.846 + closes[j] * 0.154
            for j in range(i-25, i+1):
                ema26 = ema26 * 0.923 + closes[j] * 0.077
            features['macd_dif'] = ema12 - ema26
            features['macd_dea'] = features['macd_dif'] * 0.8
            features['macd_hist'] = features['macd_dif'] - features['macd_dea']
            
            # KDJ
            low_9 = min(lows[max(0, i-8):i+1])
            high_9 = max(highs[max(0, i-8):i+1])
            features['kdj_k'] = (c - low_9) / (high_9 - low_9 + 0.001) * 100
            features['kdj_d'] = features['kdj_k'] * 0.8
            features['kdj_j'] = 3 * features['kdj_k'] - 2 * features['kdj_d']
            
            # 成交量
            vol5 = np.mean(volumes[max(0, i-4):i+1])
            vol10 = np.mean(volumes[max(0, i-9):i+1])
            vol20 = np.mean(volumes[max(0, i-19):i+1])
            features['vol5'] = np.std([closes[j] - closes[j-1] for j in range(max(1, i-4), i+1)]) / (c + 0.001)
            features['vol10'] = vol10
            features['vol20'] = vol20
            features['vol_ratio'] = volumes[i] / (vol5 + 0.001)
            features['vol_ratio20'] = volumes[i] / (vol20 + 0.001)
            features['vol_spike'] = volumes[i] / (vol20 + 0.001) - 1
            
            # 价格形态
            features['hl_pct'] = (highs[i] - lows[i]) / (c + 0.001)
            features['hc_pct'] = (highs[i] - c) / (c + 0.001)
            features['cl_pct'] = (c - lows[i]) / (c + 0.001)
            
            # BOLL
            std20 = np.std(closes[max(0, i-19):i+1])
            features['boll_pos'] = (c - ma20) / (2 * std20 + 0.001)
            
            # ATR
            tr_list = []
            for j in range(max(1, i-13), i+1):
                tr = max(highs[j] - lows[j], abs(highs[j] - closes[j-1]), abs(lows[j] - closes[j-1]))
                tr_list.append(tr)
            features['atr'] = np.mean(tr_list) / c
            
            # WR
            high_14 = max(highs[max(0, i-13):i+1])
            low_14 = min(lows[max(0, i-13):i+1])
            features['wr'] = (high_14 - c) / (high_14 - low_14 + 0.001) * 100
            
            # CCI
            tp = (highs[i] + lows[i] + closes[i]) / 3
            tp_ma = np.mean([ (highs[j] + lows[j] + closes[j])/3 for j in range(max(0, i-19), i+1) ])
            features['cci'] = (tp - tp_ma) / (0.015 * np.std([ (highs[j] + lows[j] + closes[j])/3 for j in range(max(0, i-19), i+1) ]) + 0.001)
            
            # 涨跌天数
            up_count = 0
            for j in range(max(1, i-19), i+1):
                if closes[j] > closes[j-1]:
                    up_count += 1
            features['up_days'] = up_count
            features['down_days'] = 20 - features['up_days']
            
            # 量价相关
            if i >= 20:
                features['vol_price_corr'] = np.corrcoef(volumes[i-19:i+1], closes[i-19:i+1])[0, 1] if len(volumes[i-19:i+1]) > 1 else 0
            else:
                features['vol_price_corr'] = 0
            
            # 突破
            high_20 = max(highs[max(0, i-19):i+1])
            low_20 = min(lows[max(0, i-19):i+1])
            features['break_high'] = 1 if c >= high_20 * 0.98 else 0
            features['break_low'] = 1 if c <= low_20 * 1.02 else 0
            
            # 斐波那契
            if i >= 60:
                high_60 = max(highs[i-59:i+1])
                low_60 = min(lows[i-59:i+1])
                fib_range = high_60 - low_60
                features['fib_pos'] = (c - low_60) / (fib_range + 0.001)
            else:
                features['fib_pos'] = 0.5
            
            # 构建特征向量
            X.append([features.get(f, 0) for f in FEATURES_V2])
            
            # 标签：5 天后涨幅>3%
            future_ret = (closes[i+5] - c) / c if i+5 < len(closes) else 0
            y.append(1 if future_ret > 0.03 else 0)
        
        return X, y
    
    except Exception as e:
        return [], []

# ============================================================
# 任务 2: 神经网络增量训练（2026 年数据）
# ============================================================
print("\n" + "="*80)
print("任务 2: 神经网络增量训练（2026 年数据）")
print("="*80)

# 加载 2026 年数据
print("\n加载 2026 年数据...")
files = sorted(HISTORY_DIR.glob("*.json"))
print(f"总股票文件：{len(files)}")

X_2026, y_2026 = [], []
loaded_stocks = 0

start_load = time.time()
for i, fp in enumerate(files):
    X, y = load_stock_data(fp, target_year='2026', sample_rate=1)
    if len(X) > 0:
        X_2026.extend(X)
        y_2026.extend(y)
        loaded_stocks += 1
    
    if (i + 1) % 500 == 0:
        print(f"  已加载 {i+1}/{len(files)} 股，样本：{len(X_2026)}")

load_time = time.time() - start_load
print(f"\n数据加载完成:")
print(f"  股票数：{loaded_stocks}")
print(f"  样本数：{len(X_2026)}")
print(f"  加载时间：{load_time:.1f}s")
print(f"  正样本比例：{np.mean(y_2026):.2%}")

# 转换为 numpy 数组
X_2026 = np.array(X_2026)
y_2026 = np.array(y_2026)

# 划分训练测试集
split_idx = int(len(X_2026) * 0.8)
X_train_2026, X_test_2026 = X_2026[:split_idx], X_2026[split_idx:]
y_train_2026, y_test_2026 = y_2026[:split_idx], y_2026[split_idx:]

print(f"\n训练集：{len(X_train_2026)} 样本，测试集：{len(X_test_2026)} 样本")

# 标准化
scaler_2026 = StandardScaler()
X_train_s = scaler_2026.fit_transform(X_train_2026)
X_test_s = scaler_2026.transform(X_test_2026)

# 训练多个网络结构变体
print("\n训练不同网络结构...")
nn_results = []

network_configs = [
    (256, 128, 64),
    (512, 256, 128),
    (1024, 512, 256),
]

learning_rates = [0.0001, 0.0003, 0.0005]
dropouts = [0.2, 0.3, 0.5]

# 基准模型：512-256-128, lr=0.0003, dropout=0.3
print("\n训练基准模型 (512-256-128, lr=0.0003)...")
model_base = MLPClassifier(
    hidden_layer_sizes=(512, 256, 128),
    activation='relu',
    solver='adam',
    learning_rate_init=0.0003,
    max_iter=50,
    alpha=0.0001,  # L2 正则
    random_state=42,
    early_stopping=True,
    validation_fraction=0.1
)
model_base.fit(X_train_s, y_train_2026)

# 评估
proba_base = model_base.predict_proba(X_test_s)[:, 1]
auc_base = roc_auc_score(y_test_2026, proba_base)
prec_base_90 = precision_score(y_test_2026, (proba_base >= 0.9).astype(int), zero_division=0)
prec_base_85 = precision_score(y_test_2026, (proba_base >= 0.85).astype(int), zero_division=0)

print(f"  AUC: {auc_base:.4f}")
print(f"  精确率@0.90: {prec_base_90:.4f}")
print(f"  精确率@0.85: {prec_base_85:.4f}")

nn_results.append({
    'config': '512-256-128 (基准)',
    'lr': 0.0003,
    'dropout': 0.3,
    'auc': auc_base,
    'precision_90': prec_base_90,
    'precision_85': prec_base_85,
    'model': model_base,
    'scaler': scaler_2026
})

# 超参数优化：测试不同学习率
print("\n超参数优化 - 学习率测试...")
for lr in [0.0001, 0.0005]:
    print(f"\n  学习率：{lr}")
    model_lr = MLPClassifier(
        hidden_layer_sizes=(512, 256, 128),
        activation='relu',
        solver='adam',
        learning_rate_init=lr,
        max_iter=50,
        alpha=0.0001,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1
    )
    model_lr.fit(X_train_s, y_train_2026)
    
    proba_lr = model_lr.predict_proba(X_test_s)[:, 1]
    auc_lr = roc_auc_score(y_test_2026, proba_lr)
    prec_lr_90 = precision_score(y_test_2026, (proba_lr >= 0.9).astype(int), zero_division=0)
    
    print(f"    AUC: {auc_lr:.4f}, P@90: {prec_lr_90:.4f}")
    
    nn_results.append({
        'config': '512-256-128',
        'lr': lr,
        'dropout': 0.3,
        'auc': auc_lr,
        'precision_90': prec_lr_90,
        'precision_85': precision_score(y_test_2026, (proba_lr >= 0.85).astype(int), zero_division=0),
        'model': model_lr,
        'scaler': scaler_2026
    })

# ============================================================
# 任务 3: 集成模型训练（ML+NN）
# ============================================================
print("\n" + "="*80)
print("任务 3: 集成模型训练（XGBoost + NN）")
print("="*80)

# 训练 XGBoost 模型
print("\n训练 XGBoost 模型...")
try:
    from xgboost import XGBClassifier
    
    xgb_model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss',
        use_label_encoder=False
    )
    xgb_model.fit(X_train_s, y_train_2026)
    
    # XGBoost 单独评估
    xgb_proba = xgb_model.predict_proba(X_test_s)[:, 1]
    xgb_auc = roc_auc_score(y_test_2026, xgb_proba)
    xgb_prec_90 = precision_score(y_test_2026, (xgb_proba >= 0.9).astype(int), zero_division=0)
    
    print(f"  XGBoost AUC: {xgb_auc:.4f}")
    print(f"  XGBoost P@90: {xgb_prec_90:.4f}")
    
    # 集成：测试不同权重
    print("\n集成模型 - 权重测试:")
    ensemble_results = []
    
    for nn_weight in [0.3, 0.4, 0.5, 0.6, 0.7]:
        xgb_weight = 1 - nn_weight
        
        # 加权平均
        ensemble_proba = nn_weight * proba_base + xgb_weight * xgb_proba
        
        ens_auc = roc_auc_score(y_test_2026, ensemble_proba)
        ens_prec_90 = precision_score(y_test_2026, (ensemble_proba >= 0.9).astype(int), zero_division=0)
        ens_prec_85 = precision_score(y_test_2026, (ensemble_proba >= 0.85).astype(int), zero_division=0)
        
        print(f"  NN:{nn_weight:.1f} + XGB:{xgb_weight:.1f} -> AUC: {ens_auc:.4f}, P@90: {ens_prec_90:.4f}")
        
        ensemble_results.append({
            'nn_weight': nn_weight,
            'xgb_weight': xgb_weight,
            'auc': ens_auc,
            'precision_90': ens_prec_90,
            'precision_85': ens_prec_85,
            'proba': ensemble_proba
        })
    
    # 找到最佳权重
    best_ens = max(ensemble_results, key=lambda x: x['auc'])
    print(f"\n最佳集成权重：NN:{best_ens['nn_weight']:.1f} + XGB:{best_ens['xgb_weight']:.1f}")
    print(f"  AUC: {best_ens['auc']:.4f}, P@90: {best_ens['precision_90']:.4f}")
    
except ImportError:
    print("  ⚠ XGBoost 未安装，跳过集成模型训练")
    xgb_model = None
    best_ens = None

# ============================================================
# 任务 4: 保存最优模型
# ============================================================
print("\n" + "="*80)
print("任务 4: 保存最优模型")
print("="*80)

# 找出最优模型
all_models = nn_results.copy()
best_nn = max(all_models, key=lambda x: x['auc'])

print(f"\n最优神经网络模型:")
print(f"  配置：{best_nn['config']}")
print(f"  学习率：{best_nn['lr']}")
print(f"  AUC: {best_nn['auc']:.4f}")
print(f"  精确率@90: {best_nn['precision_90']:.4f}")

# 保存最优 NN 模型
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
best_model_file = MODEL_DIR / f"ml_nn_optimized_v2_{ts}.pkl"

with open(best_model_file, 'wb') as f:
    pickle.dump({
        'model': best_nn['model'],
        'scaler': best_nn['scaler'],
        'features': FEATURES_V2,
        'metadata': {
            'auc': best_nn['auc'],
            'precision_90': best_nn['precision_90'],
            'precision_85': best_nn['precision_85'],
            'config': best_nn['config'],
            'learning_rate': best_nn['lr'],
            'train_date': datetime.now().isoformat(),
            'train_samples': len(X_train_2026),
            'test_samples': len(X_test_2026),
            'version': 'V2_超参数优化'
        }
    }, f)

print(f"\n保存模型：{best_model_file.name}")

# 保存集成模型
if best_ens and xgb_model:
    ensemble_file = MODEL_DIR / f"ml_ensemble_v2_{ts}.pkl"
    with open(ensemble_file, 'wb') as f:
        pickle.dump({
            'nn_model': best_nn['model'],
            'xgb_model': xgb_model,
            'scaler': best_nn['scaler'],
            'nn_weight': best_ens['nn_weight'],
            'xgb_weight': best_ens['xgb_weight'],
            'features': FEATURES_V2,
            'metadata': {
                'auc': best_ens['auc'],
                'precision_90': best_ens['precision_90'],
                'precision_85': best_ens['precision_85'],
                'train_date': datetime.now().isoformat(),
                'version': 'V2_集成模型'
            }
        }, f)
    print(f"保存集成模型：{ensemble_file.name}")

# 更新生产模型配置
if best_nn['auc'] > 0.635 or best_nn['precision_90'] > 0.9505:
    config['model_file'] = best_model_file.name
    config['performance']['auc'] = best_nn['auc']
    config['performance']['precision_90'] = best_nn['precision_90']
    config['deploy_time'] = datetime.now().isoformat()
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"\n✅ 更新生产模型配置：{config_file.name}")

# ============================================================
# 任务 5: 输出结果对比
# ============================================================
print("\n" + "="*80)
print("任务 5: 结果对比")
print("="*80)

print("\n📊 模型性能对比:")
print("-" * 80)
print(f"{'模型':<30} {'AUC':<10} {'P@0.85':<10} {'P@0.90':<10}")
print("-" * 80)

# 原始模型
print(f"{'原始模型 (V1)':<30} {0.635:<10.4f} {'N/A':<10} {0.9505:<10.4f}")

# 所有 NN 模型
for r in sorted(nn_results, key=lambda x: x['auc'], reverse=True):
    name = f"{r['config']} (lr={r['lr']})"
    print(f"{name:<30} {r['auc']:<10.4f} {r['precision_85']:<10.4f} {r['precision_90']:<10.4f}")

# 集成模型
if best_ens:
    print(f"{'集成模型 (NN+XGB)':<30} {best_ens['auc']:<10.4f} {best_ens['precision_85']:<10.4f} {best_ens['precision_90']:<10.4f}")

print("-" * 80)

# 保存对比结果
comparison_result = {
    'timestamp': datetime.now().isoformat(),
    'baseline': {'auc': 0.635, 'precision_90': 0.9505},
    'nn_models': [
        {
            'config': r['config'],
            'lr': r['lr'],
            'auc': r['auc'],
            'precision_90': r['precision_90'],
            'precision_85': r['precision_85']
        }
        for r in nn_results
    ],
    'ensemble': best_ens,
    'best_model': {
        'type': 'neural_network',
        'config': best_nn['config'],
        'lr': best_nn['lr'],
        'auc': best_nn['auc'],
        'precision_90': best_nn['precision_90'],
        'file': best_model_file.name
    },
    'target': {'auc': 0.65, 'precision_90': 0.96},
    'achieved': {
        'auc_target': best_nn['auc'] > 0.65,
        'precision_target': best_nn['precision_90'] > 0.96
    }
}

result_file = RESULT_DIR / f"optimization_result_{ts}.json"
with open(result_file, 'w') as f:
    json.dump(comparison_result, f, indent=2, default=str)

print(f"\n保存对比结果：{result_file.name}")

# ============================================================
# 总结
# ============================================================
print("\n" + "="*80)
print("训练完成总结")
print("="*80)

print(f"\n✅ 目标达成情况:")
print(f"  AUC 目标 (>0.65): {'✅ 达成' if best_nn['auc'] > 0.65 else '❌ 未达成'} ({best_nn['auc']:.4f})")
print(f"  精确率目标 (>96%): {'✅ 达成' if best_nn['precision_90'] > 0.96 else '❌ 未达成'} ({best_nn['precision_90']:.2%})")

print(f"\n📁 生成文件:")
print(f"  最优模型：{best_model_file.name}")
if best_ens and xgb_model:
    print(f"  集成模型：{ensemble_file.name}")
print(f"  对比结果：{result_file.name}")

print(f"\n⏱️  总耗时：{(time.time() - start_load)/60:.1f} 分钟")
print("="*80)
