#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 集成模型回测脚本
"""

import pandas as pd
import numpy as np
import json
import pickle
from pathlib import Path
from datetime import datetime
import sys
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, roc_auc_score

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
        
        df = df.dropna(subset=feature_cols + ['label', 'future_return_5d'])
        
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
    n_samples = len(df) - min_history
    
    if n_samples <= 0:
        return [], [], []
    
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

def run_backtest(n_stocks=500, threshold=0.90):
    """运行回测"""
    log('='*60)
    log('V8 集成模型回测')
    log('='*60)
    
    models, config = load_v8_ensemble()
    
    log(f'\n回测参数:')
    log(f'  股票数量：{n_stocks}')
    log(f'  置信度阈值：{threshold*100}%')
    log(f'  持有期：5 天')
    
    stock_files = list(DATA_DIR.glob('*.json'))
    import random
    random.seed(42)
    selected_files = random.sample(stock_files, min(n_stocks, len(stock_files)))
    
    log(f'\n开始回测 {len(selected_files)} 只股票...')
    
    all_trades = []
    all_returns = []
    all_probs = []
    stock_stats = []
    
    for i, stock_file in enumerate(selected_files):
        df = load_stock_data(stock_file)
        if df is None:
            continue
        
        dates, returns, probs = backtest_single_stock(df, models, threshold)
        
        if len(returns) > 0:
            all_trades.extend(dates)
            all_returns.extend(returns)
            all_probs.extend(probs)
            
            stock_stats.append({
                'file': stock_file.name,
                'trades': len(returns),
                'avg_return': np.mean(returns),
                'win_rate': np.mean([r > 0.05 for r in returns])
            })
        
        if (i + 1) % 100 == 0:
            log(f'已回测 {i+1}/{len(selected_files)} 只股票')
    
    log(f'\n回测完成！')
    log(f'总交易数：{len(all_returns):,}')
    log(f'覆盖股票：{len(stock_stats)}')
    
    if len(all_returns) == 0:
        log('⚠️ 无交易信号')
        return None
    
    # 统计分析
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
    
    log(f'\n{">" * 60}')
    log('回测结果')
    log(f'{"=" * 60}')
    log(f'总交易数：{len(all_returns):,}')
    log(f'覆盖股票：{len(stock_stats)}')
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
            log(f'置信度>={int(conf_threshold*100)}%: {mask.sum()}次, 胜率{group_win*100:.1f}%, 平均收益{group_ret.mean()*100:.2f}%')
    
    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results = {
        'model': 'V8_ensemble',
        'threshold': threshold,
        'total_trades': len(all_returns),
        'n_stocks': len(stock_stats),
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
        'stock_stats': stock_stats,
        'timestamp': timestamp
    }
    
    result_file = RESULTS_DIR / f'backtest_v8_ensemble_{timestamp}.json'
    RESULTS_DIR.mkdir(exist_ok=True)
    with open(result_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    log(f'\n结果已保存：{result_file.name}')
    
    # V8 vs V7 对比
    log(f'\n{">" * 60}')
    log('V8 vs V7 对比')
    log(f'{"=" * 60}')
    
    v7_results = {'expected_return': 0.1445, 'win_rate': 0.875, 'trades': 1244}
    
    log(f'{"模型":<12} | {"期望收益":>10} | {"胜率":>8} | {"交易数":>8}')
    log(f'{"-"*12}-|-{"-"*10}-|-{"-"*8}-|-{"-"*8}')
    log(f'{"V7 精简版":<12} | {v7_results["expected_return"]*100:>9.2f}% | {v7_results["win_rate"]*100:>7.1f}% | {v7_results["trades"]:>8}')
    log(f'{"V8 组合版":<12} | {expected_return*100:>9.2f}% | {win_rate*100:>7.1f}% | {len(all_returns):>8}')
    
    improvement = (expected_return - v7_results['expected_return']) / v7_results['expected_return'] * 100
    log(f'\n相比 V7: 期望收益 {improvement:+.1f}%')
    
    return results

if __name__ == '__main__':
    results = run_backtest(n_stocks=500, threshold=0.90)
