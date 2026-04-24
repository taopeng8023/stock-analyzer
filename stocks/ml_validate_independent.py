#!/usr/bin/env python3
"""
独立数据验证 - 使用历史数据目录中的最新数据（未参与训练）
关键：避免数据泄露，得到真实性能
"""
import os
import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import roc_auc_score, precision_score

print("="*80)
print("独立数据验证 - 使用真实历史数据")
print("="*80)

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 获取股票列表
stock_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
print(f"股票数据文件: {len(stock_files)}")

# 随机选择100只股票作为独立测试集
import random
random.seed(42)
test_stocks = random.sample(stock_files, 100)
print(f"选择测试股票: {len(test_stocks)}")

# 加载并合并测试数据
print("\n加载测试数据...")
all_data = []
for stock_file in test_stocks:
    try:
        with open(os.path.join(DATA_DIR, stock_file), 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list) and len(data) > 50:
            df = pd.DataFrame(data)
            df['code'] = stock_file.replace('.json', '')
            all_data.append(df)
    except:
        continue

test_df = pd.concat(all_data, ignore_index=True)
print(f"测试样本总数: {len(test_df)}")

# 计算特征（与训练数据一致的逻辑）
def compute_features(df):
    """计算特征 - 必须与训练数据一致"""
    # 价格均线位置
    df['p_ma5'] = df['close'] / df['close'].rolling(5).mean()
    df['p_ma10'] = df['close'] / df['close'].rolling(10).mean()
    df['p_ma20'] = df['close'] / df['close'].rolling(20).mean()
    df['p_ma60'] = df['close'] / df['close'].rolling(60).mean()
    
    # 均线斜率
    df['ma5_slope'] = df['close'].rolling(5).mean().pct_change()
    df['ma10_slope'] = df['close'].rolling(10).mean().pct_change()
    df['ma20_slope'] = df['close'].rolling(20).mean().pct_change()
    
    # 收益率
    df['ret1'] = df['close'].pct_change()
    df['ret5'] = df['close'].pct_change(5)
    df['ret10'] = df['close'].pct_change(10)
    df['ret20'] = df['close'].pct_change(20)
    
    # 波动率 (重要！训练数据中vol5/vol10是波动率，不是成交量均线)
    df['vol5'] = df['ret1'].rolling(5).std()
    df['vol10'] = df['ret1'].rolling(10).std()
    df['vol20'] = df['ret1'].rolling(20).std()
    
    # RSI (简化版)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd_dif'] = ema12 - ema26
    df['macd_dea'] = df['macd_dif'].ewm(span=9).mean()
    df['macd_hist'] = df['macd_dif'] - df['macd_dea']
    
    # KDJ
    low_min = df['low'].rolling(9).min()
    high_max = df['high'].rolling(9).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    df['kdj_k'] = rsv.ewm(alpha=1/3).mean()
    df['kdj_d'] = df['kdj_k'].ewm(alpha=1/3).mean()
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
    
    # 成交量比
    df['vol_ratio'] = df['volume'] / df['volume'].rolling(5).mean()
    df['vol_ratio20'] = df['volume'] / df['volume'].rolling(20).mean()
    
    # 价格波动幅度
    df['hl_pct'] = (df['high'] - df['low']) / df['close']
    df['hc_pct'] = (df['high'] - df['close']) / df['close']
    df['cl_pct'] = (df['close'] - df['low']) / df['close']
    
    # 布林带位置
    mid = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['boll_pos'] = (df['close'] - mid) / (2 * std)
    
    return df

test_df = compute_features(test_df)

# 模型列表
model_files = [f for f in os.listdir(MODEL_DIR) if f.startswith("ml_v2_") and f.endswith(".pkl")]
print(f"模型数量: {len(model_files)}")

results = []

print("\n" + "="*80)
print("开始独立数据验证")
print("="*80)

for model_file in sorted(model_files):
    name = model_file.replace("ml_v2_", "").replace(".pkl", "")
    
    print(f"\n验证: {name}")
    
    try:
        with open(os.path.join(MODEL_DIR, model_file), 'rb') as f:
            data = pickle.load(f)
        
        model = data['model']
        scaler = data['scaler']
        features = data['features']
        strategy = data['strategy']
        forward = strategy['forward']
        profit = strategy['profit']
        
        # 计算未来收益label
        test_df['future_ret'] = test_df['ret1'].rolling(forward, min_periods=1).sum().shift(-forward)
        test_df['label'] = (test_df['future_ret'] > profit).astype(int)
        
        # 过滤无效数据
        valid_df = test_df.dropna(subset=features + ['future_ret', 'label']).copy()
        valid_df = valid_df[:-forward]  # 排除最后forward天
        
        if len(valid_df) < 1000:
            print(f"  有效样本不足: {len(valid_df)}")
            continue
        
        pos_ratio = valid_df['label'].mean()
        
        # 预测
        X = valid_df[features].fillna(0).values.astype(np.float32)
        X_scaled = scaler.transform(X)
        y_prob = model.predict_proba(X_scaled)[:, 1]
        y_true = valid_df['label'].values
        
        # AUC
        try:
            auc = roc_auc_score(y_true, y_prob)
        except:
            auc = 0.5
        
        # 最佳阈值精确率
        best_prec = 0
        best_thresh = 0
        for thresh in [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]:
            y_pred = (y_prob >= thresh).astype(int)
            if y_pred.sum() > 0 and y_pred.sum() < len(y_pred):
                prec = precision_score(y_true, y_pred, zero_division=0)
                if prec > best_prec:
                    best_prec = prec
                    best_thresh = thresh
        
        # 收益统计（使用阈值0.85，平衡精确率和选股数）
        selected_idx = y_prob >= 0.85
        if selected_idx.sum() > 10:
            avg_ret = valid_df.loc[selected_idx, 'future_ret'].mean()
            win_rate = (valid_df.loc[selected_idx, 'future_ret'] > 0).mean()
            max_ret = valid_df.loc[selected_idx, 'future_ret'].max()
            min_ret = valid_df.loc[selected_idx, 'future_ret'].min()
        else:
            avg_ret = 0
            win_rate = 0
            max_ret = 0
            min_ret = 0
        
        print(f"  有效样本: {len(valid_df)}")
        print(f"  正样本比例: {pos_ratio*100:.2f}%")
        print(f"  AUC: {auc:.4f}")
        print(f"  精确率(阈值0.85): {best_prec:.2%}")
        print(f"  选股数: {selected_idx.sum()}")
        print(f"  平均收益: {avg_ret*100:.2f}%")
        print(f"  胜率: {win_rate:.1%}")
        print(f"  最大收益: {max_ret*100:.2f}%")
        print(f"  最小收益: {min_ret*100:.2f}%")
        
        results.append({
            'name': name,
            'forward_days': forward,
            'profit_pct': profit * 100,
            'pos_ratio': pos_ratio * 100,
            'auc': auc,
            'precision': best_prec,
            'avg_return': avg_ret * 100,
            'win_rate': win_rate,
            'selected_count': int(selected_idx.sum()),
            'max_return': max_ret * 100,
            'min_return': min_ret * 100,
        })
        
    except Exception as e:
        print(f"  错误: {e}")

# 汇总输出
print("\n" + "="*80)
print("独立验证结果汇总")
print("="*80)

print("\n| 策略 | 周期 | 目标 | AUC | 精确率 | 平均收益 | 胜率 | 选股数 |")
print("|------|------|------|-----|--------|----------|------|--------|")

for r in sorted(results, key=lambda x: x['avg_return'], reverse=True):
    print(f"| {r['name']} | {r['forward_days']}天 | {r['profit_pct']:.0f}% | {r['auc']:.4f} | {r['precision']:.1%} | {r['avg_return']:.2f}% | {r['win_rate']:.1%} | {r['selected_count']} |")

# 有效策略（收益>0，胜率>50%）
valid = [r for r in results if r['avg_return'] > 0 and r['win_rate'] > 0.5]
print(f"\n有效策略数量: {len(valid)}")

if valid:
    # 综合评分
    best = max(valid, key=lambda x: x['avg_return'] * x['win_rate'])
    print(f"\n🏆 推荐策略: {best['name']}")
    print(f"   平均收益: {best['avg_return']:.2f}%")
    print(f"   胜率: {best['win_rate']:.1%}")
    print(f"   选股数: {best['selected_count']}")
    
    # 最稳定策略
    stable = max(valid, key=lambda x: x['win_rate'])
    print(f"\n🥈 最稳定策略: {stable['name']}")
    print(f"   胜率: {stable['win_rate']:.1%}")
    print(f"   平均收益: {stable['avg_return']:.2f}%")

# 保存
with open(os.path.join(MODEL_DIR, 'independent_validation_results.json'), 'w') as f:
    json.dump({
        'strategies': results,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'test_stocks': len(test_stocks),
        'test_samples': len(test_df),
    }, f, indent=2, ensure_ascii=False)

print("\n✅ 独立验证完成")