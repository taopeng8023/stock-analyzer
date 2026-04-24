#!/usr/bin/env python3
"""
V6模型全量回测验证 - 5503只股票
目标：验证模型在所有股票上的真实表现

测试模型：
- V6_中长_7天10% (最优)
- V6_长期_10天10%
- V5_标准_5天5%
- V5_短攻_3天5%
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
print("V6模型全量回测验证 - 5503只股票")
print("="*80)
print(f"开始时间: {datetime.now()}")

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 全量股票
stock_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
print(f"股票数据文件: {len(stock_files)}")

# 测试模型
MODELS = [
    ("ml_v6_中长_7天10pct.pkl", "V6_中长_7天10%", 7, 0.10),
    ("ml_v6_长期_10天10pct.pkl", "V6_长期_10天10%", 10, 0.10),
    ("ml_v5_标准_5天5pct.pkl", "V5_标准_5天5%", 5, 0.05),
    ("ml_v5_短攻_3天5pct.pkl", "V5_短攻_3天5%", 3, 0.05),
]

# 特征计算 - 与原始一致
def compute_features_fixed(df):
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

results_all = []
total_stocks = len(stock_files)

for model_file, model_name, forward, profit_target in MODELS:
    print(f"\n{'='*60}")
    print(f"回测模型: {model_name}")
    print(f"周期: {forward}天")
    print(f"{'='*60}")
    
    model_path = os.path.join(MODEL_DIR, model_file)
    if not os.path.exists(model_path):
        print(f"⚠️ 模型不存在")
        continue
    
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data['model']
    scaler = model_data['scaler']
    features = model_data['features']
    metrics = model_data.get('metrics', {})
    threshold = metrics.get('threshold', 0.85)
    
    trades = []
    processed = 0
    
    for stock_file in stock_files:
        processed += 1
        
        if processed % 500 == 0:
            print(f"  处理进度: {processed}/{total_stocks} ({processed*100//total_stocks}%)")
        
        try:
            with open(os.path.join(DATA_DIR, stock_file), 'r') as f:
                data = json.load(f)
            
            if 'items' not in data or len(data['items']) < 80:
                continue
            
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            df = compute_features_fixed(df)
            valid_df = df.dropna(subset=features).copy()
            
            if len(valid_df) < forward + 30:
                continue
            
            X = valid_df[features].fillna(0).values.astype(np.float32)
            X_scaled = scaler.transform(X)
            y_prob = model.predict_proba(X_scaled)[:, 1]
            
            valid_df['prob'] = y_prob
            
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
        
        except Exception as e:
            continue
    
    if trades:
        profits = [t['profit_pct'] for t in trades]
        wins = sum(1 for t in trades if t['win'])
        
        avg_profit = np.mean(profits)
        median_profit = np.median(profits)
        win_rate = wins / len(trades)
        
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
        
        # 收益分布
        p10 = np.percentile(profits, 10)
        p90 = np.percentile(profits, 90)
        
        print(f"\n✅ 全量回测结果:")
        print(f"  处理股票: {processed}")
        print(f"  交易次数: {len(trades)}")
        print(f"  覆盖股票: {len(set(t['stock'] for t in trades))}")
        print(f"  胜率: {win_rate:.1%}")
        print(f"  平均收益: {avg_profit*100:.2f}%")
        print(f"  收益中位数: {median_profit*100:.2f}%")
        print(f"  收益P10: {p10*100:.2f}%")
        print(f"  收益P90: {p90*100:.2f}%")
        print(f"  最大单笔盈利: {max(profits)*100:.2f}%")
        print(f"  最大单笔亏损: {min(profits)*100:.2f}%")
        print(f"  最大回撤: {max_dd*100:.2f}%")
        print(f"  总累计收益: {sum(profits)*100:.2f}%")
        
        results_all.append({
            'model': model_name,
            'forward': forward,
            'threshold': threshold,
            'trades': len(trades),
            'stocks_covered': len(set(t['stock'] for t in trades)),
            'win_rate': win_rate,
            'avg_profit': avg_profit * 100,
            'median_profit': median_profit * 100,
            'p10': p10 * 100,
            'p90': p90 * 100,
            'max_win': max(profits) * 100,
            'max_loss': min(profits) * 100,
            'max_drawdown': max_dd * 100,
            'total_return': sum(profits) * 100,
        })
        
        # 保存交易记录
        trades_df = pd.DataFrame(trades)
        trades_file = os.path.join(MODEL_DIR, f"backtest_full_{model_name.replace('%', 'pct')}.csv")
        trades_df.to_csv(trades_file, index=False)
        print(f"\n✅ 交易记录: {trades_file}")
    else:
        print(f"\n⚠️ 无交易")

# 汇总对比
print("\n" + "="*80)
print("全量回测对比汇总 (5503只股票)")
print("="*80)

if results_all:
    print("\n| 模型 | 周期 | 交易数 | 覆盖股票 | 胜率 | 平均收益 | 中位数 | P10 | P90 | 最大回撤 | 总收益 |")
    print("|------|------|--------|----------|------|----------|--------|-----|-----|----------|--------|")
    
    for r in sorted(results_all, key=lambda x: x['avg_profit'], reverse=True):
        print(f"| {r['model']} | {r['forward']}天 | {r['trades']} | {r['stocks_covered']} | {r['win_rate']:.1%} | {r['avg_profit']:.2f}% | {r['median_profit']:.2f}% | {r['p10']:.2f}% | {r['p90']:.2f}% | {r['max_drawdown']:.2f}% | {r['total_return']:.2f}% |")
    
    # 推荐
    print("\n" + "="*80)
    print("推荐策略")
    print("="*80)
    
    best = max(results_all, key=lambda x: x['avg_profit'])
    print(f"\n🏆 最高收益: {best['model']}")
    print(f"   平均收益: {best['avg_profit']:.2f}%")
    print(f"   覆盖股票: {best['stocks_covered']}")
    print(f"   胜率: {best['win_rate']:.1%}")
    
    best_wr = max(results_all, key=lambda x: x['win_rate'])
    print(f"\n🥈 最高胜率: {best_wr['model']}")
    print(f"   胜率: {best_wr['win_rate']:.1%}")
    
    # 对比100股样本
    print("\n📊 对比100股样本回测:")
    sample_results = {
        'V6_中长_7天10%': 39.47,
        'V6_长期_10天10%': 37.33,
        'V5_标准_5天5%': 21.92,
        'V5_短攻_3天5%': 13.68,
    }
    
    for r in results_all:
        sample = sample_results.get(r['model'], 0)
        if sample > 0:
            diff = r['avg_profit'] - sample
            print(f"  {r['model']}: 全量{r['avg_profit']:.2f}% vs 样本{sample:.2f}% (差{diff:.1f}%)")

print(f"\n完成时间: {datetime.now()}")