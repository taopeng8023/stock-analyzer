#!/usr/bin/env python3
"""
全量回测 V2 - 优化版（减少处理时间）
策略：随机抽样500股 + 多线程处理
"""
import os
import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime
import random
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("全量回测 V2 - 优化版（500股抽样）")
print("="*80)
print(f"开始时间: {datetime.now()}")

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

MODELS = [
    ("ml_v6_中长_7天10pct.pkl", "V6_中长_7天10%", 7, 0.10),
    ("ml_v6_长期_10天10pct.pkl", "V6_长期_10天10%", 10, 0.10),
]

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

# 随机抽样500股
stock_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
random.seed(42)
test_stocks = random.sample(stock_files, 500)
print(f"测试股票: {len(test_stocks)}")

results_all = []

for model_file, model_name, forward, profit in MODELS:
    print(f"\n{'='*60}")
    print(f"模型: {model_name}")
    print(f"{'='*60}")
    
    path = os.path.join(MODEL_DIR, model_file)
    with open(path, 'rb') as f:
        data = pickle.load(f)
    
    model = data['model']
    scaler = data['scaler']
    features = data['features']
    threshold = data['metrics'].get('threshold', 0.9)
    
    print(f"阈值: {threshold}")
    
    trades = []
    processed = 0
    
    for stock_file in test_stocks:
        processed += 1
        if processed % 100 == 0:
            print(f"  进度: {processed}/{len(test_stocks)}")
        
        try:
            with open(os.path.join(DATA_DIR, stock_file), 'r') as f:
                data = json.load(f)
            
            if 'items' not in data or len(data['items']) < 80:
                continue
            
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            df = compute_features(df)
            valid_df = df.dropna(subset=features)
            
            if len(valid_df) < forward + 30:
                continue
            
            X = valid_df[features].fillna(0).values.astype(np.float32)
            X_scaled = scaler.transform(X)
            y_prob = model.predict_proba(X_scaled)[:, 1]
            
            # 首次打印置信度分布
            if processed == 1:
                print(f"\n  置信度分布:")
                print(f"    最大: {y_prob.max():.3f}")
                print(f"    最小: {y_prob.min():.3f}")
                print(f"    中位数: {np.median(y_prob):.3f}")
                print(f"    >{threshold}数量: {(y_prob >= threshold).sum()}")
            
            valid_df['prob'] = y_prob
            
            for i in range(len(valid_df) - forward - 1):
                row = valid_df.iloc[i]
                if row['prob'] >= threshold:
                    sell_idx = i + forward
                    if sell_idx < len(valid_df):
                        profit_pct = (valid_df.iloc[sell_idx]['close'] / row['close'] - 1)
                        trades.append({
                            'profit_pct': profit_pct,
                            'win': profit_pct > 0,
                        })
        
        except:
            continue
    
    if trades:
        profits = [t['profit_pct'] for t in trades]
        wins = sum(1 for t in trades if t['win'])
        
        avg = np.mean(profits)
        median = np.median(profits)
        win_rate = wins / len(trades)
        
        print(f"\n✅ 结果:")
        print(f"  交易: {len(trades)}笔")
        print(f"  胜率: {win_rate:.1%}")
        print(f"  平均收益: {avg*100:.2f}%")
        print(f"  中位数: {median*100:.2f}%")
        
        results_all.append({
            'model': model_name,
            'trades': len(trades),
            'win_rate': win_rate,
            'avg_profit': avg * 100,
            'median_profit': median * 100,
        })

# 汇总
print("\n" + "="*80)
print("全量回测汇总 (500股)")
print("="*80)

if results_all:
    print("\n| 模型 | 交易数 | 胜率 | 平均收益 | 中位数 |")
    for r in results_all:
        print(f"| {r['model']} | {r['trades']} | {r['win_rate']:.1%} | {r['avg_profit']:.2f}% | {r['median_profit']:.2f}% |")

print(f"\n完成时间: {datetime.now()}")