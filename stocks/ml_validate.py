#!/usr/bin/env python3
"""
神经网络模型测试验证
对比新旧模型性能差异
"""
import json
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.metrics import roc_auc_score, precision_score, accuracy_score
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("神经网络模型测试验证")
print("="*70)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

# 加载模型
print("\n加载模型...")
models = {}

# V8初始版
v8_file = MODEL_DIR / "ml_nn_v8_test_20260416_0051.pkl"
if v8_file.exists():
    with open(v8_file, 'rb') as f:
        models['V8初始'] = pickle.load(f)

# Deep优化版（生产模型）
prod_file = MODEL_DIR / "ml_nn_production.pkl"
with open(prod_file, 'rb') as f:
    models['Deep优化'] = pickle.load(f)

# V7旧版本
v7_file = MODEL_DIR / "ml_nn_opt_超大网络_20260413_142659.pkl"
if v7_file.exists():
    with open(v7_file, 'rb') as f:
        models['V7旧版'] = pickle.load(f)

print(f"已加载 {len(models)} 个模型")

# 加载测试数据（独立验证集）
print("\n加载独立验证数据（2025年数据）...")
files = sorted(HISTORY_DIR.glob("*.json"))[200:250]  # 不同的股票
print(f"验证股票: {len(files)} 只")

X_test = []
y_test = []
stock_codes = []

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
        
        # 2025年数据验证
        idx_start = idx_end = None
        for i, d in enumerate(data):
            if d['date'].startswith('2025'):
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
        
        for k in range(valid_start, min(valid_end, valid_start+50)):  # 每股最多50样本
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
            
            X_test.append([f.get(k, 0) for k in FEATURES])
            y_test.append(label)
            stock_codes.append(fp.stem)
    
    except:
        continue

print(f"验证样本: {len(X_test)}, 正样本: {sum(y_test)} ({sum(y_test)/len(y_test)*100:.1f}%)")

if len(X_test) < 100:
    print("验证样本不足")
    exit(1)

X = np.array(X_test, dtype=np.float32)
y = np.array(y_test, dtype=np.int32)

# 对比测试
print("\n"+"="*70)
print("模型性能对比验证")
print("="*70)

results = {}

for name, model_data in models.items():
    model = model_data['model']
    scaler = model_data['scaler']
    
    # 检查特征匹配
    model_features = model_data.get('features', FEATURES)
    if len(model_features) != len(FEATURES):
        print(f"\n{name}: 特征数不匹配({len(model_features)} vs {len(FEATURES)})，跳过")
        continue
    
    X_scaled = scaler.transform(X)
    
    prob = model.predict_proba(X_scaled)[:, 1]
    
    auc = roc_auc_score(y, prob)
    acc = accuracy_score(y, (prob >= 0.5).astype(int))
    p80 = precision_score(y, (prob >= 0.80).astype(int), zero_division=0)
    p85 = precision_score(y, (prob >= 0.85).astype(int), zero_division=0)
    p90 = precision_score(y, (prob >= 0.90).astype(int), zero_division=0)
    p95 = precision_score(y, (prob >= 0.95).astype(int), zero_division=0)
    
    # 置信度分布
    high_conf = np.sum(prob >= 0.90)
    very_high = np.sum(prob >= 0.95)
    
    results[name] = {
        'auc': auc,
        'acc': acc,
        'p80': p80,
        'p85': p85,
        'p90': p90,
        'p95': p95,
        'high_conf': high_conf,
        'very_high': very_high
    }
    
    print(f"\n{name}:")
    print(f"  AUC: {auc:.4f}")
    print(f"  准确率: {acc:.4f}")
    print(f"  精确率@80: {p80:.4f}")
    print(f"  精确率@85: {p85:.4f}")
    print(f"  精确率@90: {p90:.4f} ⭐")
    print(f"  精确率@95: {p95:.4f}")
    print(f"  高置信度样本(≥90): {high_conf} ({high_conf/len(y)*100:.1f}%)")
    print(f"  极高置信度(≥95): {very_high} ({very_high/len(y)*100:.1f}%)")

# 找最佳
print("\n"+"="*70)
print("最佳模型评选")
print("="*70)

best_auc_name = max(results.keys(), key=lambda k: results[k]['auc'])
best_prec_name = max(results.keys(), key=lambda k: results[k]['p90'])

print(f"\nAUC最佳: {best_auc_name} (AUC={results[best_auc_name]['auc']:.4f})")
print(f"精确率最佳: {best_prec_name} (P90={results[best_prec_name]['p90']:.4f})")

# 实际预测案例
print("\n"+"="*70)
print("实际预测案例分析")
print("="*70)

# 使用Deep优化版预测
model = models['Deep优化']['model']
scaler = models['Deep优化']['scaler']
X_scaled = scaler.transform(X)
probs = model.predict_proba(X_scaled)[:, 1]

# 高置信度预测案例
high_conf_idx = np.where(probs >= 0.90)[0]

if len(high_conf_idx) > 0:
    print(f"\n高置信度预测(≥90%)案例:")
    print("-"*70)
    
    for i in high_conf_idx[:10]:  # 展示前10个
        code = stock_codes[i]
        prob = probs[i]
        actual = y[i]
        status = "✅ 正确" if actual == 1 else "❌ 错误"
        
        print(f"{code}: 置信度={prob:.2%} | 实际={actual} | {status}")

# 置信度阈值推荐
print("\n"+"="*70)
print("置信度阈值推荐")
print("="*70)

thresholds = [0.80, 0.85, 0.90, 0.95]
print("\n不同阈值下的精确率和覆盖率:")
print("| 阈值 | 精确率 | 覆盖样本数 | 覆盖率 |")
print("|------|--------|-----------|--------|")

for th in thresholds:
    idx = np.where(probs >= th)[0]
    if len(idx) > 0:
        prec = np.sum(y[idx]) / len(idx)
        coverage = len(idx) / len(y) * 100
        print(f"| {th:.0%} | {prec:.2%} | {len(idx)} | {coverage:.1f}% |")

# 推荐阈值
print("\n推荐操作阈值:")
print("  • 高风险承受: ≥80% (覆盖多，精确率适中)")
print("  • 中等风险: ≥85% (平衡)")
print("  • 低风险: ≥90% (精确率高，覆盖少) ⭐推荐")
print("  • 极低风险: ≥95% (最保守)")

# 保存验证报告
report = {
    '验证时间': str(datetime.now()),
    '验证样本': len(X_test),
    '正样本比例': sum(y_test)/len(y_test),
    '模型对比': results,
    '最佳AUC': best_auc_name,
    '最佳精确率': best_prec_name,
    '推荐阈值': '≥90%'
}

report_file = MODEL_DIR / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
with open(report_file, 'w') as f:
    json.dump(report, f, indent=2)

print(f"\n验证报告已保存: {report_file.name}")
print("\n验证完成:", datetime.now())