#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V9 市场自适应模型训练
针对当前市场风格 (2025-10~2026-04) 重新训练

核心优化：
1. 使用最近 6 个月数据 (而非 2022-2025)
2. 调整标签定义：涨超 2% 即为正样本 (原 3%)
3. 增加市场状态特征
4. 使用相对排名而非绝对置信度阈值
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import gc
warnings.filterwarnings('ignore')

# 配置
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
DATA_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
LOG_FILE = Path("/Users/taopeng/.openclaw/workspace/stocks/ml_nn_v9_market_adapt.log")

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

# 新增市场状态特征
MARKET_FEATURES = [
    'market_rsi',  # 市场整体 RSI
    'market_trend',  # 市场趋势 (上涨股票比例)
    'volatility_state'  # 波动率状态
]

V9_FEATURES = V8_FEATURES + MARKET_FEATURES

def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def load_and_prepare_stock(stock_file, min_records=100, cutoff_date=None):
    """加载单只股票并计算 V9 特征"""
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
        
        # 日期过滤 (只保留最近 6 个月)
        df['date_dt'] = pd.to_datetime(df['date'], format='%Y%m%d')
        if cutoff_date:
            df = df[df['date_dt'] >= cutoff_date].copy()
        
        if len(df) < 80:  # 至少 80 个交易日
            return None
        
        # 计算基础特征 (与 V8 一致)
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
        
        # 新增市场状态特征 (简化版：用个股代理)
        # 实际应该用全市场数据计算，这里用简化版本
        df['market_rsi'] = df['rsi'].rolling(20).mean()  # 平滑 RSI 代理市场状态
        df['market_trend'] = (df['pct_chg'] > 0).rolling(20).mean()  # 上涨比例
        df['volatility_state'] = df['volatility5'].rolling(20).rank(pct=True)
        
        # 标签：未来 5 天涨超 2% (降低阈值适应当前市场)
        df['future_return_5d'] = df['close'].shift(-5) / df['close'] - 1
        df['label'] = (df['future_return_5d'] > 0.02).astype(int)  # 2% 阈值
        
        # 删除 NaN
        df = df.dropna(subset=V9_FEATURES + ['label'])
        
        if len(df) < 50:
            return None
        
        return df[V9_FEATURES + ['label', 'date']]
    
    except Exception as e:
        return None

def prepare_recent_data(n_stocks=1500):
    """准备最近 6 个月数据"""
    log(f"\n{'='*60}")
    log("准备最近 6 个月训练数据")
    log(f"{'='*60}")
    
    # 最近 6 个月起始日期
    cutoff_date = datetime.now() - timedelta(days=180)
    cutoff_date = pd.Timestamp(cutoff_date)
    
    log(f"\n数据时间范围：{cutoff_date.strftime('%Y-%m-%d')} ~ 至今")
    
    stock_files = list(DATA_DIR.glob('*.json'))
    selected_files = random.sample(stock_files, min(n_stocks, len(stock_files)))
    
    all_data = []
    
    for idx, stock_file in enumerate(selected_files):
        if (idx + 1) % 100 == 0:
            log(f"已加载 {idx+1}/{len(selected_files)} 只股票...")
        
        df = load_and_prepare_stock(stock_file, cutoff_date=cutoff_date)
        if df is not None:
            all_data.append(df)
    
    if not all_data:
        return None, None
    
    combined = pd.concat(all_data, ignore_index=True)
    
    log(f"\n数据准备完成:")
    log(f"  总样本数：{len(combined):,}")
    log(f"  正样本比例：{combined['label'].mean()*100:.1f}%")
    log(f"  特征维度：{len(V9_FEATURES)}")
    
    # 检查正样本比例
    pos_ratio = combined['label'].mean()
    if pos_ratio < 0.20:
        log(f"\n⚠️  警告：正样本比例 {pos_ratio*100:.1f}% 偏低")
        log(f"  考虑降低标签阈值或使用不同策略")
    
    # 打乱数据
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)
    
    X = combined[V9_FEATURES].values.astype(np.float32)
    y = combined['label'].values.astype(np.int32)
    
    return X, y

def train_ensemble(X, y, n_models=5):
    """训练集成模型"""
    log(f"\n{'='*60}")
    log(f"训练 V9 集成模型 (5 个)")
    log(f"{'='*60}")
    
    # 划分训练/验证集
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    log(f"\n训练集：{len(X_train):,} 样本")
    log(f"验证集：{len(X_val):,} 样本")
    log(f"正样本比例：{y_train.mean()*100:.1f}%")
    
    models = []
    seeds = [42, 123, 456, 789, 1024]
    
    for i, seed in enumerate(seeds):
        log(f"\n--- 模型 {i+1}/{n_models} (seed={seed}) ---")
        
        # 神经网络
        model = MLPClassifier(
            hidden_layer_sizes=(256, 128, 64),
            activation='relu',
            solver='adam',
            alpha=0.001,
            batch_size=256,
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=200,
            shuffle=True,
            random_state=seed,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=15,
            verbose=False
        )
        
        log(f"开始训练...")
        model.fit(X_train, y_train)
        
        # 评估
        train_score = model.score(X_train, y_train)
        val_score = model.score(X_val, y_val)
        
        log(f"  训练集准确率：{train_score*100:.2f}%")
        log(f"  验证集准确率：{val_score*100:.2f}%")
        log(f"  实际迭代：{model.n_iter_}")
        
        # 验证集预测分析
        val_probs = model.predict_proba(X_val)[:, 1]
        
        # 不同阈值的精确率
        for thresh in [0.5, 0.6, 0.7, 0.8, 0.9]:
            preds = (val_probs >= thresh).astype(int)
            if preds.sum() > 0:
                precision = (preds == y_val).sum() / preds.sum()
                log(f"  阈值≥{thresh:.1f}: {preds.sum()}个，精确率{precision*100:.1f}%")
        
        models.append(model)
        
        gc.collect()
    
    return models, seeds

def evaluate_ensemble(models, X_val, y_val):
    """评估集成模型"""
    log(f"\n{'='*60}")
    log("集成模型评估")
    log(f"{'='*60}")
    
    # 集成预测 (平均)
    all_probs = []
    for model in models:
        probs = model.predict_proba(X_val)[:, 1]
        all_probs.append(probs)
    
    avg_probs = np.mean(all_probs, axis=0)
    
    log(f"\n预测概率分布:")
    log(f"  最小值：{avg_probs.min():.3f}")
    log(f"  最大值：{avg_probs.max():.3f}")
    log(f"  平均值：{avg_probs.mean():.3f}")
    log(f"  中位数：{np.median(avg_probs):.3f}")
    
    # 不同阈值的性能
    log(f"\n不同阈值性能:")
    for thresh in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]:
        preds = (avg_probs >= thresh).astype(int)
        if preds.sum() > 0:
            precision = (preds == y_val).sum() / preds.sum()
            recall = ((preds == 1) & (y_val == 1)).sum() / (y_val.sum() + 1e-10)
            log(f"  ≥{thresh:.2f}: {preds.sum()}个 ({preds.sum()/len(preds)*100:.1f}%), "
                f"精确率{precision*100:.1f}%, 召回率{recall*100:.1f}%")
    
    # 高置信度样本
    high_conf_90 = avg_probs >= 0.9
    high_conf_85 = avg_probs >= 0.85
    high_conf_80 = avg_probs >= 0.80
    
    log(f"\n高置信度样本:")
    log(f"  ≥90%: {high_conf_90.sum()}个 ({high_conf_90.sum()/len(high_conf_90)*100:.1f}%)")
    log(f"  ≥85%: {high_conf_85.sum()}个 ({high_conf_85.sum()/len(high_conf_85)*100:.1f}%)")
    log(f"  ≥80%: {high_conf_80.sum()}个 ({high_conf_80.sum()/len(high_conf_80)*100:.1f}%)")
    
    if high_conf_90.sum() > 0:
        precision_90 = (high_conf_90 & (y_val == 1)).sum() / high_conf_90.sum()
        log(f"  ≥90% 精确率：{precision_90*100:.1f}%")
    
    return avg_probs

def save_models(models, seeds, X, y):
    """保存模型"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    log(f"\n{'='*60}")
    log("保存模型")
    log(f"{'='*60}")
    
    for i, model in enumerate(models):
        save_path = MODEL_DIR / f'ml_nn_v9_model{i+1}_seed{seeds[i]}_{timestamp}.pkl'
        
        save_data = {
            'model': model,
            'seed': seeds[i],
            'features': V9_FEATURES,
            'train_samples': len(X),
            'train_date': timestamp,
            'label_threshold': 0.02,  # 2% 阈值
            'data_period': '6_months'
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(save_data, f)
        
        log(f"保存：{save_path.name}")
    
    # 保存配置
    config = {
        'version': 'V9_market_adapt',
        'train_date': timestamp,
        'n_features': len(V9_FEATURES),
        'features': V9_FEATURES,
        'n_models': len(models),
        'seeds': seeds,
        'train_samples': len(X),
        'positive_ratio': float(y.mean()),
        'label_threshold': 0.02,
        'data_period': 'recent_6_months',
        'model_paths': [f'ml_nn_v9_model{i+1}_seed{seeds[i]}_{timestamp}.pkl' 
                       for i in range(len(models))]
    }
    
    config_path = MODEL_DIR / f'ml_nn_v9_config_{timestamp}.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    log(f"\n保存配置：{config_path.name}")
    
    return config

def main():
    """主函数"""
    log(f"\n{'='*60}")
    log("V9 市场自适应模型训练")
    log(f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*60}")
    
    log(f"\n优化要点:")
    log(f"  1. 使用最近 6 个月数据 (适应当前市场)")
    log(f"  2. 标签阈值：涨超 2% 即为正 (原 3%)")
    log(f"  3. 新增市场状态特征 (3 个)")
    log(f"  4. 5 模型集成提高稳定性")
    
    # 准备数据
    X, y = prepare_recent_data(n_stocks=1500)
    
    if X is None or len(X) == 0:
        log("\n❌ 数据准备失败")
        return
    
    # 训练集成模型
    models, seeds = train_ensemble(X, y, n_models=5)
    
    # 评估
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    avg_probs = evaluate_ensemble(models, X_val, y_val)
    
    # 保存
    config = save_models(models, seeds, X, y)
    
    log(f"\n{'='*60}")
    log("✅ V9 训练完成")
    log(f"{'='*60}")
    log(f"\n下一步:")
    log(f"  1. 使用 v9_selector.py 进行实盘选股测试")
    log(f"  2. 观察高置信度样本数量和分布")
    log(f"  3. 对比 V8 和 V9 的选股效果")
    
    log(f"\n💡 关键改进:")
    log(f"  - 正样本比例：{y.mean()*100:.1f}% (目标>25%)")
    log(f"  - 如仍偏低，考虑进一步降低标签阈值或使用其他策略")

if __name__ == '__main__':
    main()
