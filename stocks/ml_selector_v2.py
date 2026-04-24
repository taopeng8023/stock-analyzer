#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器学习选股系统 V2 - 简化版
自动从历史数据中发现盈利模式

核心思路：
1. 特征：简单的技术指标（RSI、MACD、均线等）
2. 标签：未来5天涨幅>3%
3. 模型：XGBoost分类器
4. 回测：验证预测效果
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

# 机器学习库
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

CACHE_DIR = Path(__file__).parent / 'data_tushare'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'
MODEL_DIR = Path(__file__).parent / 'models'
RESULTS_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)


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
    """计算特征 - 简化版"""
    data = df.copy()
    
    # 均线
    data['ma5'] = data['close'].rolling(5).mean()
    data['ma10'] = data['close'].rolling(10).mean()
    data['ma20'] = data['close'].rolling(20).mean()
    
    # 价格相对均线
    data['p_ma5'] = (data['close'] - data['ma5']) / data['ma5']
    data['p_ma10'] = (data['close'] - data['ma10']) / data['ma10']
    data['p_ma20'] = (data['close'] - data['ma20']) / data['ma20']
    
    # 均线斜率
    data['ma5_slope'] = data['ma5'] / data['ma5'].shift(5) - 1
    data['ma20_slope'] = data['ma20'] / data['ma20'].shift(10) - 1
    
    # 涨跌幅
    data['ret1'] = data['close'].pct_change()
    data['ret5'] = data['close'].pct_change(5)
    data['ret10'] = data['close'].pct_change(10)
    
    # 波动率
    data['vol5'] = data['ret1'].rolling(5).std()
    data['vol20'] = data['ret1'].rolling(20).std()
    
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
    data['vol_ratio'] = data['volume'] / data['vol_ma5']
    
    # 最高最低价差
    data['hl_pct'] = (data['high'] - data['low']) / data['close']
    
    return data


def prepare_data(symbols, forward_days=5, profit_pct=0.03):
    """准备训练数据"""
    print('='*80)
    print('准备训练数据')
    print('='*80, flush=True)
    
    # 特征列表
    features = [
        'p_ma5', 'p_ma10', 'p_ma20',
        'ma5_slope', 'ma20_slope',
        'ret1', 'ret5', 'ret10',
        'vol5', 'vol20',
        'rsi',
        'macd_dif', 'macd_dea', 'macd_hist',
        'kdj_k', 'kdj_d', 'kdj_j',
        'vol_ratio',
        'hl_pct'
    ]
    
    all_data = []
    start_time = time.time()
    
    for i, symbol in enumerate(symbols[:500]):  # 先处理500只
        try:
            df = load_stock_data(symbol)
            if df is None or len(df) < 100:
                continue
            
            # 计算特征
            feat_df = calc_features(df)
            
            # 计算未来收益
            feat_df['future_ret'] = feat_df['close'].shift(-forward_days) / feat_df['close'] - 1
            
            # 标签：涨超3%为买入信号
            feat_df['label'] = (feat_df['future_ret'] > profit_pct).astype(int)
            
            # 只保留有完整特征和标签的数据
            valid = feat_df.dropna(subset=features + ['future_ret'])
            
            if len(valid) < 30:
                continue
            
            # 收集数据
            for idx in valid.index[:-forward_days]:  # 排除最后几天
                row_data = {
                    'symbol': symbol,
                    'date': feat_df.loc[idx, 'date'],
                    'label': feat_df.loc[idx, 'label']
                }
                for f in features:
                    row_data[f] = feat_df.loc[idx, f]
                all_data.append(row_data)
            
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                print(f"⏳ {i+1}/{len(symbols[:500])} | 样本:{len(all_data)} | 耗时:{elapsed:.0f}s", flush=True)
        
        except:
            pass
    
    if not all_data:
        print("\n❌ 无有效数据", flush=True)
        return None, None, None
    
    # 转为DataFrame
    df_all = pd.DataFrame(all_data)
    
    X = df_all[features].values
    y = df_all['label'].values
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ 数据准备完成", flush=True)
    print(f"  样本数：{len(X)}", flush=True)
    print(f"  特征数：{len(features)}", flush=True)
    print(f"  买入信号：{sum(y==1)} ({sum(y==1)/len(y)*100:.1f}%)", flush=True)
    print(f"  非买入：{sum(y==0)} ({sum(y==0)/len(y)*100:.1f}%)", flush=True)
    print(f"  耗时：{elapsed:.0f}s", flush=True)
    
    return X, y, features


def train_model(X, y):
    """训练模型"""
    print('\n' + '='*80)
    print('训练 XGBoost 模型')
    print('='*80, flush=True)
    
    # 划分数据
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 标准化
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    
    # 训练
    print("  训练中...", flush=True)
    start = time.time()
    
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
    model.fit(X_train_s, y_train)
    
    elapsed = time.time() - start
    print(f"  训练完成：{elapsed:.0f}s", flush=True)
    
    # 评估
    y_pred = model.predict(X_test_s)
    y_prob = model.predict_proba(X_test_s)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    
    print(f"\n📊 模型性能", flush=True)
    print(f"  准确率：{acc:.4f}", flush=True)
    print(f"  精确率：{prec:.4f} (预测买入中真正上涨的比例)", flush=True)
    print(f"  召回率：{rec:.4f} (真正上涨中被预测到的比例)", flush=True)
    
    # 高置信度预测
    high_prob = y_prob > 0.6
    if sum(high_prob) > 0:
        high_prec = sum((y_pred[high_prob] == 1) & (y_test[high_prob] == 1)) / sum(high_prob)
        print(f"  高置信度(>60%)精确率：{high_prec:.4f}", flush=True)
    
    return model, scaler


def backtest(model, scaler, features, symbols, prob_threshold=0.65):
    """回测策略"""
    print('\n' + '='*80)
    print(f'回测 ML策略 (置信度>{int(prob_threshold*100)}%)')
    print('='*80, flush=True)
    
    results = []
    
    for symbol in symbols[:200]:  # 回测200只
        try:
            df = load_stock_data(symbol)
            if df is None or len(df) < 100:
                continue
            
            feat_df = calc_features(df)
            feat_df = feat_df.dropna(subset=features)
            
            if len(feat_df) < 50:
                continue
            
            # 预测
            X = feat_df[features].values
            X_s = scaler.transform(X)
            probs = model.predict_proba(X_s)[:, 1]
            
            # 回测交易
            capital = 100000
            pos = 0
            cost = 0
            buy_i = 0
            trades = []
            
            for i in range(len(feat_df)):
                prob = probs[i]
                close = float(feat_df['close'].iloc[i])
                
                if pos > 0:
                    hold = i - buy_i
                    pnl = (close - cost) / cost
                    
                    # 止损10%
                    if pnl <= -0.10:
                        trades.append({'ret': pnl, 'reason': 'stop'})
                        pos = 0
                    
                    # 止盈12%
                    elif pnl >= 0.12:
                        trades.append({'ret': pnl, 'reason': 'profit'})
                        pos = 0
                    
                    # 持仓15天
                    elif hold >= 15:
                        trades.append({'ret': pnl, 'reason': 'hold'})
                        pos = 0
                
                # 买入（高置信度）
                if pos == 0 and prob > prob_threshold:
                    pos = 1
                    cost = close * 1.001
                    buy_i = i
            
            # 强制平仓
            if pos > 0:
                pnl = (feat_df['close'].iloc[-1] - cost) / cost
                trades.append({'ret': pnl, 'reason': 'force'})
            
            # 统计
            if trades:
                win = [t for t in trades if t['ret'] > 0]
                win_rate = len(win) / len(trades)
                avg_ret = np.mean([t['ret'] for t in trades])
                
                results.append({
                    'symbol': symbol,
                    'trades': len(trades),
                    'win_rate': win_rate,
                    'avg_ret': avg_ret
                })
        
        except:
            pass
    
    if results:
        avg_win = np.mean([r['win_rate'] for r in results])
        avg_ret = np.mean([r['avg_ret'] for r in results])
        total = sum([r['trades'] for r in results])
        
        print(f"\n📊 回测结果", flush=True)
        print(f"  覆盖股票：{len(results)}", flush=True)
        print(f"  总交易数：{total}", flush=True)
        print(f"  平均胜率：{avg_win*100:.1f}%", flush=True)
        print(f"  平均收益：{avg_ret*100:+.2f}%", flush=True)
        
        # Top10
        sorted_r = sorted(results, key=lambda x: -x['avg_ret'])
        print("\n🏆 Top 10", flush=True)
        for r in sorted_r[:10]:
            print(f"  {r['symbol']} | {r['trades']}次 | 胜率{r['win_rate']*100:.0f}% | 收益{r['avg_ret']*100:+.1f}%", flush=True)
    
    return results


def main():
    """主流程"""
    print('='*80)
    print('机器学习选股系统 V2 - 自动发现盈利模式')
    print('='*80, flush=True)
    
    # 加载股票列表
    symbols = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    print(f"\n📊 股票数量：{len(symbols)}", flush=True)
    
    # 准备数据
    X, y, features = prepare_data(symbols, forward_days=5, profit_pct=0.03)
    
    if X is None:
        return
    
    # 训练模型
    model, scaler = train_model(X, y)
    
    # 回测
    results = backtest(model, scaler, features, symbols, prob_threshold=0.65)
    
    # 特征重要性
    print("\n" + "="*80)
    print("📊 特征重要性")
    print("="*80, flush=True)
    
    imp = model.feature_importances_
    imp_df = pd.DataFrame({'feature': features, 'importance': imp})
    imp_df = imp_df.sort_values('importance', ascending=False)
    
    for i, row in imp_df.head(10).iterrows():
        print(f"  {row['feature']:15s} : {row['importance']:.4f}", flush=True)
    
    # 保存模型
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_file = MODEL_DIR / f'ml_selector_v2_{timestamp}.pkl'
    
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'features': features
        }, f)
    
    print(f"\n💾 模型已保存：{model_file}", flush=True)
    
    # 保存特征重要性
    imp_df.to_csv(RESULTS_DIR / f'feature_importance_v2_{timestamp}.csv',
                  index=False, encoding='utf-8-sig')
    
    # 总结
    print("\n" + "="*80)
    print("🎯 结论")
    print("="*80, flush=True)
    
    if results and np.mean([r['win_rate'] for r in results]) > 0.55:
        print("✅ 机器学习策略有效！胜率>55%", flush=True)
        print("\n💡 使用方法：", flush=True)
        print("  1. 加载模型：pickle.load(open(model_file, 'rb'))", flush=True)
        print("  2. 计算特征：calc_features(df)", flush=True)
        print("  3. 预测买入概率：model.predict_proba(X)", flush=True)
        print("  4. 筛选高置信度(>65%)股票买入", flush=True)
    else:
        print("⚠️ 策略表现一般，可调整参数：", flush=True)
        print("  - 提高置信度阈值(70%+)", flush=True)
        print("  - 增加特征(成交量形态等)", flush=True)
        print("  - 延长预测周期(10天)", flush=True)


if __name__ == '__main__':
    main()