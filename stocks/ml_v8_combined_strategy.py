#!/usr/bin/env python3
"""
V8 组合策略 - 多模型投票
目标：融合多个模型的预测，提升稳定性

策略：
1. 加载V5/V6/V7多个模型
2. 每个模型独立预测
3. 多模型投票（置信度加权）
4. 验证组合效果
"""
import os
import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import roc_auc_score, precision_score
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("V8 组合策略 - 多模型投票")
print("="*80)
print(f"开始时间: {datetime.now()}")

TEMP_DIR = "temp_data"
MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 加载多个模型（相同forward周期）
MODELS = [
    ("ml_v6_中长_7天10pct.pkl", 0.9),  # V6
    ("V7_中长_7天10pct.pkl", 0.8),     # V7 (注意文件名)
]

forward = 7
profit = 0.10

# 特征计算
def compute_features(df):
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    df['p_ma5'] = (df['close'] - df['ma5']) / df['ma5']
    df['p_ma10'] = (df['close'] - df['ma10']) / df['ma10']
    df['p_ma20'] = (df['close'] - df['ma20']) / df['ma20']
    df['p_ma60'] = (df['close'] - df['ma60']) / df['ma60']
    
    df['ma5_slope'] = df['ma5'] / df['ma5'].shift(5) - 1
    df['ma10_slope'] = df['ma10'] / df['ma10'].shift(10) - 1
    df['ma20_slope'] = df['ma20'] / df['ma20'].shift(20) - 1
    
    df['ret1'] = df['close'].pct_change()
    df['ret5'] = df['close'].pct_change(5)
    df['ret10'] = df['close'].pct_change(10)
    df['ret20'] = df['close'].pct_change(20)
    
    df['vol5'] = df['ret1'].rolling(5).std()
    df['vol10'] = df['ret1'].rolling(10).std()
    df['vol20'] = df['ret1'].rolling(20).std()
    
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd_dif'] = ema12 - ema26
    df['macd_dea'] = df['macd_dif'].ewm(span=9).mean()
    df['macd_hist'] = df['macd_dif'] - df['macd_dea']
    
    low_min = df['low'].rolling(9).min()
    high_max = df['high'].rolling(9).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    df['kdj_k'] = rsv.ewm(alpha=1/3).mean()
    df['kdj_d'] = df['kdj_k'].ewm(alpha=1/3).mean()
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
    
    df['vol_ratio'] = df['vol'] / df['vol'].rolling(5).mean()
    df['vol_ratio20'] = df['vol'] / df['vol'].rolling(20).mean()
    
    df['hl_pct'] = (df['high'] - df['low']) / df['close']
    df['hc_pct'] = (df['high'] - df['close']) / df['close']
    df['cl_pct'] = (df['close'] - df['low']) / df['close']
    
    mid = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['boll_pos'] = (df['close'] - mid) / (2 * std)
    
    return df

# 加载模型
print("\n加载模型...")
models_loaded = []

for model_file, thresh in MODELS:
    path = os.path.join(MODEL_DIR, model_file)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            data = pickle.load(f)
        models_loaded.append({
            'name': model_file,
            'model': data['model'],
            'scaler': data['scaler'],
            'features': data['features'],
            'threshold': thresh,
        })
        print(f"  ✅ {model_file}")
    else:
        print(f"  ⚠️ {model_file} 不存在")

print(f"\n加载模型: {len(models_loaded)}个")

# 测试组合策略
print("\n测试组合策略...")

# 加载测试股票
stock_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
print(f"股票数据: {len(stock_files)}")

import random
random.seed(42)
test_stocks = random.sample(stock_files, 150)
print(f"测试股票: {len(test_stocks)}")

trades = []
cumulative = 0

for stock_file in test_stocks:
    try:
        with open(os.path.join(DATA_DIR, stock_file), 'r') as f:
            data = json.load(f)
        
        if 'items' not in data or len(data['items']) < 100:
            continue
        
        df = pd.DataFrame(data['items'], columns=data['fields'])
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        df = compute_features(df)
        
        for m in models_loaded:
            valid_df = df.dropna(subset=m['features']).copy()
            
            if len(valid_df) < forward + 30:
                continue
            
            X = valid_df[m['features']].fillna(0).values.astype(np.float32)
            X_scaled = m['scaler'].transform(X)
            prob = m['model'].predict_proba(X_scaled)[:, 1]
            
            valid_df[f'prob_{m["name"]}'] = prob
        
        # 组合预测（平均置信度）
        prob_cols = [f'prob_{m["name"]}' for m in models_loaded]
        if prob_cols and all(c in df.columns for c in prob_cols):
            df['prob_avg'] = df[prob_cols].mean(axis=1)
            
            # 组合阈值（降低）
            combined_thresh = 0.5  # 降低组合阈值
            
            for i in range(len(df) - forward - 1):
                row = df.iloc[i]
                
                if row['prob_avg'] >= combined_thresh:
                    # 检查各模型一致性
                    votes = sum(1 for m in models_loaded if row[f'prob_{m["name"]}'] >= m['threshold'])
                    
                    if votes >= len(models_loaded) * 0.5:  # 至少半数同意
                        buy_price = row['close']
                        sell_idx = i + forward
                        
                        if sell_idx < len(df):
                            sell_price = df.iloc[sell_idx]['close']
                            profit_pct = (sell_price / buy_price - 1)
                            
                            trades.append({
                                'stock': stock_file.replace('.json', ''),
                                'buy_date': row['trade_date'],
                                'profit_pct': profit_pct,
                                'prob_avg': row['prob_avg'],
                                'votes': votes,
                                'win': profit_pct > 0,
                            })
                            cumulative += profit_pct
    
    except Exception as e:
        continue

if trades:
    profits = [t['profit_pct'] for t in trades]
    wins = sum(1 for t in trades if t['win'])
    
    avg_profit = np.mean(profits)
    median_profit = np.median(profits)
    win_rate = wins / len(trades)
    
    print(f"\n✅ 组合策略结果:")
    print(f"  交易次数: {len(trades)}")
    print(f"  胜率: {win_rate:.1%}")
    print(f"  平均收益: {avg_profit*100:.2f}%")
    print(f"  收益中位数: {median_profit*100:.2f}%")
    
    # 按投票数分析
    print(f"\n按投票数分析:")
    for v in sorted(set(t['votes'] for t in trades)):
        v_trades = [t for t in trades if t['votes'] == v]
        if v_trades:
            v_avg = np.mean([t['profit_pct'] for t in v_trades])
            v_wr = sum(1 for t in v_trades if t['win']) / len(v_trades)
            print(f"  {v}票同意: {len(v_trades)}笔, 收益{v_avg*100:.2f}%, 胜率{v_wr:.1%}")
    
    # 对比单模型
    print(f"\n📊 对比单模型 (V6回测39.47%)")
    diff = avg_profit * 100 - 39.47
    if diff > 0:
        print(f"✅ 组合策略提升 {diff:.2f}%")
    else:
        print(f"⚠️ 组合策略下降 {-diff:.2f}%")
    
    # 保存
    trades_df = pd.DataFrame(trades)
    trades_df.to_csv(os.path.join(MODEL_DIR, "v8_combined_trades.csv"), index=False)
    
    result = {
        'name': 'V8_组合策略',
        'models': [m['name'] for m in models_loaded],
        'trades': len(trades),
        'win_rate': win_rate,
        'avg_profit': avg_profit * 100,
        'median_profit': median_profit * 100,
        'vs_v6': diff,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    with open(os.path.join(MODEL_DIR, 'v8_combined_result.json'), 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 结果保存")

else:
    print("\n⚠️ 无交易记录")

print(f"\n完成时间: {datetime.now()}")