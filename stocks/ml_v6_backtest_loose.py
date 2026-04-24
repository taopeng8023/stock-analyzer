#!/usr/bin/env python3
"""
V6模型回测验证 - 降低阈值
使用历史数据模拟真实交易，验证实际收益

调整：
- 降低阈值 (0.5-0.7)
- 增加测试股票数量
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
print("V6模型回测验证 - 宽松阈值")
print("="*80)
print(f"开始时间: {datetime.now()}")

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 要回测的模型 (降低阈值)
MODELS = [
    ("ml_v6_超长_20天20pct.pkl", "V6_超长_20天20%", 20, 0.20, 0.50),
    ("ml_v6_超长_15天15pct.pkl", "V6_超长_15天15%", 15, 0.15, 0.50),
    ("ml_v6_中长_7天10pct.pkl", "V6_中长_7天10%", 7, 0.10, 0.50),
    ("ml_v6_长期_10天10pct.pkl", "V6_长期_10天10%", 10, 0.10, 0.50),
    ("ml_v5_标准_5天5pct.pkl", "V5_标准_5天5%", 5, 0.05, 0.50),
]

# 获取所有股票
stock_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
print(f"股票数据文件: {len(stock_files)}")

# 测试200只股票
import random
random.seed(42)
test_stocks = random.sample(stock_files, 200)
print(f"测试股票: {len(test_stocks)}")

# 特征计算
def compute_features(df):
    df['p_ma5'] = df['close'] / df['close'].rolling(5).mean()
    df['p_ma10'] = df['close'] / df['close'].rolling(10).mean()
    df['p_ma20'] = df['close'] / df['close'].rolling(20).mean()
    df['p_ma60'] = df['close'] / df['close'].rolling(60).mean()
    
    df['ma5_slope'] = df['close'].rolling(5).mean().pct_change()
    df['ma10_slope'] = df['close'].rolling(10).mean().pct_change()
    df['ma20_slope'] = df['close'].rolling(20).mean().pct_change()
    
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

results_all = []

for model_file, model_name, forward, profit_target, threshold in MODELS:
    print(f"\n{'='*60}")
    print(f"回测模型: {model_name}")
    print(f"周期: {forward}天, 阈值: {threshold}")
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
            
            df = compute_features(df)
            
            valid_df = df.dropna(subset=features).copy()
            
            if len(valid_df) < forward + 30:
                continue
            
            X = valid_df[features].fillna(0).values.astype(np.float32)
            X_scaled = scaler.transform(X)
            y_prob = model.predict_proba(X_scaled)[:, 1]
            
            valid_df['prob'] = y_prob
            
            # 模拟交易 (简单版：所有信号都执行)
            in_position = False
            buy_idx = 0
            
            for i in range(len(valid_df) - forward):
                row = valid_df.iloc[i]
                
                if not in_position and row['prob'] >= threshold:
                    # 买入
                    buy_price = row['close']
                    buy_date = row['trade_date']
                    buy_idx = i
                    in_position = True
                
                if in_position and i >= buy_idx + forward:
                    # 卖出 (到期)
                    sell_row = valid_df.iloc[i]
                    sell_price = sell_row['close']
                    sell_date = sell_row['trade_date']
                    
                    profit_pct = (sell_price / buy_price - 1)
                    
                    trades.append({
                        'stock': stock_file.replace('.json', ''),
                        'buy_date': buy_date,
                        'sell_date': sell_date,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'profit_pct': profit_pct,
                        'prob': valid_df.iloc[buy_idx]['prob'],
                        'win': profit_pct > 0,
                    })
                    
                    cumulative_profit += profit_pct
                    in_position = False
        
        except Exception as e:
            continue
    
    if len(trades) > 0:
        avg_profit = cumulative_profit / len(trades)
        win_rate = sum(1 for t in trades if t['win']) / len(trades)
        
        profits = [t['profit_pct'] for t in trades]
        
        # 最大回撤计算
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
        
        print(f"\n回测结果:")
        print(f"  交易次数: {len(trades)}")
        print(f"  胜率: {win_rate:.1%}")
        print(f"  平均收益: {avg_profit*100:.2f}%")
        print(f"  收益中位数: {np.median(profits)*100:.2f}%")
        print(f"  最大单笔盈利: {max(profits)*100:.2f}%")
        print(f"  最大单笔亏损: {min(profits)*100:.2f}%")
        print(f"  最大回撤: {max_dd*100:.2f}%")
        
        results_all.append({
            'model': model_name,
            'forward': forward,
            'threshold': threshold,
            'trades': len(trades),
            'win_rate': win_rate,
            'avg_profit': avg_profit * 100,
            'median_profit': np.median(profits) * 100,
            'max_profit': max(profits) * 100,
            'min_profit': min(profits) * 100,
            'max_drawdown': max_dd * 100,
            'total_return': cumulative_profit * 100,
        })
        
        # 保存交易记录
        trades_df = pd.DataFrame(trades)
        trades_file = os.path.join(MODEL_DIR, f"backtest_{model_name.replace('%', 'pct')}.csv")
        trades_df.to_csv(trades_file, index=False)
        print(f"\n✅ 交易记录: {trades_file}")
    else:
        print(f"⚠️ 无交易记录")

# 汇总对比
print("\n" + "="*80)
print("回测对比汇总")
print("="*80)

print("\n| 模型 | 周期 | 阈值 | 交易数 | 胜率 | 平均收益 | 中位数 | 最大回撤 | 总收益 |")
print("|------|------|------|--------|------|----------|--------|----------|--------|")

for r in sorted(results_all, key=lambda x: x['avg_profit'], reverse=True):
    print(f"| {r['model']} | {r['forward']}天 | {r['threshold']} | {r['trades']} | {r['win_rate']:.1%} | {r['avg_profit']:.2f}% | {r['median_profit']:.2f}% | {r['max_drawdown']:.2f}% | {r['total_return']:.2f}% |")

# 推荐
if results_all:
    print("\n" + "="*80)
    print("推荐策略")
    print("="*80)
    
    best = max(results_all, key=lambda x: x['avg_profit'])
    print(f"\n🏆 最高收益: {best['model']}")
    print(f"   平均收益: {best['avg_profit']:.2f}%")
    print(f"   胜率: {best['win_rate']:.1%}")
    
    best_wr = max(results_all, key=lambda x: x['win_rate'])
    print(f"\n🥈 最高胜率: {best_wr['model']}")
    print(f"   胜率: {best_wr['win_rate']:.1%}")
    
    # 真实性验证
    print("\n📊 真实性验证:")
    print("   验证集 (batch_8) vs 回测结果:")
    
    validation_map = {
        'V6_超长_20天20%': 41.96,
        'V6_超长_15天15%': 33.13,
        'V6_中长_7天10%': 29.43,
        'V6_长期_10天10%': 24.79,
        'V5_标准_5天5%': 18.78,
    }
    
    for r in results_all:
        v_ret = validation_map.get(r['model'], 0)
        if v_ret > 0:
            diff = r['avg_profit'] - v_ret
            status = "✅" if abs(diff) < 10 else "⚠️"
            print(f"   {r['model']}: {status} 回测{r['avg_profit']:.2f}% vs 验证{v_ret:.2f}% (差{diff:.2f}%)")

print(f"\n完成时间: {datetime.now()}")