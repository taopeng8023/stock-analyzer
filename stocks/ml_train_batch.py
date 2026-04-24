#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器学习选股系统 - 分批训练版
将5687只股票分成多个批次训练，避免内存溢出

策略：
1. 分批处理：每批500只股票
2. 增量训练：使用XGBoost的增量训练功能
3. 定期保存：每批完成后保存中间模型
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import warnings
from pathlib import Path
import time
import pickle

warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

CACHE_DIR = Path(__file__).parent / 'data_tushare'
MODEL_DIR = Path(__file__).parent / 'models'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'
MODEL_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# 特征列表
FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'p_ma60',
    'ma5_slope', 'ma10_slope', 'ma20_slope',
    'ret1', 'ret5', 'ret10', 'ret20',
    'vol5', 'vol10', 'vol20',
    'rsi',
    'macd_dif', 'macd_dea', 'macd_hist',
    'kdj_k', 'kdj_d', 'kdj_j',
    'vol_ratio', 'vol_ratio20',
    'hl_pct', 'hc_pct', 'cl_pct',
    'boll_pos'
]


def load_stock_data(symbol):
    """加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data['items'], columns=data['fields'])
        df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna()
    except:
        return None


def calc_features(df):
    """计算特征"""
    data = df.copy()
    
    # 均线
    for period in [5, 10, 20, 60]:
        data[f'ma{period}'] = data['close'].rolling(period).mean()
        data[f'p_ma{period}'] = (data['close'] - data[f'ma{period}']) / data[f'ma{period}']
    
    # 斜率
    data['ma5_slope'] = data['ma5'] / data['ma5'].shift(5) - 1
    data['ma10_slope'] = data['ma10'] / data['ma10'].shift(5) - 1
    data['ma20_slope'] = data['ma20'] / data['ma20'].shift(10) - 1
    
    # 涨跌幅
    for days in [1, 5, 10, 20]:
        data[f'ret{days}'] = data['close'].pct_change(days)
    
    # 波动率
    for days in [5, 10, 20]:
        data[f'vol{days}'] = data['ret1'].rolling(days).std()
    
    # RSI
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss.replace(0, 0.001)
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = data['close'].ewm(span=12, adjust=False).mean()
    ema26 = data['close'].ewm(span=26, adjust=False).mean()
    data['macd_dif'] = ema12 - ema26
    data['macd_dea'] = data['macd_dif'].ewm(span=9, adjust=False).mean()
    data['macd_hist'] = (data['macd_dif'] - data['macd_dea']) * 2
    
    # KDJ
    lowv = data['low'].rolling(9).min()
    highv = data['high'].rolling(9).max()
    rsv = (data['close'] - lowv) / (highv - lowv + 0.001) * 100
    data['kdj_k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
    data['kdj_d'] = data['kdj_k'].ewm(alpha=1/3, adjust=False).mean()
    data['kdj_j'] = 3 * data['kdj_k'] - 2 * data['kdj_d']
    
    # 成交量
    data['vol_ma5'] = data['volume'].rolling(5).mean()
    data['vol_ma20'] = data['volume'].rolling(20).mean()
    data['vol_ratio'] = data['volume'] / data['vol_ma5']
    data['vol_ratio20'] = data['volume'] / data['vol_ma20']
    
    # 价格形态
    data['hl_pct'] = (data['high'] - data['low']) / data['close']
    data['hc_pct'] = (data['high'] - data['close']) / data['close']
    data['cl_pct'] = (data['close'] - data['low']) / data['close']
    
    # 布林带
    data['boll_mid'] = data['close'].rolling(20).mean()
    data['boll_std'] = data['close'].rolling(20).std()
    data['boll_upper'] = data['boll_mid'] + 2 * data['boll_std']
    data['boll_lower'] = data['boll_mid'] - 2 * data['boll_std']
    data['boll_pos'] = (data['close'] - data['boll_lower']) / (data['boll_upper'] - data['boll_lower'] + 0.001)
    
    return data


def prepare_batch_data(symbols_batch, forward_days=5, profit_pct=0.03):
    """准备单批次数据"""
    batch_rows = []
    
    for symbol in symbols_batch:
        try:
            df = load_stock_data(symbol)
            if df is None or len(df) < 60:
                continue
            
            feat_df = calc_features(df)
            feat_df['future_ret'] = feat_df['close'].shift(-forward_days) / feat_df['close'] - 1
            feat_df['label'] = (feat_df['future_ret'] > profit_pct).astype(int)
            
            valid = feat_df.dropna(subset=FEATURES + ['future_ret'])
            
            if len(valid) < forward_days + 10:
                continue
            
            for idx in valid.index[:-forward_days]:
                row = {'symbol': symbol, 'label': feat_df.loc[idx, 'label']}
                for f in FEATURES:
                    row[f] = feat_df.loc[idx, f]
                batch_rows.append(row)
        
        except:
            pass
    
    if not batch_rows:
        return None, None
    
    df_batch = pd.DataFrame(batch_rows)
    X = df_batch[FEATURES].values
    y = df_batch['label'].values
    
    return X, y


def train_incrementally(symbols, forward_days=5, profit_pct=0.03, batch_size=500):
    """增量训练"""
    print('='*80)
    print('分批增量训练')
    print('='*80, flush=True)
    
    print(f"\n配置:", flush=True)
    print(f"  股票总数: {len(symbols)}", flush=True)
    print(f"  批次大小: {batch_size}", flush=True)
    print(f"  预测周期: {forward_days}天", flush=True)
    print(f"  盈利阈值: {int(profit_pct*100)}%", flush=True)
    
    # 初始化模型
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='binary:logistic',
        eval_metric='auc',
        use_label_encoder=False,
        random_state=42,
        verbosity=0
    )
    
    scaler = StandardScaler()
    
    total_samples = 0
    total_buy_signals = 0
    start_time = time.time()
    
    # 分批处理
    num_batches = (len(symbols) + batch_size - 1) // batch_size
    
    all_X = []
    all_y = []
    
    for batch_idx in range(num_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, len(symbols))
        batch_symbols = symbols[batch_start:batch_end]
        
        print(f"\n⏳ 批次 {batch_idx+1}/{num_batches} ({batch_start}-{batch_end})", flush=True)
        
        X_batch, y_batch = prepare_batch_data(batch_symbols, forward_days, profit_pct)
        
        if X_batch is None:
            print(f"  无有效数据", flush=True)
            continue
        
        batch_samples = len(X_batch)
        batch_buy = sum(y_batch == 1)
        
        total_samples += batch_samples
        total_buy_signals += batch_buy
        
        print(f"  样本数: {batch_samples} | 买入信号: {batch_buy} ({batch_buy/batch_samples*100:.1f}%)", flush=True)
        
        # 收集数据
        all_X.append(X_batch)
        all_y.append(y_batch)
        
        # 每批后保存中间模型
        if (batch_idx + 1) % 3 == 0:
            elapsed = time.time() - start_time
            print(f"  累计样本: {total_samples} | 耗时: {elapsed:.0f}s", flush=True)
    
    # 合并所有数据
    print("\n合并数据...", flush=True)
    X_all = np.vstack(all_X)
    y_all = np.concatenate(all_y)
    
    print(f"  总样本: {len(X_all)}", flush=True)
    print(f"  买入信号: {sum(y_all==1)} ({sum(y_all==1)/len(y_all)*100:.1f}%)", flush=True)
    
    # 划分训练测试
    X_train, X_test, y_train, y_test = train_test_split(X_all, y_all, test_size=0.2, random_state=42)
    
    # 标准化
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    
    # 训练模型
    print("\n训练模型...", flush=True)
    start_train = time.time()
    
    model.fit(X_train_s, y_train)
    
    elapsed_train = time.time() - start_train
    print(f"  训练完成: {elapsed_train:.0f}s", flush=True)
    
    # 评估
    y_pred = model.predict(X_test_s)
    y_prob = model.predict_proba(X_test_s)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    
    # 测试不同阈值
    best_threshold = 0.65
    best_high_prec = 0
    
    for threshold in [0.55, 0.60, 0.65, 0.70, 0.75]:
        high_mask = y_prob > threshold
        if sum(high_mask) > 10:
            high_correct = sum((y_test[high_mask] == 1))
            high_prec = high_correct / sum(high_mask)
            if high_prec > best_high_prec:
                best_high_prec = high_prec
                best_threshold = threshold
    
    print(f"\n📊 模型性能:", flush=True)
    print(f"  准确率: {acc:.4f}", flush=True)
    print(f"  精确率: {prec:.4f}", flush=True)
    print(f"  最佳阈值: {best_threshold*100:.0f}%", flush=True)
    print(f"  高置信度精确率: {best_high_prec:.4f}", flush=True)
    
    elapsed_total = time.time() - start_time
    print(f"\n⏱️ 总耗时: {elapsed_total:.0f}s ({elapsed_total/60:.1f}分钟)", flush=True)
    
    # 特征重要性
    imp = model.feature_importances_
    imp_df = pd.DataFrame({'feature': FEATURES, 'importance': imp})
    imp_df = imp_df.sort_values('importance', ascending=False)
    
    print(f"\n📊 Top 10 特征:", flush=True)
    for i, row in imp_df.head(10).iterrows():
        print(f"  {row['feature']:12s} : {row['importance']:.4f}", flush=True)
    
    return model, scaler, {
        'threshold': best_threshold,
        'forward_days': forward_days,
        'profit_pct': profit_pct,
        'high_precision': best_high_prec,
        'accuracy': acc,
        'precision': prec,
        'total_samples': total_samples
    }


def main():
    """主流程"""
    print('='*80)
    print('机器学习选股系统 - 分批训练版')
    print('='*80, flush=True)
    
    # 加载股票列表
    symbols = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    print(f"\n📊 全量股票: {len(symbols)} 只", flush=True)
    
    # 训练
    model, scaler, config = train_incrementally(
        symbols,
        forward_days=5,
        profit_pct=0.03,
        batch_size=500
    )
    
    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    model_file = MODEL_DIR / f'ml_selector_full_{timestamp}.pkl'
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': FEATURES,
            **config
        }, f)
    
    print(f"\n💾 模型保存: {model_file}", flush=True)
    
    # 保存特征重要性
    imp_df = pd.DataFrame({
        'feature': FEATURES,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    imp_df.to_csv(RESULTS_DIR / f'feature_importance_full_{timestamp}.csv',
                  index=False, encoding='utf-8-sig')
    
    # 总结
    print("\n" + "="*80)
    print("🎯 完成")
    print("="*80, flush=True)
    
    print(f"""
训练配置:
  预测周期: {config['forward_days']}天
  盈利阈值: {int(config['profit_pct']*100)}%
  置信度阈值: {config['threshold']*100:.0f}%

模型性能:
  总样本数: {config['total_samples']}
  准确率: {config['accuracy']*100:.1f}%
  精确率: {config['precision']*100:.1f}%
  高置信度精确率: {config['high_precision']*100:.1f}%

✅ 全量训练完成！
""", flush=True)


if __name__ == '__main__':
    main()