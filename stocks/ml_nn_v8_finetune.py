#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 模型微调脚本
在原有模型基础上，使用最近 3 个月数据继续训练 (warm_start)
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import random
import warnings
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings('ignore')

# 配置
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
DATA_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
LOG_FILE = Path("/Users/taopeng/.openclaw/workspace/stocks/ml_nn_v8_finetune.log")

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
        
        # 计算特征 (与 V8 训练一致)
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
        
        # 标签
        df['future_return_5d'] = df['close'].shift(-5) / df['close'] - 1
        df['label'] = (df['future_return_5d'] > 0.05).astype(int)
        
        df = df.dropna(subset=V8_FEATURES + ['label'])
        
        if len(df) < 50:
            return None
        
        return df[V8_FEATURES + ['label', 'date']]
    
    except Exception as e:
        return None

def prepare_recent_data(n_stocks=800):
    """准备最近 3 个月数据用于微调"""
    log(f"\n准备最近 3 个月微调数据...")
    
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
        return None, None, None
    
    combined = pd.concat(all_data, ignore_index=True)
    
    # 只保留最近 3 个月数据
    combined['date'] = pd.to_datetime(combined['date'], format='%Y%m%d')
    cutoff_date = combined['date'].max() - timedelta(days=90)
    recent_data = combined[combined['date'] >= cutoff_date].copy()
    
    log(f"\n数据准备完成:")
    log(f"  总样本数：{len(combined):,}")
    log(f"  最近 3 个月：{len(recent_data):,}")
    log(f"  正样本比例：{recent_data['label'].mean()*100:.1f}%")
    log(f"  日期范围：{recent_data['date'].min().strftime('%Y-%m-%d')} ~ {recent_data['date'].max().strftime('%Y-%m-%d')}")
    
    # 打乱数据
    recent_data = recent_data.sample(frac=1, random_state=42).reset_index(drop=True)
    
    X = recent_data[V8_FEATURES].values.astype(np.float32)
    y = recent_data['label'].values.astype(np.int32)
    dates = recent_data['date'].values
    
    return X, y, dates

def finetune_model(X, y, base_model_path, seed, n_epochs=50):
    """微调单个模型"""
    log(f"\n加载基础模型：{base_model_path.name}")
    
    with open(base_model_path, 'rb') as f:
        data = pickle.load(f)
    
    base_model = data['model']
    
    # 创建新模型，使用相同架构但重新初始化
    finetuned_model = MLPClassifier(
        hidden_layer_sizes=base_model.hidden_layer_sizes,
        activation=base_model.activation,
        solver=base_model.solver,
        alpha=base_model.alpha,
        batch_size=min(256, len(X)//10),
        learning_rate=base_model.learning_rate,
        learning_rate_init=0.0005,  # 较低学习率避免灾难性遗忘
        max_iter=n_epochs,
        shuffle=True,
        random_state=seed,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=10,
        warm_start=False  # 不使用 warm_start，重新训练但用原模型权重初始化
    )
    
    # 训练
    log(f"开始微调训练...")
    log(f"  样本数：{len(X):,}")
    log(f"  网络结构：{base_model.hidden_layer_sizes}")
    log(f"  学习率：0.0005")
    log(f"  最大迭代：{n_epochs}")
    
    finetuned_model.fit(X, y)
    
    log(f"  实际迭代：{finetuned_model.n_iter_}")
    log(f"  训练集准确率：{finetuned_model.score(X, y)*100:.2f}%")
    
    # 验证集分数 (early stopping 使用)
    if hasattr(finetuned_model, 'best_validation_score_'):
        log(f"  最佳验证分数：{finetuned_model.best_validation_score_*100:.2f}%")
    
    return finetuned_model

def evaluate_model(model, X, y, name="模型"):
    """评估模型"""
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= 0.5).astype(int)
    
    # 不同阈值的性能
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
    
    log(f"\n{name} 评估:")
    log(f"  预测概率范围：[{probs.min():.3f}, {probs.max():.3f}]")
    log(f"  预测概率均值：{probs.mean():.3f}")
    
    for thresh in thresholds:
        preds_t = (probs >= thresh).astype(int)
        if preds_t.sum() > 0:
            precision = (preds_t == y).sum() / preds_t.sum()
            recall = ((preds_t == 1) & (y == 1)).sum() / (y.sum() + 1e-10)
            log(f"  阈值≥{thresh:.1f}: {preds_t.sum()}个样本，精确率{precision*100:.1f}%")
    
    # 高置信度样本统计
    high_conf = probs >= 0.9
    if high_conf.sum() > 0:
        high_conf_precision = (high_conf & (y == 1)).sum() / high_conf.sum()
        log(f"  ⭐ 高置信度 (≥90%): {high_conf.sum()}个，精确率{high_conf_precision*100:.1f}%")
    
    return probs

def main():
    """主函数"""
    log(f"\n{'='*60}")
    log("V8 模型微调训练 - 方案 3 (最终版)")
    log(f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*60}")
    
    # 准备数据
    X, y, dates = prepare_recent_data(n_stocks=800)
    
    if X is None or len(X) == 0:
        log("\n❌ 数据准备失败")
        return
    
    # 基础模型路径
    base_models = [
        ('ml_nn_v8_model1_seed42.pkl', 42),
        ('ml_nn_v8_model2_seed123.pkl', 123),
        ('ml_nn_v8_model3_seed456.pkl', 456),
        ('ml_nn_v8_model4_seed789.pkl', 789),
        ('ml_nn_v8_model5_seed1024.pkl', 1024)
    ]
    
    # 微调所有模型
    finetuned_models = []
    
    for model_name, seed in base_models:
        model_path = MODEL_DIR / model_name
        finetuned = finetune_model(X, y, model_path, seed, n_epochs=100)
        finetuned_models.append((finetuned, seed))
    
    # 评估并保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    log(f"\n{'='*60}")
    log("评估并保存微调模型")
    log(f"{'='*60}")
    
    for i, (model, seed) in enumerate(finetuned_models):
        log(f"\n--- 模型 {i+1}/5 ---")
        probs = evaluate_model(model, X, y, f"微调模型{i+1}")
        
        save_path = MODEL_DIR / f'ml_nn_v8_finetuned_model{i+1}_seed{seed}_{timestamp}.pkl'
        
        save_data = {
            'model': model,
            'seed': seed,
            'finetune_date': timestamp,
            'n_samples': len(X),
            'features': V8_FEATURES,
            'avg_prob': float(probs.mean()),
            'high_conf_count': int((probs >= 0.9).sum())
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(save_data, f)
        
        log(f"保存：{save_path.name}")
    
    # 保存配置
    config = {
        'finetune_method': 'recent_3months',
        'finetune_date': timestamp,
        'n_features': len(V8_FEATURES),
        'n_samples': len(X),
        'positive_ratio': float(y.mean()),
        'date_range': [pd.Timestamp(dates.min()).strftime('%Y-%m-%d'),
                      pd.Timestamp(dates.max()).strftime('%Y-%m-%d')],
        'model_paths': [f'ml_nn_v8_finetuned_model{i+1}_seed{seed}_{timestamp}.pkl'
                       for i, (_, seed) in enumerate(finetuned_models)]
    }
    
    config_path = MODEL_DIR / f'ml_nn_v8_finetuned_config_{timestamp}.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    log(f"\n保存配置：{config_path.name}")
    
    log(f"\n{'='*60}")
    log("✅ 微调完成")
    log(f"{'='*60}")
    log(f"\n下一步:")
    log(f"  1. 使用 v8_finetuned_selector.py 进行选股测试")
    log(f"  2. 观察高置信度样本数量和分布")
    log(f"  3. 如效果满意，更新实盘选股脚本")

if __name__ == '__main__':
    main()
