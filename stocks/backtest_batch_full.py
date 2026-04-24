#!/usr/bin/env python3
"""
分批全量回测 - 优化版
目标：稳定完成5503只股票的回测验证

策略：
1. 分批处理（每批500股）
2. 降低处理复杂度
3. 增加进度输出
4. 保存中间结果
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
print("分批全量回测 - 优化版")
print("="*80)
print(f"开始时间: {datetime.now()}")

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 最优模型
MODELS = [
    ("ml_v6_中长_7天10pct.pkl", "V6_中长_7天10%", 7, 0.10),
    ("ml_v6_长期_10天10pct.pkl", "V6_长期_10天10%", 10, 0.10),
]

def compute_features(df):
    """特征计算 - 与训练数据一致"""
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

# 获取股票列表
stock_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.json')])
total_stocks = len(stock_files)
print(f"股票总数: {total_stocks}")

results_all = {}

for model_file, model_name, forward, profit in MODELS:
    print(f"\n{'='*60}")
    print(f"模型: {model_name}")
    print(f"{'='*60}")
    
    model_path = os.path.join(MODEL_DIR, model_file)
    with open(model_path, 'rb') as f:
        data = pickle.load(f)
    
    model = data['model']
    scaler = data['scaler']
    features = data['features']
    threshold = data['metrics'].get('threshold', 0.9)
    
    print(f"阈值: {threshold}")
    
    all_trades = []
    batch_size = 500
    total_batches = total_stocks // batch_size + 1
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, total_stocks)
        batch_files = stock_files[start_idx:end_idx]
        
        print(f"\n批次 {batch_idx+1}/{total_batches} ({start_idx}-{end_idx})")
        
        batch_trades = 0
        
        for i, stock_file in enumerate(batch_files):
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
                            all_trades.append({
                                'code': code,
                                'date': row['trade_date'].strftime('%Y%m%d'),
                                'profit': profit_pct,
                                'prob': row['prob'],
                            })
                            batch_trades += 1
            
            except Exception as e:
                continue
        
        print(f"  本批交易: {batch_trades}笔")
        print(f"  累计交易: {len(all_trades)}笔")
        
        # 每批保存中间结果
        if len(all_trades) > 0 and batch_idx % 2 == 0:
            trades_df = pd.DataFrame(all_trades)
            trades_df.to_csv(os.path.join(MODEL_DIR, f"backtest_progress_{model_name.replace('%','pct')}.csv"), index=False)
    
    # 统计最终结果
    if all_trades:
        profits = [t['profit'] for t in all_trades]
        wins = sum(1 for p in profits if p > 0)
        
        avg_profit = np.mean(profits)
        median_profit = np.median(profits)
        win_rate = wins / len(profits)
        
        # 最大回撤
        cum_profits = []
        cum = 0
        for p in profits:
            cum += p
            cum_profits.append(cum)
        
        peak = 0
        max_dd = 0
        for cp in cum_profits:
            peak = max(peak, cp)
            dd = peak - cp
            max_dd = max(max_dd, dd)
        
        print(f"\n✅ 全量回测结果:")
        print(f"  总交易: {len(all_trades)}笔")
        print(f"  覆盖股票: {len(set(t['code'] for t in all_trades))}只")
        print(f"  胜率: {win_rate:.1%}")
        print(f"  平均收益: {avg_profit*100:.2f}%")
        print(f"  收益中位数: {median_profit*100:.2f}%")
        print(f"  最大盈利: {max(profits)*100:.2f}%")
        print(f"  最大亏损: {min(profits)*100:.2f}%")
        print(f"  最大回撤: {max_dd*100:.2f}%")
        
        results_all[model_name] = {
            'trades': len(all_trades),
            'stocks': len(set(t['code'] for t in all_trades)),
            'win_rate': win_rate,
            'avg_profit': avg_profit * 100,
            'median_profit': median_profit * 100,
            'max_win': max(profits) * 100,
            'max_loss': min(profits) * 100,
            'max_drawdown': max_dd * 100,
        }
        
        # 保存最终结果
        trades_df = pd.DataFrame(all_trades)
        trades_df.to_csv(os.path.join(MODEL_DIR, f"backtest_full_{model_name.replace('%','pct')}.csv"), index=False)

# 汇总对比
print("\n" + "="*80)
print("全量回测汇总")
print("="*80)

if results_all:
    print("\n| 模型 | 交易数 | 覆盖股票 | 胜率 | 平均收益 | 中位数 | 最大回撤 |")
    print("|------|--------|----------|------|----------|--------|----------|")
    
    for name, r in sorted(results_all.items(), key=lambda x: x[1]['avg_profit'], reverse=True):
        print(f"| {name} | {r['trades']} | {r['stocks']} | {r['win_rate']:.1%} | {r['avg_profit']:.2f}% | {r['median_profit']:.2f}% | {r['max_drawdown']:.2f}% |")
    
    # 对比100股样本
    print("\n📊 对比100股样本回测:")
    sample_map = {
        'V6_中长_7天10%': 39.47,
        'V6_长期_10天10%': 37.33,
    }
    
    for name, r in results_all.items():
        sample = sample_map.get(name, 0)
        if sample > 0:
            diff = r['avg_profit'] - sample
            status = "✅" if abs(diff) < 10 else "⚠️"
            print(f"  {name}: {status} 全量{r['avg_profit']:.2f}% vs 样本{sample:.2f}%")

print(f"\n完成时间: {datetime.now()}")