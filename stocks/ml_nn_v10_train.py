#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V10 右侧交易模型训练
特征：已经涨起来的股票 (5 日>5%, 10 日>8%, RSI50-70, 均线多头)
目标：预测未来 5 天继续涨超 8%
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import pickle
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score
import warnings
import sys
warnings.filterwarnings('ignore')

# 配置
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/backtest_results")

# V10 特征 (28 维)
V10_FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
    'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
    'momentum10', 'vol_change', 'price_position',
    'volatility_rank', 'recent_return', 'acceleration',
    'up_days_ratio', 'momentum_strength',
    'vol_price_corr', 'vol_trend', 'momentum_accel', 'trend_strength',
    'volatility_trend', 'range_ratio', 'money_flow_proxy', 'money_flow_ma'
]

# 右侧交易选股条件 (用于筛选训练样本)
RIGHT_SIDE_CONDITIONS = {
    'ret5_min': 0.05,      # 5 日涨超 5%
    'ret10_min': 0.08,     # 10 日涨超 8%
    'rsi_min': 50,         # RSI >= 50
    'rsi_max': 70,         # RSI < 70
    'ma5_above_ma10': True,
    'price_above_ma5': True,
}

# 正样本定义：未来 5 天涨超 8%
FUTURE_RETURN_THRESHOLD = 0.08
FORECAST_PERIOD = 5

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

def calculate_rsi(closes, period=14):
    """计算 RSI"""
    if len(closes) < period + 1:
        return 50
    
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i-1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-delta)
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def check_right_side(df):
    """检查是否符合右侧交易条件"""
    try:
        closes = df['close'].values
        if len(closes) < 60:
            return False
        
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        
        ret5 = closes[-1] / closes[-6] - 1 if len(closes) >= 6 else 0
        ret10 = closes[-1] / closes[-11] - 1 if len(closes) >= 11 else 0
        rsi = calculate_rsi(closes)
        
        if ret5 < RIGHT_SIDE_CONDITIONS['ret5_min']:
            return False
        if ret10 < RIGHT_SIDE_CONDITIONS['ret10_min']:
            return False
        if not (RIGHT_SIDE_CONDITIONS['rsi_min'] <= rsi < RIGHT_SIDE_CONDITIONS['rsi_max']):
            return False
        if RIGHT_SIDE_CONDITIONS['ma5_above_ma10'] and ma5 <= ma10:
            return False
        if RIGHT_SIDE_CONDITIONS['price_above_ma5'] and closes[-1] < ma5:
            return False
        
        return True
    except:
        return False

def calculate_features(df):
    """计算 28 维特征"""
    try:
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        volumes = df['vol'].values if 'vol' in df.columns else df['amount'].values
        
        if len(closes) < 60:
            return None
        
        # 均线
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        
        p_ma5 = closes[-1] / ma5 - 1
        p_ma10 = closes[-1] / ma10 - 1
        p_ma20 = closes[-1] / ma20 - 1
        
        ma5_slope = (closes[-1] - closes[-6]) / closes[-6] if len(closes) >= 6 else 0
        ma10_slope = (ma5 - ma10) / ma10
        
        # 收益率
        ret5 = closes[-1] / closes[-6] - 1 if len(closes) >= 6 else 0
        ret10 = closes[-1] / closes[-11] - 1 if len(closes) >= 11 else 0
        
        # RSI
        rsi = calculate_rsi(closes) / 100
        
        # MACD
        ema12 = pd.Series(closes).ewm(span=12).mean().values
        ema26 = pd.Series(closes).ewm(span=26).mean().values
        macd = ema12 - ema26
        macd_signal = pd.Series(macd).ewm(span=9).mean().values
        macd_hist = (macd[-1] - macd_signal[-1]) / closes[-1]
        
        # KDJ
        low_9 = np.min(lows[-9:])
        high_9 = np.max(highs[-9:])
        kdj_k = ((closes[-1] - low_9) / (high_9 - low_9)) if high_9 > low_9 else 0.5
        
        # 成交量
        vol_ma5 = np.mean(volumes[-5:])
        vol_ma10 = np.mean(volumes[-10:])
        vol_ratio = volumes[-1] / vol_ma5 if vol_ma5 > 0 else 1
        vol_change = volumes[-1] / vol_ma10 - 1 if vol_ma10 > 0 else 0
        
        # 布林带
        boll_std = np.std(closes[-20:])
        boll_pos = (closes[-1] - (ma20 - 2*boll_std)) / (4*boll_std) if boll_std > 0 else 0.5
        
        # 其他特征
        momentum10 = ret10
        vol_change_pct = (volumes[-1] - volumes[-6]) / volumes[-6] if len(volumes) >= 6 else 0
        price_position = (closes[-1] - np.min(closes[-60:])) / (np.max(closes[-60:]) - np.min(closes[-60:]))
        volatility_rank = np.std(closes[-20:]) / np.mean(closes[-20:])
        acceleration = ret5 - ret10
        up_days_ratio = np.sum(np.diff(closes[-20:]) > 0) / 19
        
        features = {
            'p_ma5': p_ma5, 'p_ma10': p_ma10, 'p_ma20': p_ma20,
            'ma5_slope': ma5_slope, 'ma10_slope': ma10_slope,
            'ret5': ret5, 'ret10': ret10, 'rsi': rsi, 'macd_hist': macd_hist,
            'kdj_k': kdj_k, 'vol_ratio': vol_ratio, 'boll_pos': boll_pos,
            'momentum10': momentum10, 'vol_change': vol_change, 'price_position': price_position,
            'volatility_rank': volatility_rank, 'recent_return': ret5, 'acceleration': acceleration,
            'up_days_ratio': up_days_ratio, 'momentum_strength': abs(ret10),
            'vol_price_corr': 0, 'vol_trend': vol_ma5/vol_ma10-1, 'momentum_accel': acceleration,
            'trend_strength': abs(ma5_slope), 'volatility_trend': 0,
            'range_ratio': (highs[-1]-lows[-1])/closes[-2], 'money_flow_proxy': 0, 'money_flow_ma': 0
        }
        
        return features
    except Exception as e:
        return None

def prepare_training_data():
    """准备训练数据"""
    log(f"\n{'='*70}")
    log("📊 准备 V10 训练数据")
    log(f"{'='*70}")
    
    stock_list_path = HISTORY_DIR / "stock_list.json"
    with open(stock_list_path, 'r') as f:
        stock_list = json.load(f)
    
    X_list = []
    y_list = []
    codes = []
    
    total = len(stock_list)
    right_side_count = 0
    valid_sample_count = 0
    
    for i, stock in enumerate(stock_list):
        code = stock.get('ts_code', '')
        if '.' in code:
            code = code.split('.')[0]
        
        data_path = HISTORY_DIR / f"{code}.json"
        if not data_path.exists():
            continue
        
        try:
            with open(data_path, 'r') as f:
                data = json.load(f)
            
            if not data.get('items'):
                continue
            
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df = df.drop_duplicates(subset=['trade_date'], keep='last').reset_index(drop=True)
            
            if len(df) < FORECAST_PERIOD + 10:
                continue
            
            # 只取有未来数据的部分
            for idx in range(len(df) - FORECAST_PERIOD):
                df_window = df.iloc[:idx+1].reset_index(drop=True)
                
                # 检查是否符合右侧交易条件
                if not check_right_side(df_window):
                    continue
                
                right_side_count += 1
                
                # 计算特征
                features = calculate_features(df_window)
                if features is None:
                    continue
                
                # 计算未来收益
                future_close = df.iloc[idx + FORECAST_PERIOD]['close']
                current_close = df.iloc[idx]['close']
                future_return = (future_close - current_close) / current_close
                
                # 标签：未来 5 天涨超 8%
                label = 1 if future_return >= FUTURE_RETURN_THRESHOLD else 0
                
                X_list.append([features.get(f, 0) for f in V10_FEATURES])
                y_list.append(label)
                codes.append(code)
                valid_sample_count += 1
            
            if (i + 1) % 500 == 0:
                log(f"进度：{i+1}/{total} - 右侧交易样本：{valid_sample_count}")
                
        except Exception as e:
            continue
    
    log(f"\n{'='*70}")
    log("📊 数据准备完成")
    log(f"{'='*70}")
    log(f"扫描股票：{total} 只")
    log(f"右侧交易信号：{right_side_count} 个")
    log(f"有效样本：{valid_sample_count} 个")
    log(f"正样本比例：{np.mean(y_list)*100:.1f}%")
    
    return np.array(X_list), np.array(y_list), codes

def train_v10():
    """训练 V10 模型"""
    log(f"\n{'='*70}")
    log("🚀 V10 右侧交易模型训练")
    log(f"{'='*70}")
    
    # 准备数据
    X, y, codes = prepare_training_data()
    
    if len(X) == 0:
        log("\n❌ 没有足够的训练样本！")
        return
    
    # 数据集划分
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    log(f"\n训练集：{len(X_train)} 样本")
    log(f"测试集：{len(X_test)} 样本")
    log(f"正样本比例：{np.mean(y_train)*100:.1f}%")
    
    # 训练神经网络
    log(f"\n📈 训练神经网络...")
    
    models = []
    seeds = [42, 123, 456, 789, 1024]
    
    for i, seed in enumerate(seeds):
        log(f"\n训练模型 {i+1}/5 (seed={seed})...")
        
        model = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            alpha=0.001,
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=200,
            random_state=seed,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=20
        )
        
        model.fit(X_train, y_train)
        
        # 评估
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_pred_proba)
        
        log(f"  AUC: {auc:.4f}")
        
        models.append({
            'model': model,
            'auc': auc,
            'seed': seed
        })
    
    # 保存模型
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    MODEL_DIR.mkdir(exist_ok=True)
    
    avg_auc = np.mean([m['auc'] for m in models])
    std_auc = np.std([m['auc'] for m in models])
    
    log(f"\n{'='*70}")
    log("💾 保存模型")
    log(f"{'='*70}")
    
    for i, m in enumerate(models, 1):
        model_path = MODEL_DIR / f"ml_nn_v10_model{i}_seed{m['seed']}_{timestamp}.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(m, f)
        log(f"保存：{model_path.name}")
    
    # 保存配置
    config = {
        'version': 'V10_right_side',
        'train_date': timestamp,
        'n_features': len(V10_FEATURES),
        'features': V10_FEATURES,
        'n_models': len(models),
        'seeds': seeds,
        'train_samples': len(X_train),
        'positive_ratio': float(np.mean(y_train)),
        'label_threshold': FUTURE_RETURN_THRESHOLD,
        'forecast_period': FORECAST_PERIOD,
        'strategy': 'right_side_trend_following',
        'avg_auc': avg_auc,
        'std_auc': std_auc,
        'model_paths': [f"ml_nn_v10_model{i}_seed{seeds[i-1]}_{timestamp}.pkl" for i in range(1, len(seeds)+1)]
    }
    
    config_path = MODEL_DIR / f"ml_nn_v10_config_{timestamp}.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    log(f"保存配置：{config_path.name}")
    
    log(f"\n{'='*70}")
    log("✅ V10 训练完成")
    log(f"{'='*70}")
    log(f"平均 AUC: {avg_auc:.4f} ± {std_auc:.4f}")
    log(f"训练样本：{len(X_train)}")
    log(f"正样本比例：{np.mean(y_train)*100:.1f}%")
    log(f"\n下一步:")
    log(f"  1. 使用 v10_selector.py 进行实盘选股测试")
    log(f"  2. 观察高置信度样本数量和分布")
    log(f"  3. 对比 V9 和 V10 的选股效果")
    log(f"{'='*70}\n")

if __name__ == "__main__":
    train_v10()
