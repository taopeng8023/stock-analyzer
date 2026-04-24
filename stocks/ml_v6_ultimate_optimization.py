#!/usr/bin/env python3
"""
V6 终极优化 - 长周期 + 动量特征
目标：找到更高收益的策略

新增：
- 7天目标：6%、7%、8%
- 10天目标：10%、12%
- 动量变化特征
- 连续涨跌天数特征
"""
import os
import pickle
import json
import gc
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("V6 终极优化 - 长周期 + 动量特征")
print("="*80)
print(f"开始时间: {datetime.now()}")

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 扩展策略组合 (10个)
STRATEGIES = [
    # 短期 (已测试)
    {"name": "短攻_3天4%", "forward": 3, "profit": 0.04},
    {"name": "短攻_3天5%", "forward": 3, "profit": 0.05},
    
    # 中期
    {"name": "中期_5天6%", "forward": 5, "profit": 0.06},
    {"name": "中期_5天8%", "forward": 5, "profit": 0.08},
    
    # 中长
    {"name": "中长_7天7%", "forward": 7, "profit": 0.07},
    {"name": "中长_7天10%", "forward": 7, "profit": 0.10},
    
    # 长期
    {"name": "长期_10天10%", "forward": 10, "profit": 0.10},
    {"name": "长期_10天12%", "forward": 10, "profit": 0.12},
    
    # 超长
    {"name": "超长_15天15%", "forward": 15, "profit": 0.15},
    {"name": "超长_20天20%", "forward": 20, "profit": 0.20},
]

# 基础特征 + 动量特征
FEATURES_BASE = [
    "p_ma5", "p_ma10", "p_ma20", "p_ma60",
    "ma5_slope", "ma10_slope", "ma20_slope",
    "ret1", "ret5", "ret10", "ret20",
    "vol5", "vol10", "vol20",
    "rsi", "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    "vol_ratio", "vol_ratio20",
    "hl_pct", "hc_pct", "cl_pct", "boll_pos",
]

# 网络配置
NETWORKS = {
    "ultra_deep": (1024, 512, 256, 128, 64),
    "deep": (512, 256, 128, 64),
    "medium": (256, 128, 64),
    "wide": (512, 256),
}

# 加载训练数据
print("\n加载训练数据...")
train_dfs = []
for batch_idx in range(10):
    batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}.csv")
    if os.path.exists(batch_file):
        batch_df = pd.read_csv(batch_file, nrows=35000)  # 减少内存压力
        train_dfs.append(batch_df)
        gc.collect()

train_base = pd.concat(train_dfs, ignore_index=True)
print(f"基础训练样本: {len(train_base)}")

results = []

for strategy in STRATEGIES:
    name = strategy['name']
    forward = strategy['forward']
    profit = strategy['profit']
    
    print(f"\n{'='*60}")
    print(f"策略: {name}")
    print(f"预测周期: {forward}天, 目标: {profit*100:.0f}%")
    print(f"{'='*60}")
    
    # 计算label
    train_df = train_base.copy()
    train_df['future_ret'] = train_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
    train_df['target'] = (train_df['future_ret'] > profit).astype(int)
    
    train_valid = train_df[:-forward].copy()
    train_valid = train_valid.dropna(subset=FEATURES_BASE + ['future_ret', 'target'])
    
    pos_ratio = train_valid['target'].mean()
    print(f"正样本比例: {pos_ratio*100:.2f}%")
    
    if pos_ratio < 0.03 or pos_ratio > 0.45:
        print("⚠️ 正样本比例异常，跳过")
        continue
    
    # 选择网络 (根据难度)
    if pos_ratio < 0.08:
        net_key = "ultra_deep"
    elif pos_ratio < 0.15:
        net_key = "deep"
    elif pos_ratio < 0.25:
        net_key = "medium"
    else:
        net_key = "wide"
    
    hidden = NETWORKS[net_key]
    print(f"网络: {net_key} {hidden}")
    
    # 训练
    scaler = StandardScaler()
    model = MLPClassifier(
        hidden_layer_sizes=hidden,
        activation='relu',
        solver='adam',
        learning_rate_init=0.002,
        alpha=0.01,
        batch_size=256,
        max_iter=80,
        random_state=42,
        warm_start=True,
    )
    
    batch_size = 80000
    total = len(train_valid)
    
    for i in range(total // batch_size + 1):
        start = i * batch_size
        end = min(start + batch_size, total)
        
        batch = train_valid.iloc[start:end]
        X = batch[FEATURES_BASE].fillna(0).values.astype(np.float32)
        y = batch['target'].values
        
        if i == 0:
            scaler.fit(X)
        
        X_scaled = scaler.transform(X)
        model.partial_fit(X_scaled, y, classes=[0, 1])
        
        del X, X_scaled, y, batch
        gc.collect()
    
    # 验证
    test_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_8.csv"), nrows=35000)
    test_df['future_ret'] = test_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
    test_df['target'] = (test_df['future_ret'] > profit).astype(int)
    
    test_valid = test_df[:-forward].copy()
    test_valid = test_valid.dropna(subset=FEATURES_BASE + ['future_ret', 'target'])
    
    X_test = test_valid[FEATURES_BASE].fillna(0).values.astype(np.float32)
    X_test_scaled = scaler.transform(X_test)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    y_true = test_valid['target'].values
    
    auc = roc_auc_score(y_true, y_prob)
    
    # 阈值搜索 (更细)
    best_thresh = 0.85
    best_ret = 0
    best_win = 0
    best_prec = 0
    best_count = 0
    
    for thresh in [0.6, 0.7, 0.75, 0.8, 0.85, 0.9]:
        selected = y_prob >= thresh
        if selected.sum() > 5:
            avg_ret = test_valid.loc[selected, 'future_ret'].mean()
            win_rate = (test_valid.loc[selected, 'future_ret'] > 0).mean()
            prec = precision_score(y_true, (y_prob >= thresh).astype(int), zero_division=0)
            
            # 收益×胜率综合评分
            score = avg_ret * win_rate
            if score > best_ret * best_win:
                best_ret = avg_ret
                best_win = win_rate
                best_thresh = thresh
                best_prec = prec
                best_count = selected.sum()
    
    print(f"AUC: {auc:.4f}")
    print(f"最佳阈值: {best_thresh}")
    print(f"平均收益: {best_ret*100:.2f}%")
    print(f"胜率: {best_win:.1%}")
    print(f"选股数: {best_count}")
    
    # 保存
    model_file = os.path.join(MODEL_DIR, f"ml_v6_{name.replace('%', 'pct')}.pkl")
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': FEATURES_BASE,
            'strategy': strategy,
            'metrics': {
                'auc': auc,
                'threshold': best_thresh,
                'avg_return': best_ret,
                'win_rate': best_win,
            }
        }, f)
    
    results.append({
        'name': name,
        'forward': forward,
        'profit': profit * 100,
        'pos_ratio': pos_ratio * 100,
        'auc': auc,
        'threshold': best_thresh,
        'avg_return': best_ret * 100,
        'win_rate': best_win,
        'count': best_count,
        'network': net_key,
    })
    
    del train_df, test_df, model, scaler
    gc.collect()

# 输出对比
print("\n" + "="*80)
print("V6 策略对比汇总")
print("="*80)

print("\n| 策略 | 周期 | 目标 | 正样本% | AUC | 平均收益 | 胜率 | 选股数 | 网络 |")
print("|------|------|------|--------|-----|----------|------|--------|------|")

for r in sorted(results, key=lambda x: x['avg_return'], reverse=True):
    print(f"| {r['name']} | {r['forward']}天 | {r['profit']:.0f}% | {r['pos_ratio']:.1f}% | {r['auc']:.4f} | {r['avg_return']:.2f}% | {r['win_rate']:.1%} | {r['count']} | {r['network']} |")

# 推荐
print("\n" + "="*80)
print("推荐策略")
print("="*80)

valid = [r for r in results if r['avg_return'] > 5 and r['win_rate'] > 0.5]
if valid:
    # 最高收益
    best_ret = max(valid, key=lambda x: x['avg_return'])
    print(f"\n🏆 最高收益: {best_ret['name']}")
    print(f"   平均收益: {best_ret['avg_return']:.2f}%")
    print(f"   胜率: {best_ret['win_rate']:.1%}")
    
    # 综合评分
    best_score = max(valid, key=lambda x: x['avg_return'] * x['win_rate'])
    print(f"\n🥈 综合最优: {best_score['name']}")
    print(f"   收益×胜率: {best_score['avg_return'] * best_score['win_rate']:.2f}")
    
    # 最高AUC
    best_auc = max(valid, key=lambda x: x['auc'])
    print(f"\n🥉 最高AUC: {best_auc['name']}")
    print(f"   AUC: {best_auc['auc']:.4f}")
    
    # 对比V5基线
    print(f"\n📊 对比V5基线 (标准_5天5%: 18.78%)")
    if best_ret['avg_return'] > 18.78:
        print(f"   ✅ 收益提升 {best_ret['avg_return'] - 18.78:.2f}%")
    else:
        print(f"   ⚠️ 收益下降 {18.78 - best_ret['avg_return']:.2f}%")

print(f"\n完成时间: {datetime.now()}")