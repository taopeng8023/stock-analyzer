#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 模型重新校准脚本
使用最近 3 个月数据微调模型 + 概率校准
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import random
import warnings
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import CalibratedClassifierCV
warnings.filterwarnings('ignore')

# 配置
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
DATA_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
LOG_FILE = Path("/Users/taopeng/.openclaw/workspace/stocks/ml_nn_v8_calibrate.log")

# V8 特征列表
V8_FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
    'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
    'momentum10', 'vol_change', 'price_position',
    'volatility_rank', 'recent_return', 'acceleration',
    'up_days_ratio', 'momentum_strength',
    'vol_price_corr', 'vol_trend', 'momentum_accel', 'trend_strength',
    'volatility_trend', 'range_ratio', 'money_flow_proxy', 'money_flow_ma'
]

def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_and_prepare_stock(stock_file, min_records=100):
    """加载单只股票并计算 V8 特征"""
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
        
        # 构建 DataFrame
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
        
        # 计算特征 (与训练一致)
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
        
        df['recent_return'] = df['close'].pct_change(3)
        df['acceleration'] = df['recent_return'] - df['recent_return'].shift(3)
        df['volatility_rank'] = df['volatility5'].rolling(60).rank(pct=True)
        df['up_days_ratio'] = (df['pct_chg'] > 0).rolling(10).mean()
        df['momentum_strength'] = (df['ret5'] - df['ret10']).clip(-0.5, 0.5)
        
        df['vol_price_corr'] = df['vol'].rolling(20).corr(df['close']).fillna(0).clip(-1, 1)
        df['vol_trend'] = (df['vol_ma5'] / (df['vol'].rolling(20).mean() + 1e-10)).clip(0.5, 2.0)
        df['momentum_accel'] = (df['ret5'] - df['ret5'].shift(5)).clip(-0.5, 0.5)
        df['trend_strength'] = (df['ma5'] - df['ma20']) / (df['ma20'] + 1e-10)
        df['volatility_trend'] = (df['volatility5'] / (df['volatility5'].shift(5) + 1e-10)).clip(0.5, 2.0)
        df['range_ratio'] = (df['high'] - df['low']) / (df['close'] + 1e-10)
        df['money_flow_proxy'] = (df['vol'] * df['pct_chg'] / 1e6).clip(-100, 100)
        df['money_flow_ma'] = df['money_flow_proxy'].rolling(5).mean()
        
        # 标签：未来 5 天涨超 5%
        df['future_return_5d'] = df['close'].shift(-5) / df['close'] - 1
        df['label'] = (df['future_return_5d'] > 0.05).astype(int)
        
        # 删除 NaN
        df = df.dropna(subset=V8_FEATURES + ['label'])
        
        if len(df) < 50:
            return None
        
        return df[V8_FEATURES + ['label', 'date']]
    
    except Exception as e:
        return None

def prepare_recent_data(n_stocks=500):
    """准备最近 3 个月数据"""
    log(f"\n准备最近 3 个月数据...")
    
    stock_files = list(DATA_DIR.glob('*.json'))
    selected_files = random.sample(stock_files, min(n_stocks, len(stock_files)))
    
    all_data = []
    
    for idx, stock_file in enumerate(selected_files):
        if (idx + 1) % 100 == 0:
            log(f"已加载 {idx+1}/{len(selected_files)} 只股票...")
        
        df = load_and_prepare_stock(stock_file)
        if df is not None:
            all_data.append(df)
    
    if not all_data:
        return None, None
    
    combined = pd.concat(all_data, ignore_index=True)
    
    # 只保留最近 3 个月数据
    combined['date'] = pd.to_datetime(combined['date'], format='%Y%m%d')
    cutoff_date = combined['date'].max() - timedelta(days=90)
    recent_data = combined[combined['date'] >= cutoff_date].copy()
    
    log(f"\n数据准备完成:")
    log(f"  总样本数：{len(combined):,}")
    log(f"  最近 3 个月：{len(recent_data):,} ({len(recent_data)/len(combined)*100:.1f}%)")
    log(f"  正样本比例：{recent_data['label'].mean()*100:.1f}%")
    log(f"  日期范围：{recent_data['date'].min().strftime('%Y-%m-%d')} ~ {recent_data['date'].max().strftime('%Y-%m-%d')}")
    
    X = recent_data[V8_FEATURES].values
    y = recent_data['label'].values
    
    return X, y

def calibrate_models(X, y):
    """校准模型概率"""
    log(f"\n{'='*60}")
    log("模型概率校准")
    log(f"{'='*60}")
    
    # 加载原有模型
    model_names = [
        'ml_nn_v8_model1_seed42.pkl',
        'ml_nn_v8_model2_seed123.pkl',
        'ml_nn_v8_model3_seed456.pkl',
        'ml_nn_v8_model4_seed789.pkl',
        'ml_nn_v8_model5_seed1024.pkl'
    ]
    
    calibrated_models = []
    
    for i, model_name in enumerate(model_names):
        model_path = MODEL_DIR / model_name
        log(f"\n校准模型 {i+1}/5: {model_name}")
        
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        
        base_model = data['model']
        
        # 使用 Isotonic Regression 校准
        calibrator = IsotonicRegression(out_of_bounds='clip')
        
        # 获取原模型预测
        raw_probs = base_model.predict_proba(X)[:, 1]
        
        # 拟合校准器
        calibrator.fit(raw_probs, y)
        
        # 保存校准后的模型
        calibrated_model = {
            'base_model': base_model,
            'calibrator': calibrator,
            'seed': data.get('seed', i),
            'val_auc': data.get('val_auc', 0.0)
        }
        
        calibrated_models.append(calibrated_model)
        
        # 验证校准效果
        calibrated_probs = calibrator.predict(raw_probs)
        log(f"  原概率范围：[{raw_probs.min():.3f}, {raw_probs.max():.3f}]")
        log(f"  校准后范围：[{calibrated_probs.min():.3f}, {calibrated_probs.max():.3f}]")
        log(f"  高置信度样本：{sum(calibrated_probs >= 0.9)} ({sum(calibrated_probs >= 0.9)/len(calibrated_probs)*100:.1f}%)")
    
    return calibrated_models

def save_calibrated_models(calibrated_models):
    """保存校准后的模型"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for i, cal_model in enumerate(calibrated_models):
        save_path = MODEL_DIR / f'ml_nn_v8_calibrated_model{i+1}_seed{cal_model["seed"]}_{timestamp}.pkl'
        
        with open(save_path, 'wb') as f:
            pickle.dump(cal_model, f)
        
        log(f"保存校准模型 {i+1}: {save_path.name}")
    
    # 保存配置
    config = {
        'calibration_method': 'isotonic_regression',
        'calibration_date': timestamp,
        'n_features': len(V8_FEATURES),
        'model_paths': [f'ml_nn_v8_calibrated_model{i+1}_seed{cal_model["seed"]}_{timestamp}.pkl' 
                       for i, cal_model in enumerate(calibrated_models)]
    }
    
    config_path = MODEL_DIR / f'ml_nn_v8_calibrated_config_{timestamp}.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    log(f"\n保存配置文件：{config_path.name}")
    
    return config

def main():
    """主函数"""
    log(f"\n{'='*60}")
    log("V8 模型重新校准 - 方案 3")
    log(f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*60}")
    
    # 准备数据
    X, y = prepare_recent_data(n_stocks=500)
    
    if X is None or len(X) == 0:
        log("\n❌ 数据准备失败")
        return
    
    # 校准模型
    calibrated_models = calibrate_models(X, y)
    
    # 保存模型
    config = save_calibrated_models(calibrated_models)
    
    log(f"\n{'='*60}")
    log("✅ 校准完成")
    log(f"{'='*60}")
    log(f"\n使用方法:")
    log(f"  1. 加载校准模型: ml_nn_v8_calibrated_model*_seed*_{config['calibration_date']}.pkl")
    log(f"  2. 预测时先调用 base_model.predict_proba(), 再用 calibrator.predict() 校准")
    log(f"  3. 或使用 v8_calibrated_selector.py 进行选股")
    
    log(f"\n💡 建议:")
    log(f"  - 校准后重新运行选股，观察置信度分布")
    log(f"  - 如效果仍不理想，考虑使用最近 3 个月数据微调训练")

if __name__ == '__main__':
    main()
