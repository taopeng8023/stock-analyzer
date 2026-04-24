#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股模型 V4 - 简化增强版

基于现有数据格式优化:
- 使用 data_history_2022_2026 目录的 JSON 数据
- 更深的网络 (128-64-32)
- 更好的正则化
- 类别平衡
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import time
import pickle
import gc
import sys
from datetime import datetime
import random

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

DATA_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026')
MODEL_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/models')
LOG_FILE = Path('/Users/taopeng/.openclaw/workspace/stocks/ml_train_neural_v4.log')

def log(msg):
    print(msg)
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_and_prepare_stock(stock_file, min_records=100):
    """加载单只股票并计算特征"""
    try:
        with open(stock_file, 'r') as f:
            data = json.load(f)
        
        items = data.get('items', [])
        if len(items) < min_records:
            return None
        
        # 字段映射
        fields = data.get('fields', [])
        idx_map = {name: i for i, name in enumerate(fields)}
        
        # 必需字段
        required = ['trade_date', 'close', 'open', 'high', 'low', 'vol', 'pct_chg']
        if not all(r in idx_map for r in required):
            return None
        
        # 转换为 DataFrame
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
        
        # 计算技术指标
        # MA
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        # 价格位置
        df['p_ma5'] = (df['close'] - df['ma5']) / df['ma5']
        df['p_ma10'] = (df['close'] - df['ma10']) / df['ma10']
        df['p_ma20'] = (df['close'] - df['ma20']) / df['ma20']
        
        # 均线斜率
        df['ma5_slope'] = df['ma5'].pct_change(5)
        df['ma10_slope'] = df['ma10'].pct_change(5)
        
        # 收益率
        df['ret5'] = df['close'].pct_change(5)
        df['ret10'] = df['close'].pct_change(10)
        
        # RSI (简化版)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - 100 / (1 + rs)
        
        # 成交量比率
        df['vol_ma5'] = df['vol'].rolling(5).mean()
        df['vol_ratio'] = df['vol'] / (df['vol_ma5'] + 1e-10)
        
        # 布林带位置
        df['ma20_roll'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['boll_upper'] = df['ma20_roll'] + 2 * df['std20']
        df['boll_lower'] = df['ma20_roll'] - 2 * df['std20']
        df['boll_pos'] = (df['close'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'] + 1e-10)
        
        # MACD (简化)
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_hist'] = df['macd'] - df['macd'].ewm(span=9, adjust=False).mean()
        
        # KDJ (简化)
        low_9 = df['low'].rolling(9).min()
        high_9 = df['high'].rolling(9).max()
        df['kdj_k'] = 100 * (df['close'] - low_9) / (high_9 - low_9 + 1e-10)
        
        # 标签：未来 5 天涨幅是否超过 3%
        df['future_return'] = df['close'].shift(-5) / df['close'] - 1
        df['label'] = (df['future_return'] > 0.03).astype(int)
        
        # 删除 NaN
        feature_cols = ['p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
                       'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos']
        df = df.dropna(subset=feature_cols + ['label'])
        
        if len(df) < 50:
            return None
        
        return df[feature_cols + ['label']]
    
    except Exception as e:
        return None

def main():
    # 清空日志
    with open(LOG_FILE, 'w') as f:
        f.write(f'训练日志 V4 - {datetime.now()}\n\n')
    
    log('='*60)
    log('神经网络选股模型 V4 - 简化增强版')
    log('='*60)
    
    start_time = time.time()
    
    # 扫描数据文件
    stock_files = list(DATA_DIR.glob('*.json'))
    log(f'发现 {len(stock_files):,} 只股票数据')
    
    # 随机选择部分股票
    n_stocks = min(1500, len(stock_files))
    selected_files = random.sample(stock_files, n_stocks)
    log(f'选择 {n_stocks} 只股票进行训练')
    
    # 分批加载
    all_dfs = []
    batch_size = 300
    
    for i, stock_file in enumerate(selected_files):
        df = load_and_prepare_stock(stock_file)
        if df is None:
            continue
        
        all_dfs.append(df)
        
        if (i + 1) % batch_size == 0:
            log(f'已加载 {i+1}/{n_stocks} 只股票，累计 {sum(len(d) for d in all_dfs):,} 条样本')
            gc.collect()
    
    log(f'\n合并数据...')
    combined = pd.concat(all_dfs, ignore_index=True)
    log(f'总样本数：{len(combined):,}')
    log(f'正样本比例：{combined["label"].mean()*100:.1f}%')
    
    # 采样平衡
    positives = combined[combined['label'] == 1]
    negatives = combined[combined['label'] == 0]
    
    n_pos = min(len(positives), 200000)
    n_neg = min(len(negatives), 400000)
    
    pos_sample = positives.sample(n=n_pos, random_state=42)
    neg_sample = negatives.sample(n=n_neg, random_state=42)
    
    sampled = pd.concat([pos_sample, neg_sample], ignore_index=True)
    sampled = sampled.sample(frac=1, random_state=42).reset_index(drop=True)
    
    log(f'采样后：{len(sampled):,} 条 (正样本：{sampled["label"].mean()*100:.1f}%)')
    
    del combined, all_dfs, positives, negatives
    gc.collect()
    
    # 准备数据
    feature_cols = ['p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
                   'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos']
    
    log('准备数据...')
    X = sampled[feature_cols].values.astype(np.float32)
    y = sampled['label'].values
    
    del sampled
    gc.collect()
    
    log(f'特征矩阵：{X.shape}')
    log(f'特征内存：{X.nbytes / 1024**2:.1f}MB')
    
    # 划分
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    del X, y
    gc.collect()
    
    log(f'训练集：{len(X_train):,}')
    log(f'测试集：{len(X_test):,}')
    
    # 标准化
    log('标准化...')
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    
    del X_train
    gc.collect()
    
    # 训练网络
    log('='*60)
    log('训练神经网络...')
    log('='*60)
    
    model = MLPClassifier(
        hidden_layer_sizes=(128, 64, 32),  # 三层网络
        activation='relu',
        solver='adam',
        alpha=0.001,  # L2 正则化
        batch_size=256,
        learning_rate='adaptive',
        learning_rate_init=0.001,
        max_iter=100,
        random_state=42,
        verbose=True,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=10
    )
    
    train_start = time.time()
    model.fit(X_train_s, y_train)
    train_time = time.time() - train_start
    
    log(f'\n训练完成：{train_time:.0f}s')
    log(f'迭代次数：{model.n_iter_}')
    log(f'最终损失：{model.loss_:.4f}')
    
    # 评估
    y_prob = model.predict_proba(X_test_s)[:, 1]
    y_pred = model.predict(X_test_s)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    
    log('='*60)
    log('评估结果')
    log('='*60)
    log(f'准确率：{acc:.4f}')
    log(f'精确率：{prec:.4f}')
    log(f'召回率：{rec:.4f}')
    log(f'F1: {f1:.4f}')
    log(f'AUC: {auc:.4f}')
    
    # 不同阈值的精确率
    log('\n| 阈值 | 覆盖 | 精确率 |')
    best_threshold = 0.5
    best_prec = 0
    for threshold in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        high_conf = (y_prob >= threshold).sum()
        if high_conf > 0:
            conf_prec = precision_score(y_test, y_prob >= threshold, zero_division=0)
            log(f'| {int(threshold*100)}% | {high_conf} | {conf_prec:.4f} |')
            if conf_prec > best_prec and high_conf >= 50:
                best_prec = conf_prec
                best_threshold = threshold
    
    log(f'\n最佳阈值：{int(best_threshold*100)}% (精确率：{best_prec:.4f})')
    
    # 保存模型
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_path = MODEL_DIR / f'ml_nn_v4_{timestamp}.pkl'
    
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': feature_cols,
            'auc': auc,
            'best_threshold': best_threshold,
            'best_prec': best_prec
        }, f)
    
    log(f'\n模型已保存：{model_path}')
    log('='*60)
    log(f'总耗时：{time.time() - start_time:.0f}s')
    log(f'完成时间：{datetime.now()}')
    log('='*60)

if __name__ == '__main__':
    main()
