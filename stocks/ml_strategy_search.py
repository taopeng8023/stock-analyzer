#!/usr/bin/env python3
"""
多策略搜索训练 - 找到最优上涨预测策略
测试不同预测周期和收益阈值组合
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
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("多策略搜索训练 - 找到最优上涨策略")
print("="*80)
print(datetime.now())

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 策略配置：不同周期+阈值组合
STRATEGIES = [
    {"name": "短快_3天2%", "forward": 3, "profit": 0.02},
    {"name": "短快_3天3%", "forward": 3, "profit": 0.03},
    {"name": "标准_5天2%", "forward": 5, "profit": 0.02},
    {"name": "标准_5天3%", "forward": 5, "profit": 0.03},
    {"name": "标准_5天5%", "forward": 5, "profit": 0.05},
    {"name": "中稳_10天3%", "forward": 10, "profit": 0.03},
    {"name": "中稳_10天5%", "forward": 10, "profit": 0.05},
    {"name": "中稳_10天8%", "forward": 10, "profit": 0.08},
    {"name": "长期_15天5%", "forward": 15, "profit": 0.05},
    {"name": "长期_15天10%", "forward": 15, "profit": 0.10},
]

# 特征列表
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

def compute_future_label(df, forward_days, profit_pct):
    """重新计算label：未来N天收益超过阈值"""
    df['future_ret'] = df['close'].shift(-forward_days) / df['close'] - 1
    df['future_ret_pct'] = df['future_ret'] * 100
    df['label_new'] = (df['future_ret'] > profit_pct).astype(int)
    return df

def load_batch_data(batch_file, forward_days, profit_pct):
    """加载批次数据并重新计算label"""
    df = pd.read_csv(batch_file)
    
    # 原始数据没有close，但有ret1可以推断
    # 使用模拟方法：假设基准价格1，根据收益率推算
    # 但实际上我们需要原始close数据
    
    # 方案：使用已有的ret数据近似
    # future_ret ≈ sum of ret1 for next forward_days
    df['future_ret'] = df['ret1'].rolling(forward_days).sum().shift(-forward_days)
    df['label_new'] = (df['future_ret'] > profit_pct).astype(int)
    
    return df

# 加载所有数据
print("\n加载全量训练数据...")
all_data = []
for batch_file in os.listdir(TEMP_DIR):
    if not batch_file.endswith('.csv'):
        continue
    
    df = pd.read_csv(os.path.join(TEMP_DIR, batch_file))
    all_data.append(df)
    print(f"  {batch_file}: {len(df)}条")

df_all = pd.concat(all_data, ignore_index=True)
print(f"\n总样本: {len(df_all)}")

# 检查数据完整性
print(f"\n特征完整性检查:")
for f in FEATURES:
    missing = df_all[f].isna().sum()
    print(f"  {f}: missing {missing} ({missing/len(df_all)*100:.2f}%)")

# 填充缺失值
df_all = df_all.fillna(0)

# 存储策略结果
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
    
    # 重新计算label
    # 使用ret1累计作为未来收益近似
    df_all['future_ret_approx'] = df_all['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
    df_all['label_strategy'] = (df_all['future_ret_approx'] > profit).astype(int)
    
    # 排除最后forward天的数据(没有未来收益)
    df_valid = df_all[:-forward].copy()
    
    X = df_valid[FEATURES].values.astype(np.float32)
    y = df_valid['label_strategy'].values
    
    # 统计正样本比例
    pos_ratio = y.mean()
    print(f"\n正样本比例: {pos_ratio*100:.2f}%")
    print(f"有效样本: {len(y)}")
    
    if pos_ratio < 0.05 or pos_ratio > 0.50:
        print(f"⚠️ 正样本比例异常，跳过")
        continue
    
    # 划分训练测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"训练集: {len(X_train)} | 测试集: {len(X_test)}")
    
    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 训练模型
    print("\n训练神经网络...")
    start_time = time.time()
    
    model = MLPClassifier(
        hidden_layer_sizes=(512, 256, 128),
        activation='relu',
        solver='adam',
        learning_rate_init=0.002,
        alpha=0.01,
        batch_size=256,
        max_iter=100,
        early_stopping=True,
        validation_fraction=0.1,
        random_state=42,
    )
    
    model.fit(X_train_scaled, y_train)
    
    elapsed = time.time() - start_time
    print(f"训练耗时: {elapsed:.0f}s")
    
    # 评估
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = model.predict(X_test_scaled)
    
    auc = roc_auc_score(y_test, y_prob)
    acc = accuracy_score(y_test, y_pred)
    
    # 计算不同阈值下的精确率
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9]
    precisions = {}
    
    for thresh in thresholds:
        y_pred_thresh = (y_prob >= thresh).astype(int)
        if y_pred_thresh.sum() > 0:
            prec = precision_score(y_test, y_pred_thresh)
            precisions[thresh] = prec
            count = y_pred_thresh.sum()
            print(f"  阈值{thresh}: 精确率{prec:.2%} 预测{count}只")
    
    # 找最佳阈值
    best_thresh = max(precisions.keys(), key=lambda k: precisions[k])
    best_prec = precisions[best_thresh]
    
    print(f"\n性能:")
    print(f"  AUC: {auc:.4f}")
    print(f"  准确率: {acc:.2%}")
    print(f"  最佳阈值: {best_thresh} (精确率{best_prec:.2%})")
    
    # 保存结果
    strategy_results.append({
        'name': name,
        'forward_days': forward,
        'profit_pct': profit * 100,
        'pos_ratio': pos_ratio * 100,
        'auc': auc,
        'accuracy': acc,
        'best_threshold': best_thresh,
        'best_precision': best_prec,
        'precisions': precisions,
        'train_time': elapsed,
    })
    
    # 保存模型
    model_file = os.path.join(MODEL_DIR, f"ml_strategy_{name.replace('%', 'pct')}.pkl")
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': FEATURES,
            'strategy': strategy,
            'performance': {
                'auc': auc,
                'precision': best_prec,
            }
        }, f)
    
    print(f"✅ 模型保存: {model_file}")
    
    # 清理内存
    del model, scaler, X_train_scaled, X_test_scaled
    gc.collect()

# 输出对比结果
print("\n" + "="*80)
print("策略对比汇总")
print("="*80)
print("\n| 策略 | 预测周期 | 目标涨幅 | 正样本% | AUC | 最佳阈值 | 精确率 |")
print("|------|---------|---------|--------|-----|---------|--------|")

for r in strategy_results:
    print(f"| {r['name']} | {r['forward_days']}天 | {r['profit_pct']}% | {r['pos_ratio']:.1f}% | {r['auc']:.4f} | {r['best_threshold']} | {r['best_precision']:.2%} |")

# 找最优策略
best_strategy = max(strategy_results, key=lambda r: r['auc'])
print(f"\n🏆 最优策略: {best_strategy['name']}")
print(f"   AUC: {best_strategy['auc']:.4f}")
print(f"   精确率: {best_strategy['best_precision']:.2%} @ 阈值{best_strategy['best_threshold']}")

# 保存结果汇总
results_file = os.path.join(MODEL_DIR, 'strategy_comparison_20260414.json')
with open(results_file, 'w') as f:
    json.dump({
        'strategies': strategy_results,
        'best_strategy': best_strategy,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, f, indent=2)

print(f"\n✅ 结果保存: {results_file}")
print("="*80)
print("完成:", datetime.now())