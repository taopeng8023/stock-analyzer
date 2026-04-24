#!/usr/bin/env python3
"""
策略搜索 V2 - 扩展组合 + 特征优化
目标：找到能稳定盈利的选股模型

扩展策略：
- 短期高频 (1-3天, 1-2%)
- 中期稳健 (5-10天, 3-5%)
- 长期爆发 (15-20天, 8-15%)

特征优化：
- 测试不同特征组合
- 网络结构调优
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
from sklearn.metrics import roc_auc_score, precision_score, f1_score
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("策略搜索 V2 - 扩展组合 + 特征优化")
print("="*80)
print(f"开始时间: {datetime.now()}")

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 扩展策略配置 (12个组合)
STRATEGIES = [
    # 短期高频
    {"name": "超短_1天1%", "forward": 1, "profit": 0.01},
    {"name": "短快_2天2%", "forward": 2, "profit": 0.02},
    {"name": "短快_3天2%", "forward": 3, "profit": 0.02},
    {"name": "短攻_3天3%", "forward": 3, "profit": 0.03},
    
    # 中期稳健
    {"name": "标准_5天3%", "forward": 5, "profit": 0.03},
    {"name": "中稳_5天4%", "forward": 5, "profit": 0.04},
    {"name": "中稳_7天5%", "forward": 7, "profit": 0.05},
    {"name": "中稳_10天5%", "forward": 10, "profit": 0.05},
    
    # 长期爆发
    {"name": "中攻_10天7%", "forward": 10, "profit": 0.07},
    {"name": "长期_15天10%", "forward": 15, "profit": 0.10},
    {"name": "长攻_15天12%", "forward": 15, "profit": 0.12},
    {"name": "超长_20天15%", "forward": 20, "profit": 0.15},
]

# 特征集
FEATURES_FULL = [
    "p_ma5", "p_ma10", "p_ma20", "p_ma60",
    "ma5_slope", "ma10_slope", "ma20_slope",
    "ret1", "ret5", "ret10", "ret20",
    "vol5", "vol10", "vol20",  # 波动率特征 (不是成交量均线!)
    "rsi", "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    "vol_ratio", "vol_ratio20",
    "hl_pct", "hc_pct", "cl_pct", "boll_pos",
]

# 核心特征集 (精简版，避免过拟合)
FEATURES_CORE = [
    "p_ma5", "p_ma10", "p_ma20",
    "ma5_slope", "ma10_slope",
    "ret1", "ret5", "ret10",
    "vol5", "vol10",  # 波动率
    "rsi", "macd_dif", "macd_hist",
    "kdj_k", "kdj_d",
    "vol_ratio",
    "boll_pos",
]

# 加载测试数据
print("\n加载测试数据...")
test_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_8.csv"))
print(f"测试样本: {len(test_df)}")

results = []

print("\n" + "="*80)
print("开始策略训练...")
print("="*80)

for strategy in STRATEGIES:
    name = strategy['name']
    forward = strategy['forward']
    profit = strategy['profit']
    
    print(f"\n{'='*60}")
    print(f"策略: {name} | 预测{forward}天涨超{profit*100:.1f}%")
    print("="*60)
    
    # 计算label
    test_df['future_ret'] = test_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
    test_df['label'] = (test_df['future_ret'] > profit).astype(int)
    
    test_valid = test_df[:-forward].copy()
    pos_ratio = test_valid['label'].mean()
    
    print(f"正样本比例: {pos_ratio*100:.2f}%")
    
    # 过滤极端情况
    if pos_ratio < 0.03 or pos_ratio > 0.50:
        print("⚠️ 正样本比例异常，跳过")
        continue
    
    # 选择特征集 (正样本少用核心特征，多用全特征)
    features = FEATURES_CORE if pos_ratio < 0.15 else FEATURES_FULL
    print(f"特征数: {len(features)}")
    
    # 网络结构 (根据难度调整)
    if pos_ratio < 0.10:
        # 难度大，用更复杂网络
        hidden = (256, 128, 64, 32)
    elif pos_ratio < 0.20:
        hidden = (256, 128, 64)
    else:
        hidden = (128, 64, 32)
    
    # 初始化
    scaler = StandardScaler()
    model = MLPClassifier(
        hidden_layer_sizes=hidden,
        activation='relu',
        solver='adam',
        learning_rate_init=0.003,
        alpha=0.01,
        batch_size=256,
        max_iter=50,
        random_state=42,
        warm_start=True,
    )
    
    start_time = time.time()
    
    # 分批训练
    print("\n分批训练...")
    for batch_idx in range(10):
        batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}.csv")
        if not os.path.exists(batch_file):
            continue
        
        batch_df = pd.read_csv(batch_file, nrows=100000)
        
        # 计算label
        batch_df['future_ret'] = batch_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
        batch_df['label'] = (batch_df['future_ret'] > profit).astype(int)
        
        batch_valid = batch_df[:-forward].copy()
        
        X_batch = batch_valid[features].fillna(0).values.astype(np.float32)
        y_batch = batch_valid['label'].values
        
        if batch_idx == 0:
            scaler.fit(X_batch)
        
        X_scaled = scaler.transform(X_batch)
        model.partial_fit(X_scaled, y_batch, classes=[0, 1])
        
        if batch_idx % 3 == 2:
            print(f"  批次 {batch_idx+1}/10 完成")
        
        del batch_df, X_batch, y_batch, X_scaled
        gc.collect()
    
    elapsed = time.time() - start_time
    print(f"训练耗时: {elapsed:.0f}s")
    
    # 测试评估
    X_test = test_valid[features].fillna(0).values.astype(np.float32)
    y_test = test_valid['label'].values
    X_test_scaled = scaler.transform(X_test)
    
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    
    # AUC
    try:
        auc = roc_auc_score(y_test, y_prob)
    except:
        auc = 0.5
    
    # 最佳阈值搜索
    best_prec = 0
    best_thresh = 0
    best_f1 = 0
    for thresh in [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]:
        y_pred = (y_prob >= thresh).astype(int)
        if y_pred.sum() > 0 and y_pred.sum() < len(y_pred):
            prec = precision_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            if prec > best_prec:
                best_prec = prec
                best_thresh = thresh
                best_f1 = f1
    
    # 计算期望收益 (假设选股后平均收益)
    selected_idx = y_prob >= best_thresh
    if selected_idx.sum() > 10:
        avg_ret = test_valid.loc[selected_idx, 'future_ret'].mean()
        win_rate = (test_valid.loc[selected_idx, 'future_ret'] > 0).mean()
    else:
        avg_ret = 0
        win_rate = 0
    
    print(f"\n性能评估:")
    print(f"  AUC: {auc:.4f}")
    print(f"  最佳阈值: {best_thresh}")
    print(f"  精确率: {best_prec:.2%}")
    print(f"  F1: {best_f1:.4f}")
    print(f"  选股数: {selected_idx.sum()}")
    print(f"  平均收益: {avg_ret*100:.2f}%")
    print(f"  胜率: {win_rate:.1%}")
    
    # 保存结果
    results.append({
        'name': name,
        'forward_days': forward,
        'profit_pct': profit * 100,
        'pos_ratio': pos_ratio * 100,
        'auc': auc,
        'best_threshold': best_thresh,
        'best_precision': best_prec,
        'best_f1': best_f1,
        'avg_return': avg_ret * 100,
        'win_rate': win_rate,
        'selected_count': int(selected_idx.sum()),
        'train_time': elapsed,
        'features_count': len(features),
    })
    
    # 保存模型
    model_file = os.path.join(MODEL_DIR, f"ml_v2_{name.replace('%', 'pct')}.pkl")
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': features,
            'strategy': strategy,
            'metrics': {
                'auc': auc,
                'precision': best_prec,
                'avg_return': avg_ret,
            }
        }, f)
    
    print(f"✅ 模型保存: {model_file}")
    
    del model, scaler
    gc.collect()

# 输出对比
print("\n" + "="*80)
print("策略对比汇总")
print("="*80)

print("\n| 策略 | 周期 | 目标 | 正样本% | AUC | 精确率 | 平均收益 | 胜率 |")
print("|------|------|------|--------|-----|--------|----------|------|")

for r in sorted(results, key=lambda x: x['avg_return'], reverse=True):
    print(f"| {r['name']} | {r['forward_days']}天 | {r['profit_pct']:.0f}% | {r['pos_ratio']:.1f}% | {r['auc']:.4f} | {r['best_precision']:.1%} | {r['avg_return']:.2f}% | {r['win_rate']:.1%} |")

# 推荐最优策略 (综合考虑收益和稳定性)
print("\n" + "="*80)
print("推荐策略")
print("="*80)

# 筛选有效策略
valid = [r for r in results if r['avg_return'] > 0 and r['win_rate'] > 0.5]
if valid:
    # 按平均收益排序
    best_return = max(valid, key=lambda x: x['avg_return'])
    print(f"\n🏆 最高收益策略: {best_return['name']}")
    print(f"   平均收益: {best_return['avg_return']:.2f}%")
    print(f"   胜率: {best_return['win_rate']:.1%}")
    print(f"   AUC: {best_return['auc']:.4f}")
    
    # 按胜率排序
    best_win = max(valid, key=lambda x: x['win_rate'])
    print(f"\n🥈 最高胜率策略: {best_win['name']}")
    print(f"   胜率: {best_win['win_rate']:.1%}")
    print(f"   平均收益: {best_win['avg_return']:.2f}%")
    
    # 综合评分 (收益*胜率)
    best_score = max(valid, key=lambda x: x['avg_return'] * x['win_rate'])
    print(f"\n🥉 综合最优策略: {best_score['name']}")
    print(f"   综合评分: {best_score['avg_return'] * best_score['win_rate']:.2f}")
    print(f"   平均收益: {best_score['avg_return']:.2f}%")
    print(f"   胜率: {best_score['win_rate']:.1%}")
else:
    print("\n⚠️ 无有效策略 (平均收益>0 且 胜率>50%)")

# 保存完整结果
result_file = os.path.join(MODEL_DIR, 'strategy_search_v2_results.json')
with open(result_file, 'w') as f:
    json.dump({
        'strategies': results,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'recommendation': {
            'best_return': best_return['name'] if valid else None,
            'best_win_rate': best_win['name'] if valid else None,
            'best_overall': best_score['name'] if valid else None,
        }
    }, f, indent=2, ensure_ascii=False)

print(f"\n✅ 结果保存: {result_file}")
print(f"\n完成时间: {datetime.now()}")