#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 集成模型超大规模回测脚本 (内存优化版)
每批 100 只股票，避免内存不足
"""

import pandas as pd
import numpy as np
import json
import pickle
from pathlib import Path
from datetime import datetime
import sys
import gc
from sklearn.preprocessing import StandardScaler

DATA_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026')
MODEL_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks')
RESULTS_DIR = MODEL_DIR / 'backtest_results'

def log(msg):
    print(msg)
    sys.stdout.flush()

def load_stock_data(stock_file, min_records=200):
    """加载股票数据并计算 V8 特征"""
    try:
        with open(stock_file, 'r') as f:
            data = json.load(f)
        
        items = data.get('items', [])
        if len(items) < min_records:
            return None
        
        fields = data.get('fields', [])
        idx_map = {name: i for i, name in enumerate(fields)}
        
        required = ['trade_date', 'close', 'open', 'high', 'low', 'vol', 'pct_chg']
        if not all(r in idx_map for r in required):
            return None
        
        df_data = []
        for item in items:
            row = {
                'date': item[idx_map['trade_date']],
                'close': item[idx_map['close']],
                'open': item[idx_map['open']],
                'high': item[idx_map['high']],
                'low': item[idx_map['low']],
                'vol': item[idx_map['vol']],
                'pct_chg': item[idx_map['pct_chg']]
            }
            df_data.append(row)
        
        df = pd.DataFrame(df_data)
        df = df.sort_values('date').reset_index(drop=True)
        
        # V8 特征 (28 维)
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        df['p_ma5'] = (df['close'] - df['ma5']) / (df['ma5'] + 1e-10)
        df['p_ma10'] = (df['close'] - df['ma10']) / (df['ma10'] + 1e-10)
        df['p_ma20'] = (df['close'] - df['ma20']) / (df['ma20'] + 1e-10)
        
        df['ma5_slope'] = df['ma5'].pct_change(5)
        df['ma10_slope'] = df['ma10'].pct_change(5)
        
        df['ret5'] = df['close'].pct_change(5)
        df['ret10'] = df['close'].pct_change(10)
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - 100 / (1 + rs)
        
        df['vol_ma5'] = df['vol'].rolling(5).mean()
        df['vol_ratio'] = df['vol'] / (df['vol_ma5'] + 1e-10)
        
        df['ma20_roll'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['boll_upper'] = df['ma20_roll'] + 2 * df['std20']
        df['boll_lower'] = df['ma20_roll'] - 2 * df['std20']
        df['boll_pos'] = (df['close'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'] + 1e-10)
        
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_hist'] = df['macd'] - df['macd'].ewm(span=9, adjust=False).mean()
        
        low_9 = df['low'].rolling(9).min()
        high_9 = df['high'].rolling(9).max()
        df['kdj_k'] = 100 * (df['close'] - low_9) / (high_9 - low_9 + 1e-10)
        
        df['momentum10'] = (df['close'] / df['close'].shift(10) - 1).clip(-0.9, 5)
        
        df['volatility5'] = df['ret5'].rolling(5).std()
        df['volatility10'] = df['ret5'].rolling(10).std()
        df['vol_change'] = (df['volatility5'] / (df['volatility10'] + 1e-10)).clip(0.1, 10)
        
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        df['price_position'] = ((df['close'] - low_20) / (high_20 - low_20 + 1e-10)).clip(0, 1)
        
        df['future_return_5d'] = df['close'].shift(-5) / df['close'] - 1
        df['recent_return'] = df['close'].pct_change(3)
        df['acceleration'] = df['recent_return'] - df['recent_return'].shift(3)
        df['volatility_rank'] = df['volatility5'].rolling(60).rank(pct=True)
        df['up_days_ratio'] = (df['pct_chg'] > 0).rolling(10).mean()
        df['momentum_strength'] = (df['ret5'] - df['ret10']).clip(-0.5, 0.5)
        
        # V8 新增
        df['vol_price_corr'] = df['vol'].rolling(20).corr(df['close']).fillna(0).clip(-1, 1)
        df['vol_trend'] = (df['vol_ma5'] / (df['vol'].rolling(20).mean() + 1e-10)).clip(0.5, 2.0)
        df['momentum_accel'] = (df['ret5'] - df['ret5'].shift(5)).clip(-0.5, 0.5)
        df['trend_strength'] = (df['ma5'] - df['ma20']) / (df['ma20'] + 1e-10)
        df['volatility_trend'] = (df['volatility5'] / (df['volatility5'].shift(5) + 1e-10)).clip(0.5, 2.0)
        df['range_ratio'] = (df['high'] - df['low']) / (df['close'] + 1e-10)
        df['money_flow_proxy'] = (df['vol'] * df['pct_chg'] / 1e6).clip(-100, 100)
        df['money_flow_ma'] = df['money_flow_proxy'].rolling(5).mean()
        
        df['label'] = (df['future_return_5d'] > 0.05).astype(int)
        
        feature_cols = ['p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
                       'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
                       'momentum10', 'vol_change', 'price_position',
                       'volatility_rank', 'recent_return', 'acceleration',
                       'up_days_ratio', 'momentum_strength',
                       'vol_price_corr', 'vol_trend', 'momentum_accel', 'trend_strength',
                       'volatility_trend', 'range_ratio', 'money_flow_proxy', 'money_flow_ma']
        
        df = df.dropna(subset=feature_cols + ['label', 'future_return_5d', 'date', 'close'])
        
        if len(df) < 100:
            return None
        
        return df[feature_cols + ['label', 'future_return_5d', 'date', 'close']]
    
    except Exception as e:
        return None

def load_v8_ensemble():
    """加载 V8 集成模型"""
    config_files = list(MODEL_DIR.glob('models/ml_nn_v8_ensemble_config_*.json'))
    if not config_files:
        raise FileNotFoundError("未找到 V8 集成配置文件")
    
    latest_config = max(config_files)
    with open(latest_config, 'r') as f:
        config = json.load(f)
    
    models = []
    for model_path in config['model_paths']:
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        models.append(data['model'])
    
    log(f'已加载 V8 集成模型：{len(models)} 个子模型')
    log(f'平均 AUC: {config["avg_auc"]:.4f} ± {config["std_auc"]:.4f}')
    
    return models, config

def predict_ensemble(models, X):
    """集成预测"""
    probs = []
    for model in models:
        prob = model.predict_proba(X)[:, 1]
        probs.append(prob)
    return np.mean(probs, axis=0)

def backtest_single_stock(df, models, threshold=0.90):
    """单只股票回测"""
    feature_cols = ['p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
                   'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
                   'momentum10', 'vol_change', 'price_position',
                   'volatility_rank', 'recent_return', 'acceleration',
                   'up_days_ratio', 'momentum_strength',
                   'vol_price_corr', 'vol_trend', 'momentum_accel', 'trend_strength',
                   'volatility_trend', 'range_ratio', 'money_flow_proxy', 'money_flow_ma']
    
    X = df[feature_cols].values
    dates = df['date'].values
    returns = df['future_return_5d'].values
    
    min_history = 60
    
    trades = []
    trade_dates = []
    trade_returns = []
    
    for i in range(min_history, len(df) - 5):
        X_train = X[:i]
        X_test = X[i:i+1]
        
        # 动态标准化
        scaler_temp = StandardScaler()
        scaler_temp.fit(X_train)
        X_test_scaled = scaler_temp.transform(X_test)
        
        # 预测
        prob = predict_ensemble(models, X_test_scaled)[0]
        
        if prob >= threshold:
            ret = returns[i]
            if not np.isnan(ret):
                trades.append(prob)
                trade_dates.append(dates[i])
                trade_returns.append(ret)
    
    return trade_dates, trade_returns, trades

def backtest_batch(stock_files, models, threshold=0.90, batch_idx=0):
    """回测单个批次"""
    all_returns = []
    all_probs = []
    stock_stats = []
    
    for i, stock_file in enumerate(stock_files):
        df = load_stock_data(stock_file)
        if df is None:
            continue
        
        dates, returns, probs = backtest_single_stock(df, models, threshold)
        
        if len(returns) > 0:
            all_returns.extend(returns)
            all_probs.extend(probs)
            
            stock_stats.append({
                'file': stock_file.name,
                'trades': len(returns),
                'avg_return': float(np.mean(returns)),
                'win_rate': float(np.mean([r > 0.05 for r in returns]))
            })
        
        if (i + 1) % 50 == 0:
            log(f'  批次{batch_idx+1}: 已回测 {i+1}/{len(stock_files)} 只股票')
        
        # 每 25 只股票 GC 一次
        if (i + 1) % 25 == 0:
            gc.collect()
    
    return all_returns, all_probs, stock_stats

def run_ultra_large_backtest(n_stocks=3000, batch_size=100, threshold=0.90, start_batch=0):
    """运行超大规模回测 (内存优化)"""
    log('='*60)
    log('V8 集成模型超大规模回测 (内存优化版)')
    log('='*60)
    
    models, config = load_v8_ensemble()
    
    log(f'\n回测参数:')
    log(f'  总股票数：{n_stocks}')
    log(f'  批次大小：{batch_size} (内存优化)')
    log(f'  置信度阈值：{threshold*100}%')
    log(f'  持有期：5 天')
    log(f'  起始批次：{start_batch+1} (从 0 开始计数)')
    
    stock_files = list(DATA_DIR.glob('*.json'))
    import random
    random.seed(42)
    selected_files = random.sample(stock_files, min(n_stocks, len(stock_files)))
    
    # 分批
    n_batches = (len(selected_files) + batch_size - 1) // batch_size
    log(f'\n分 {n_batches} 批回测，每批 {batch_size} 只股票')
    log(f'预计耗时：{(n_batches - start_batch) * 4} 分钟')
    
    all_batch_results = []
    total_trades = 0
    total_stocks = 0
    
    start_time = datetime.now()
    
    for batch_idx in range(start_batch, n_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(selected_files))
        batch_files = selected_files[start_idx:end_idx]
        
        batch_start = datetime.now()
        log(f'\n{"="*60}')
        log(f'批次 {batch_idx+1}/{n_batches} (股票 {start_idx+1}-{end_idx})')
        log(f'{"="*60}')
        
        # 回测当前批次
        returns, probs, stock_stats = backtest_batch(batch_files, models, threshold, batch_idx)
        
        batch_result = {
            'batch_idx': batch_idx,
            'n_stocks': len(batch_files),
            'returns': returns,
            'probs': probs,
            'stock_stats': stock_stats
        }
        all_batch_results.append(batch_result)
        
        batch_trades = len(returns)
        batch_stocks = len(stock_stats)
        total_trades += batch_trades
        total_stocks += batch_stocks
        
        batch_end = datetime.now()
        batch_duration = (batch_end - batch_start).total_seconds() / 60
        
        log(f'\n批次 {batch_idx+1} 完成:')
        log(f'  交易数：{batch_trades}')
        log(f'  覆盖股票：{batch_stocks}')
        if len(returns) > 0:
            log(f'  平均收益：{np.mean(returns)*100:.2f}%')
            log(f'  胜率：{np.mean([r > 0.05 for r in returns])*100:.1f}%')
        log(f'  耗时：{batch_duration:.1f}分钟')
        
        # 保存批次结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_file = RESULTS_DIR / f'backtest_v8_ultra_batch{batch_idx+1}_{timestamp}.json'
        RESULTS_DIR.mkdir(exist_ok=True)
        with open(batch_file, 'w') as f:
            json.dump({
                'batch_idx': batch_idx,
                'n_stocks': len(batch_files),
                'n_trades': len(returns),
                'stock_stats': stock_stats
            }, f, indent=2)
        
        # 强制垃圾回收 (关键！)
        del returns, probs, stock_stats, batch_result
        gc.collect()
        
        # 进度报告
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        if batch_idx > 0:
            remaining = (n_batches - batch_idx - 1) * (elapsed / (batch_idx + 1))
            log(f'\n📊 总进度：{batch_idx+1}/{n_batches} ({(batch_idx+1)/n_batches*100:.1f}%)')
            log(f'⏱️  已用：{elapsed:.1f}分钟，预计剩余：{remaining:.1f}分钟')
            log(f'📈 累计交易：{total_trades:,}，覆盖股票：{total_stocks}')
    
    # 合并所有批次结果
    log(f'\n{"="*60}')
    log('合并所有批次结果...')
    log(f'{"="*60}')
    
    all_returns = []
    all_probs = []
    all_stock_stats = []
    
    for batch_result in all_batch_results:
        all_returns.extend(batch_result['returns'])
        all_probs.extend(batch_result['probs'])
        all_stock_stats.extend(batch_result['stock_stats'])
    
    # 分析最终结果
    all_returns = np.array(all_returns)
    all_probs = np.array(all_probs)
    
    wins = all_returns > 0.05
    big_wins = all_returns > 0.10
    losses = all_returns < -0.08
    
    avg_return = all_returns.mean()
    win_rate = wins.mean()
    avg_win = all_returns[wins].mean() if wins.sum() > 0 else 0
    avg_loss = all_returns[~wins].mean() if (~wins).sum() > 0 else 0
    
    profit_loss_ratio = (avg_win if avg_win > 0 else 0) / (abs(avg_loss) if avg_loss < 0 else 1)
    expected_return = win_rate * avg_win + (1 - win_rate) * avg_loss
    
    total_duration = (datetime.now() - start_time).total_seconds() / 60
    
    log(f'\n{">" * 60}')
    log('🎉 回测完成！')
    log(f'{"=" * 60}')
    log(f'总耗时：{total_duration:.1f}分钟')
    log(f'总交易数：{len(all_returns):,}')
    log(f'覆盖股票：{len(all_stock_stats)}')
    log(f'平均收益：{avg_return*100:.2f}%')
    log(f'胜率 (涨超 5%): {win_rate*100:.1f}%')
    log(f'大涨率 (涨超 10%): {big_wins.mean()*100:.1f}%')
    log(f'止损率 (跌超 8%): {losses.mean()*100:.1f}%')
    log(f'平均盈利：{avg_win*100:.2f}%')
    log(f'平均亏损：{avg_loss*100:.2f}%')
    log(f'盈亏比：{profit_loss_ratio:.2f}')
    log(f'期望收益 (每次交易): {expected_return*100:.2f}%')
    
    # 按置信度分组
    log(f'\n{">" * 60}')
    log('按置信度分组')
    log(f'{"=" * 60}')
    
    for conf_threshold in [0.90, 0.92, 0.95, 0.97]:
        mask = all_probs >= conf_threshold
        if mask.sum() > 0:
            group_ret = all_returns[mask]
            group_win = (group_ret > 0.05).mean()
            log(f'置信度>={int(conf_threshold*100)}%: {mask.sum()}次，胜率{group_win*100:.1f}%, 平均收益{group_ret.mean()*100:.2f}%')
    
    # 保存最终结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    final_results = {
        'model': 'V8_ensemble',
        'threshold': threshold,
        'n_stocks_requested': n_stocks,
        'n_stocks_actual': len(all_stock_stats),
        'n_batches': n_batches,
        'batch_size': batch_size,
        'total_duration_min': total_duration,
        'total_trades': len(all_returns),
        'avg_return': float(avg_return),
        'win_rate': float(win_rate),
        'big_win_rate': float(big_wins.mean()),
        'loss_rate': float(losses.mean()),
        'avg_win': float(avg_win),
        'avg_loss': float(avg_loss),
        'profit_loss_ratio': float(profit_loss_ratio),
        'expected_return': float(expected_return),
        'all_returns': all_returns.tolist(),
        'all_probs': all_probs.tolist(),
        'stock_stats': all_stock_stats,
        'timestamp': timestamp
    }
    
    result_file = RESULTS_DIR / f'backtest_v8_ultra_{n_stocks}stocks_{timestamp}.json'
    with open(result_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    log(f'\n最终结果已保存：{result_file.name}')
    
    # 与之前回测对比
    log(f'\n{">" * 60}')
    log('历史回测对比')
    log(f'{"=" * 60}')
    
    log(f'{"回测":<20} | {"股票数":>8} | {"交易数":>8} | {"胜率":>8} | {"期望收益":>10}')
    log(f'{"-"*20}-|-{"-"*8}-|-{"-"*8}-|-{"-"*8}-|-{"-"*10}')
    
    # V7 精简版
    log(f'{"V7 精简版":<20} | {312:>8} | {1244:>8} | {87.5:>7.1f}% | {14.45:>9.2f}%')
    # V8 500 股
    log(f'{"V8 500 股":<20} | {352:>8} | {1303:>8} | {89.5:>7.1f}% | {14.25:>9.2f}%')
    # V8 800 股 (中断)
    log(f'{"V8 800 股":<20} | {571:>8} | {2102:>8} | {88.8:>7.1f}% | {14.3:>9.2f}%')
    # V8 超大规模
    log(f'{"V8 {n_stocks}股":<20} | {len(all_stock_stats):>8} | {len(all_returns):>8} | {win_rate*100:>7.1f}% | {expected_return*100:>9.2f}%')
    
    return final_results

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--n-stocks', type=int, default=3000, help='回测股票数量')
    parser.add_argument('--batch-size', type=int, default=50, help='每批股票数 (内存优化，默认 50 避免 OOM)')
    parser.add_argument('--threshold', type=float, default=0.90, help='置信度阈值')
    parser.add_argument('--start-batch', type=int, default=0, help='起始批次 (从 0 开始，用于续测)')
    args = parser.parse_args()
    
    results = run_ultra_large_backtest(
        n_stocks=args.n_stocks,
        batch_size=args.batch_size,
        threshold=args.threshold,
        start_batch=args.start_batch
    )
