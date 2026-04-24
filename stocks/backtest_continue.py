#!/usr/bin/env python3
"""
全量回测续传 - 处理剩余股票
从上次中断点继续，避免重复处理
"""
import os
import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("全量回测续传 - 处理剩余5025股")
print("="*80)
print(f"开始时间: {datetime.now()}")

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 加载已处理结果
progress_file = os.path.join(MODEL_DIR, "backtest_progress_V6_中长_7天10pct.csv")
existing_df = pd.read_csv(progress_file)
codes_done = set(existing_df['code'].values)
print(f"已处理: {len(codes_done)}只")

# 加载模型
model_file = "ml_v6_中长_7天10pct.pkl"
with open(os.path.join(MODEL_DIR, model_file), 'rb') as f:
    data = pickle.load(f)

model = data['model']
scaler = data['scaler']
features = data['features']
threshold = data['metrics'].get('threshold', 0.9)
forward = 7

print(f"阈值: {threshold}")

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

# 获取所有股票文件
stock_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.json')])
print(f"总股票数: {len(stock_files)}")

# 过滤已处理的
remaining_files = [f for f in stock_files if f.replace('.json', '') not in codes_done]
print(f"剩余股票: {len(remaining_files)}")

# 分批处理
batch_size = 200  # 更小批次，更稳定
total_batches = len(remaining_files) // batch_size + 1

new_trades = []

for batch_idx in range(total_batches):
    start_idx = batch_idx * batch_size
    end_idx = min(start_idx + batch_size, len(remaining_files))
    batch = remaining_files[start_idx:end_idx]
    
    print(f"\n批次 {batch_idx+1}/{total_batches} ({len(batch)}股)")
    
    batch_trades = 0
    
    for stock_file in batch:
        code = stock_file.replace('.json', '')
        
        try:
            with open(os.path.join(DATA_DIR, stock_file), 'r') as f:
                stock_data = json.load(f)
            
            if 'items' not in stock_data or len(stock_data['items']) < 80:
                continue
            
            df = pd.DataFrame(stock_data['items'], columns=stock_data['fields'])
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            df = compute_features(df)
            valid_df = df.dropna(subset=features)
            
            if len(valid_df) < forward + 30:
                continue
            
            X = valid_df[features].fillna(0).values.astype(np.float32)
            X_scaled = scaler.transform(X)
            y_prob = model.predict_proba(X_scaled)[:, 1]
            
            valid_df['prob'] = y_prob
            
            for j in range(len(valid_df) - forward - 1):
                row = valid_df.iloc[j]
                if row['prob'] >= threshold:
                    sell_idx = j + forward
                    if sell_idx < len(valid_df):
                        profit_pct = (valid_df.iloc[sell_idx]['close'] / row['close'] - 1)
                        new_trades.append({
                            'code': code,
                            'date': row['trade_date'].strftime('%Y%m%d'),
                            'profit': profit_pct,
                            'prob': row['prob'],
                        })
                        batch_trades += 1
        
        except Exception as e:
            continue
    
    print(f"  本批交易: {batch_trades}笔")
    
    # 每批保存进度
    if len(new_trades) > 0:
        all_trades = existing_df.to_dict('records') + new_trades
        progress_df = pd.DataFrame(all_trades)
        progress_df.to_csv(progress_file, index=False)
        print(f"  累计交易: {len(all_trades)}笔")

# 合并最终结果
print("\n合并最终结果...")
all_trades = existing_df.to_dict('records') + new_trades
final_df = pd.DataFrame(all_trades)
final_df.to_csv(os.path.join(MODEL_DIR, "backtest_full_V6_中长_7天10pct.csv"), index=False)

# 统计
profits = [t['profit'] for t in all_trades]
wins = sum(1 for p in profits if p > 0)
avg = np.mean(profits)
median = np.median(profits)
wr = wins / len(profits)

print(f"\n✅ 全量回测最终结果:")
print(f"  总交易: {len(all_trades)}笔")
print(f"  覆盖股票: {len(set(t['code'] for t in all_trades))}只")
print(f"  胜率: {wr:.1%}")
print(f"  平均收益: {avg*100:.2f}%")
print(f"  收益中位数: {median*100:.2f}%")

print(f"\n完成时间: {datetime.now()}")