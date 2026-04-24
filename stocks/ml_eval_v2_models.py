#!/usr/bin/env python3
"""快速评估已生成的V2模型"""
import os
import pickle
import json
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, precision_score
from datetime import datetime

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 加载测试数据
print("加载测试数据...")
test_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_8.csv"))
print(f"测试样本: {len(test_df)}")

# 模型列表
model_files = [f for f in os.listdir(MODEL_DIR) if f.startswith("ml_v2_") and f.endswith(".pkl")]
print(f"找到模型: {len(model_files)}")

results = []

for model_file in sorted(model_files):
    name = model_file.replace("ml_v2_", "").replace(".pkl", "")
    
    print(f"\n评估: {name}")
    
    try:
        with open(os.path.join(MODEL_DIR, model_file), 'rb') as f:
            data = pickle.load(f)
        
        model = data['model']
        scaler = data['scaler']
        features = data['features']
        strategy = data['strategy']
        forward = strategy['forward']
        profit = strategy['profit']
        
        # 计算label
        test_df['future_ret'] = test_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
        test_df['label'] = (test_df['future_ret'] > profit).astype(int)
        
        test_valid = test_df[:-forward].copy()
        pos_ratio = test_valid['label'].mean()
        
        # 预测
        X = test_valid[features].fillna(0).values.astype(np.float32)
        X_scaled = scaler.transform(X)
        y_prob = model.predict_proba(X_scaled)[:, 1]
        y_true = test_valid['label'].values
        
        # AUC
        try:
            auc = roc_auc_score(y_true, y_prob)
        except:
            auc = 0.5
        
        # 最佳阈值
        best_prec = 0
        best_thresh = 0
        for thresh in [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]:
            y_pred = (y_prob >= thresh).astype(int)
            if y_pred.sum() > 0 and y_pred.sum() < len(y_pred):
                prec = precision_score(y_true, y_pred, zero_division=0)
                if prec > best_prec:
                    best_prec = prec
                    best_thresh = thresh
        
        # 收益统计
        selected_idx = y_prob >= best_thresh
        if selected_idx.sum() > 10:
            avg_ret = test_valid.loc[selected_idx, 'future_ret'].mean()
            win_rate = (test_valid.loc[selected_idx, 'future_ret'] > 0).mean()
        else:
            avg_ret = 0
            win_rate = 0
        
        print(f"  AUC: {auc:.4f} | 精确率: {best_prec:.2%} | 平均收益: {avg_ret*100:.2f}% | 胜率: {win_rate:.1%}")
        
        results.append({
            'name': name,
            'forward_days': forward,
            'profit_pct': profit * 100,
            'pos_ratio': pos_ratio * 100,
            'auc': auc,
            'best_threshold': best_thresh,
            'best_precision': best_prec,
            'avg_return': avg_ret * 100,
            'win_rate': win_rate,
            'selected_count': int(selected_idx.sum()),
        })
        
    except Exception as e:
        print(f"  错误: {e}")

# 输出汇总
print("\n" + "="*80)
print("策略对比汇总")
print("="*80)

print("\n| 策略 | 周期 | 目标 | AUC | 精确率 | 平均收益 | 胜率 | 选股数 |")
print("|------|------|------|-----|--------|----------|------|--------|")

for r in sorted(results, key=lambda x: x['avg_return'], reverse=True):
    print(f"| {r['name']} | {r['forward_days']}天 | {r['profit_pct']:.0f}% | {r['auc']:.4f} | {r['best_precision']:.1%} | {r['avg_return']:.2f}% | {r['win_rate']:.1%} | {r['selected_count']} |")

# 推荐
valid = [r for r in results if r['avg_return'] > 0 and r['win_rate'] > 0.5]
if valid:
    best = max(valid, key=lambda x: x['avg_return'] * x['win_rate'])
    print(f"\n🏆 推荐策略: {best['name']}")
    print(f"   平均收益: {best['avg_return']:.2f}%")
    print(f"   胜率: {best['win_rate']:.1%}")
    print(f"   精确率: {best['best_precision']:.2%}")

# 保存结果
with open(os.path.join(MODEL_DIR, 'strategy_search_v2_results.json'), 'w') as f:
    json.dump({
        'strategies': results,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }, f, indent=2, ensure_ascii=False)

print(f"\n✅ 结果保存完成")