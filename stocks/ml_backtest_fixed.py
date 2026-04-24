#!/usr/bin/env python3
"""
V6模型回测验证 - 修复版
关键修复：使用与temp_data生成时一致的特征计算逻辑

原始逻辑 (ml_main_quick.py):
- p_ma5 = (close - MA5) / MA5  ← 负值表示低于均线
- vol5 = ret1.rolling(5).std() ← 波动率
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
print("V6模型回测验证 - 修复版")
print("="*80)
print(f"开始时间: {datetime.now()}")

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 要回测的模型
MODELS = [
    ("ml_v6_中长_7天10pct.pkl", "V6_中长_7天10%", 7, 0.10),
    ("ml_v6_长期_10天10pct.pkl", "V6_长期_10天10%", 10, 0.10),
    ("ml_v5_标准_5天5pct.pkl", "V5_标准_5天5%", 5, 0.05),
    ("ml_v5_短攻_3天5pct.pkl", "V5_短攻_3天5%", 3, 0.05),
]

# 测试股票
stock_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
print(f"股票数据文件: {len(stock_files)}")

import random
random.seed(42)
test_stocks = random.sample(stock_files, 100)
print(f"测试股票: {len(test_stocks)}")

# 特征计算 - 与temp_data生成时一致
def compute_features_fixed(df):
    """
    特征计算 - 与ml_main_quick.py一致
    关键：p_ma5 = (close - MA5) / MA5，不是 close/MA5
    """
    # MA均线
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    # 价格相对均线位置 (关键修复！)
    df['p_ma5'] = (df['close'] - df['ma5']) / df['ma5']  # ← 原始逻辑
    df['p_ma10'] = (df['close'] - df['ma10']) / df['ma10']
    df['p_ma20'] = (df['close'] - df['ma20']) / df['ma20']
    df['p_ma60'] = (df['close'] - df['ma60']) / df['ma60']
    
    # 均线斜率
    df['ma5_slope'] = df['ma5'] / df['ma5'].shift(5) - 1
    df['ma10_slope'] = df['ma10'] / df['ma10'].shift(10) - 1
    df['ma20_slope'] = df['ma20'] / df['ma20'].shift(20) - 1
    
    # 收益率
    df['ret1'] = df['close'].pct_change()
    df['ret5'] = df['close'].pct_change(5)
    df['ret10'] = df['close'].pct_change(10)
    df['ret20'] = df['close'].pct_change(20)
    
    # 波动率 (不是成交量均线！)
    df['vol5'] = df['ret1'].rolling(5).std()
    df['vol10'] = df['ret1'].rolling(10).std()
    df['vol20'] = df['ret1'].rolling(20).std()
    
    # RSI
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
    df['vol_ratio'] = df['vol'] / df['vol'].rolling(5).mean()
    df['vol_ratio20'] = df['vol'] / df['vol'].rolling(20).mean()
    
    # 价格形态
    df['hl_pct'] = (df['high'] - df['low']) / df['close']
    df['hc_pct'] = (df['high'] - df['close']) / df['close']
    df['cl_pct'] = (df['close'] - df['low']) / df['close']
    
    # 布林带位置
    mid = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['boll_pos'] = (df['close'] - mid) / (2 * std)
    
    return df

results_all = []

for model_file, model_name, forward, profit_target in MODELS:
    print(f"\n{'='*60}")
    print(f"回测模型: {model_name}")
    print(f"周期: {forward}天")
    print(f"{'='*60}")
    
    model_path = os.path.join(MODEL_DIR, model_file)
    if not os.path.exists(model_path):
        print(f"⚠️ 模型不存在: {model_path}")
        continue
    
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data['model']
    scaler = model_data['scaler']
    features = model_data['features']
    metrics = model_data.get('metrics', {})
    threshold = metrics.get('threshold', 0.85)
    
    print(f"特征数: {len(features)}")
    print(f"验证阈值: {threshold}")
    
    trades = []
    cumulative_profit = 0
    
    for stock_file in test_stocks:
        try:
            with open(os.path.join(DATA_DIR, stock_file), 'r') as f:
                data = json.load(f)
            
            if 'items' not in data or len(data['items']) < 100:
                continue
            
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            # 使用修复后的特征计算
            df = compute_features_fixed(df)
            
            valid_df = df.dropna(subset=features).copy()
            
            if len(valid_df) < forward + 30:
                continue
            
            X = valid_df[features].fillna(0).values.astype(np.float32)
            X_scaled = scaler.transform(X)
            y_prob = model.predict_proba(X_scaled)[:, 1]
            
            valid_df['prob'] = y_prob
            
            # 检查置信度分布
            if len(trades) == 0:
                print(f"\n  置信度分布:")
                print(f"    最大: {y_prob.max():.3f}")
                print(f"    最小: {y_prob.min():.3f}")
                print(f"    中位数: {np.median(y_prob):.3f}")
                print(f"    >0.5数量: {(y_prob > 0.5).sum()}")
                print(f"    >0.7数量: {(y_prob > 0.7).sum()}")
            
            # 交易模拟
            for i in range(len(valid_df) - forward - 1):
                row = valid_df.iloc[i]
                
                if row['prob'] >= threshold:
                    buy_price = row['close']
                    
                    sell_idx = i + forward
                    if sell_idx < len(valid_df):
                        sell_price = valid_df.iloc[sell_idx]['close']
                        profit_pct = (sell_price / buy_price - 1)
                        
                        trades.append({
                            'stock': stock_file.replace('.json', ''),
                            'buy_date': row['trade_date'],
                            'profit_pct': profit_pct,
                            'prob': row['prob'],
                            'win': profit_pct > 0,
                        })
                        
                        cumulative_profit += profit_pct
        
        except Exception as e:
            continue
    
    if trades:
        avg_profit = cumulative_profit / len(trades)
        win_rate = sum(1 for t in trades if t['win']) / len(trades)
        profits = [t['profit_pct'] for t in trades]
        
        print(f"\n✅ 回测结果:")
        print(f"  交易次数: {len(trades)}")
        print(f"  胜率: {win_rate:.1%}")
        print(f"  平均收益: {avg_profit*100:.2f}%")
        print(f"  收益中位数: {np.median(profits)*100:.2f}%")
        
        results_all.append({
            'model': model_name,
            'forward': forward,
            'threshold': threshold,
            'trades': len(trades),
            'win_rate': win_rate,
            'avg_profit': avg_profit * 100,
            'median_profit': np.median(profits) * 100,
        })
        
        # 保存
        trades_df = pd.DataFrame(trades)
        trades_file = os.path.join(MODEL_DIR, f"backtest_fixed_{model_name.replace('%', 'pct')}.csv")
        trades_df.to_csv(trades_file, index=False)
        print(f"  交易记录: {trades_file}")
    else:
        print(f"\n⚠️ 无交易 (阈值={threshold}太高)")

# 汇总
print("\n" + "="*80)
print("回测对比汇总 (修复版)")
print("="*80)

if results_all:
    print("\n| 模型 | 周期 | 阈值 | 交易数 | 胜率 | 平均收益 | 中位数 |")
    print("|------|------|------|--------|------|----------|--------|")
    
    for r in sorted(results_all, key=lambda x: x['avg_profit'], reverse=True):
        print(f"| {r['model']} | {r['forward']}天 | {r['threshold']} | {r['trades']} | {r['win_rate']:.1%} | {r['avg_profit']:.2f}% | {r['median_profit']:.2f}% |")
    
    # 对比验证集
    print("\n📊 对比验证集 (batch_8):")
    validation_map = {
        'V6_中长_7天10%': 29.43,
        'V6_长期_10天10%': 24.79,
        'V5_标准_5天5%': 18.78,
        'V5_短攻_3天5%': 12.68,
    }
    
    for r in results_all:
        v = validation_map.get(r['model'], 0)
        if v > 0:
            diff = r['avg_profit'] - v
            status = "✅" if diff > -10 else "⚠️"
            print(f"  {r['model']}: {status} 回测{r['avg_profit']:.2f}% vs 验证{v:.2f}% (差{diff:.1f}%)")
else:
    print("\n⚠️ 无有效回测结果")

print(f"\n完成时间: {datetime.now()}")