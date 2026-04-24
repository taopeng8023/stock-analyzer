#!/usr/bin/env python3
"""
V6模型回测验证
使用历史数据模拟真实交易，验证实际收益

回测逻辑：
1. 买入：置信度 >= 阈值
2. 持仓：forward天
3. 卖出：到期/止损/止盈
4. 计算真实收益、胜率、最大回撤
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
print("V6模型回测验证")
print("="*80)
print(f"开始时间: {datetime.now()}")

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 要回测的模型
MODELS = [
    ("ml_v6_超长_20天20pct.pkl", "V6_超长_20天20%", 20, 0.20, 0.85),
    ("ml_v6_超长_15天15pct.pkl", "V6_超长_15天15%", 15, 0.15, 0.90),
    ("ml_v6_中长_7天10pct.pkl", "V6_中长_7天10%", 7, 0.10, 0.90),
    ("ml_v5_标准_5天5pct.pkl", "V5_标准_5天5%", 5, 0.05, 0.90),
]

# 获取测试股票列表
stock_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
print(f"股票数据文件: {len(stock_files)}")

# 选择测试股票 (随机100只)
import random
random.seed(42)
test_stocks = random.sample(stock_files, 100)
print(f"测试股票: {len(test_stocks)}")

# 计算特征
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
    print(f"周期: {forward}天, 目标: {profit_target*100:.0f}%")
    print(f"{'='*60}")
    
    # 加载模型
    model_path = os.path.join(MODEL_DIR, model_file)
    if not os.path.exists(model_path):
        print(f"模型文件不存在: {model_path}")
        continue
    
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data['model']
    scaler = model_data['scaler']
    features = model_data['features']
    
    # 回测统计
    trades = []
    total_profit = 0
    wins = 0
    losses = 0
    max_drawdown = 0
    peak_profit = 0
    
    for stock_file in test_stocks:
        try:
            stock_path = os.path.join(DATA_DIR, stock_file)
            with open(stock_path, 'r') as f:
                data = json.load(f)
            
            if 'items' not in data or len(data['items']) < 100:
                continue
            
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            # 计算特征
            df = compute_features(df)
            
            # 预测
            valid_df = df.dropna(subset=features).copy()
            
            if len(valid_df) < forward + 30:
                continue
            
            X = valid_df[features].fillna(0).values.astype(np.float32)
            X_scaled = scaler.transform(X)
            y_prob = model.predict_proba(X_scaled)[:, 1]
            
            # 添加预测结果
            valid_df['prob'] = y_prob
            
            # 模拟交易
            for i in range(len(valid_df) - forward):
                row = valid_df.iloc[i]
                
                if row['prob'] >= threshold:
                    # 买入信号
                    buy_price = row['close']
                    buy_date = row['trade_date']
                    
                    # 查找卖出点
                    sell_idx = i + forward
                    if sell_idx < len(valid_df):
                        sell_row = valid_df.iloc[sell_idx]
                        sell_price = sell_row['close']
                        sell_date = sell_row['trade_date']
                        
                        # 计算收益
                        profit_pct = (sell_price / buy_price - 1)
                        
                        trades.append({
                            'stock': stock_file.replace('.json', ''),
                            'buy_date': buy_date,
                            'sell_date': sell_date,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'profit_pct': profit_pct,
                            'prob': row['prob'],
                            'win': profit_pct > 0,
                        })
                        
                        total_profit += profit_pct
                        if profit_pct > 0:
                            wins += 1
                        else:
                            losses += 1
                        
                        # 计算最大回撤
                        peak_profit = max(peak_profit, total_profit)
                        drawdown = peak_profit - total_profit
                        max_drawdown = max(max_drawdown, drawdown)
        
        except Exception as e:
            continue
    
    # 统计
    if len(trades) > 0:
        avg_profit = total_profit / len(trades)
        win_rate = wins / len(trades)
        
        # 计算收益分布
        profits = [t['profit_pct'] for t in trades]
        profit_median = np.median(profits)
        profit_std = np.std(profits)
        
        print(f"\n回测结果:")
        print(f"  总交易次数: {len(trades)}")
        print(f"  盈利次数: {wins}")
        print(f"  亏损次数: {losses}")
        print(f"  胜率: {win_rate:.1%}")
        print(f"  平均收益: {avg_profit*100:.2f}%")
        print(f"  收益中位数: {profit_median*100:.2f}%")
        print(f"  收益标准差: {profit_std*100:.2f}%")
        print(f"  最大回撤: {max_drawdown*100:.2f}%")
        print(f"  收益/回撤比: {avg_profit/max_drawdown if max_drawdown > 0 else 0:.2f}")
        
        # 收益分布
        print(f"\n收益分布:")
        wins_dist = [p for p in profits if p > 0]
        losses_dist = [p for p in profits if p <= 0]
        
        if wins_dist:
            print(f"  盈利区间: {min(wins_dist)*100:.2f}% ~ {max(wins_dist)*100:.2f}%")
            print(f"  盈利平均: {np.mean(wins_dist)*100:.2f}%")
        
        if losses_dist:
            print(f"  亏损区间: {min(losses_dist)*100:.2f}% ~ {max(losses_dist)*100:.2f}%")
            print(f"  亏损平均: {np.mean(losses_dist)*100:.2f}%")
        
        results_all.append({
            'model': model_name,
            'forward': forward,
            'target': profit_target * 100,
            'threshold': threshold,
            'trades': len(trades),
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'avg_profit': avg_profit * 100,
            'median_profit': profit_median * 100,
            'std_profit': profit_std * 100,
            'max_drawdown': max_drawdown * 100,
            'profit_drawdown_ratio': avg_profit/max_drawdown if max_drawdown > 0 else 0,
        })
        
        # 保存交易记录
        trades_df = pd.DataFrame(trades)
        trades_file = os.path.join(MODEL_DIR, f"backtest_trades_{model_name.replace('%', 'pct')}.csv")
        trades_df.to_csv(trades_file, index=False)
        print(f"\n✅ 交易记录保存: {trades_file}")

# 对比汇总
print("\n" + "="*80)
print("回测对比汇总")
print("="*80)

print("\n| 模型 | 周期 | 目标 | 交易数 | 胜率 | 平均收益 | 中位数 | 最大回撤 | 收益/回撤 |")
print("|------|------|------|--------|------|----------|--------|----------|----------|")

for r in sorted(results_all, key=lambda x: x['avg_profit'], reverse=True):
    print(f"| {r['model']} | {r['forward']}天 | {r['target']:.0f}% | {r['trades']} | {r['win_rate']:.1%} | {r['avg_profit']:.2f}% | {r['median_profit']:.2f}% | {r['max_drawdown']:.2f}% | {r['profit_drawdown_ratio']:.2f} |")

# 最终推荐
print("\n" + "="*80)
print("回测结论")
print("="*80)

if results_all:
    # 最高收益
    best_profit = max(results_all, key=lambda x: x['avg_profit'])
    print(f"\n🏆 最高收益: {best_profit['model']}")
    print(f"   平均收益: {best_profit['avg_profit']:.2f}%")
    print(f"   胜率: {best_profit['win_rate']:.1%}")
    
    # 最高胜率
    best_win = max(results_all, key=lambda x: x['win_rate'])
    print(f"\n🥈 最高胜率: {best_win['model']}")
    print(f"   胜率: {best_win['win_rate']:.1%}")
    
    # 最佳风险收益比
    best_ratio = max(results_all, key=lambda x: x['profit_drawdown_ratio'])
    print(f"\n🥉 最佳风险收益比: {best_ratio['model']}")
    print(f"   收益/回撤: {best_ratio['profit_drawdown_ratio']:.2f}")
    
    # 对比验证集结果
    print(f"\n📊 对比验证集 (测试batch_8) 结果:")
    print(f"   V6超长_20天: 验证41.96% → 回测{best_profit['avg_profit']:.2f}%")
    
    # 真实性评估
    for r in results_all:
        validation_return = {
            'V6_超长_20天20%': 41.96,
            'V6_超长_15天15%': 33.13,
            'V6_中长_7天10%': 29.43,
            'V5_标准_5天5%': 18.78,
        }.get(r['model'], 0)
        
        if validation_return > 0:
            diff = r['avg_profit'] - validation_return
            if abs(diff) < 5:
                print(f"   {r['model']}: ✅ 回测与验证一致 (差异{diff:.2f}%)")
            elif diff > 0:
                print(f"   {r['model']}: ✅ 回测优于验证 (+{diff:.2f}%)")
            else:
                print(f"   {r['model']}: ⚠️ 回测低于验证 ({diff:.2f}%)")

print(f"\n完成时间: {datetime.now()}")