#!/usr/bin/env python3
"""
多策略搜索训练 - 轻量版（分批训练）
内存优化：逐批次训练，不一次性加载全量数据
"""
import os
import json
import pickle
import time
import gc
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, accuracy_score
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("多策略搜索训练 - 轻量版")
print("="*80)
print(datetime.now())

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 简化策略配置（只测试4个关键组合）
STRATEGIES = [
    {"name": "短快_3天2%", "forward": 3, "profit": 0.02},
    {"name": "标准_5天3%", "forward": 5, "profit": 0.03},
    {"name": "中稳_10天5%", "forward": 10, "profit": 0.05},
    {"name": "长期_15天10%", "forward": 15, "profit": 0.10},
]

FEATURES = [
    "p_ma5", "p_ma10", "p_ma20", "p_ma60",
    "ma5_slope", "ma10_slope", "ma20_slope",
    "ret1", "ret5", "ret10", "ret20",
    "vol5", "vol10", "vol20",
    "rsi", "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    "vol_ratio", "vol_ratio20",
    "hl_pct", "hc_pct", "cl_pct", "boll_pos",
]

# 加载一个批次作为测试集
print("\n加载测试数据 (batch_8)...")
test_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_8.csv"))
print(f"测试样本: {len(test_df)}")

strategy_results = []

print("\n" + "="*80)
print("开始多策略训练...")
print("="*80)

for strategy in STRATEGIES:
    name = strategy['name']
    forward = strategy['forward']
    profit = strategy['profit']
    
    print(f"\n{'='*60}")
    print(f"策略: {name} | 预测{forward}天涨超{profit*100}%")
    print("="*60)
    
    # 计算label（使用ret1累计近似）
    test_df['future_ret_approx'] = test_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
    test_df['label_strategy'] = (test_df['future_ret_approx'] > profit).astype(int)
    
    # 排除最后forward天
    test_valid = test_df[:-forward].copy()
    
    # 统计正样本
    pos_ratio = test_valid['label_strategy'].mean()
    print(f"正样本比例: {pos_ratio*100:.2f}%")
    
    if pos_ratio < 0.05 or pos_ratio > 0.50:
        print("⚠️ 正样本异常，跳过")
        continue
    
    # 初始化模型和scaler
    scaler = StandardScaler()
    model = MLPClassifier(
        hidden_layer_sizes=(256, 128, 64),  # 简化网络
        activation='relu',
        solver='adam',
        learning_rate_init=0.003,
        alpha=0.01,
        batch_size=256,
        max_iter=50,
        random_state=42,
        warm_start=True,
    )
    
    # 分批训练
    print("\n分批训练...")
    start_time = time.time()
    
    for batch_idx in range(10):
        batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}.csv")
        if not os.path.exists(batch_file):
            continue
        
        # 加载批次
        batch_df = pd.read_csv(batch_file, nrows=100000)  # 限制每批10万
        
        # 计算label
        batch_df['future_ret_approx'] = batch_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
        batch_df['label_strategy'] = (batch_df['future_ret_approx'] > profit).astype(int)
        
        batch_valid = batch_df[:-forward].copy()
        
        X_batch = batch_valid[FEATURES].fillna(0).values.astype(np.float32)
        y_batch = batch_valid['label_strategy'].values
        
        # 第一批初始化scaler
        if batch_idx == 0:
            scaler.fit(X_batch)
        
        X_batch_scaled = scaler.transform(X_batch)
        
        # 训练
        model.partial_fit(X_batch_scaled, y_batch, classes=[0, 1])
        
        if batch_idx % 2 == 1:
            print(f"  批次{batch_idx+1}/10 完成")
        
        # 清理内存
        del batch_df, X_batch, y_batch, X_batch_scaled
        gc.collect()
    
    elapsed = time.time() - start_time
    print(f"训练耗时: {elapsed:.0f}s")
    
    # 测试评估
    X_test = test_valid[FEATURES].fillna(0).values.astype(np.float32)
    y_test = test_valid['label_strategy'].values
    X_test_scaled = scaler.transform(X_test)
    
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    
    auc = roc_auc_score(y_test, y_prob)
    
    # 计算精确率
    best_prec = 0
    best_thresh = 0
    for thresh in [0.5, 0.6, 0.7, 0.8, 0.85, 0.9]:
        y_pred = (y_prob >= thresh).astype(int)
        if y_pred.sum() > 0:
            prec = precision_score(y_test, y_pred)
            if prec > best_prec:
                best_prec = prec
                best_thresh = thresh
    
    print(f"\n性能:")
    print(f"  AUC: {auc:.4f}")
    print(f"  最佳阈值: {best_thresh}")
    print(f"  精确率: {best_prec:.2%}")
    
    # 保存
    strategy_results.append({
        'name': name,
        'forward_days': forward,
        'profit_pct': profit * 100,
        'pos_ratio': pos_ratio * 100,
        'auc': auc,
        'best_threshold': best_thresh,
        'best_precision': best_prec,
        'train_time': elapsed,
    })
    
    model_file = os.path.join(MODEL_DIR, f"ml_strategy_{name.replace('%', 'pct')}.pkl")
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': FEATURES,
            'strategy': strategy,
        }, f)
    
    print(f"✅ 模型保存: {model_file}")
    
    del model, scaler
    gc.collect()

# 输出对比
print("\n" + "="*80)
print("策略对比汇总")
print("="*80)
print("\n| 策略 | 周期 | 目标 | 正样本% | AUC | 阈值 | 精确率 |")
print("|------|------|------|--------|-----|------|--------|")

for r in strategy_results:
    print(f"| {r['name']} | {r['forward_days']}天 | {r['profit_pct']}% | {r['pos_ratio']:.1f}% | {r['auc']:.4f} | {r['best_threshold']} | {r['best_precision']:.2%} |")

# 最优策略
if strategy_results:
    best = max(strategy_results, key=lambda r: r['auc'])
    print(f"\n🏆 最优策略: {best['name']}")
    print(f"   AUC: {best['auc']:.4f}")
    print(f"   精确率: {best['best_precision']:.2%}")

# 保存结果
with open(os.path.join(MODEL_DIR, 'strategy_comparison_20260414.json'), 'w') as f:
    json.dump({
        'strategies': strategy_results,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, f, indent=2)

print("\n✅ 完成:", datetime.now())