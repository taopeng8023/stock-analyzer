#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器学习选股系统 - 自动发现盈利模式

核心思路：
1. 从历史数据中提取特征（技术指标、形态特征、资金流向等）
2. 标签定义：未来N天收益率 > X% 为买入信号
3. 训练模型：XGBoost / LightGBM / 神经网络
4. 回测验证：确保模型预测有效

特征工程：
- 价格特征：MA5/10/20/60、涨跌幅、波动率
- 技术指标：RSI、MACD、KDJ、布林带
- 形态特征：缠论分型、蜡烛图形态
- 资金特征：成交量、换手率
- 时间特征：月份、星期

标签定义：
- 5天内涨超5%：买入信号（正样本）
- 5天内跌超5%：卖出信号（负样本）
- 其他：中性（不训练）
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import warnings
from pathlib import Path
import time
from typing import Dict, Optional, List, Tuple
import pickle
from collections import defaultdict

warnings.filterwarnings('ignore')

# 机器学习库
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except:
    HAS_SKLEARN = False

try:
    import xgboost as xgb
    HAS_XGB = True
except:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except:
    HAS_LGB = False

CACHE_DIR = Path(__file__).parent / 'data_tushare'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'
MODEL_DIR = Path(__file__).parent / 'models'
RESULTS_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)


def load_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'fields' in data and 'items' in data:
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        else:
            return None
        
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna()
        return df
    except:
        return None


# ============== 特征工程 ==============

def calc_features(data: pd.DataFrame) -> pd.DataFrame:
    """计算所有特征"""
    df = data.copy()
    
    # 1. 价格特征
    # 均线
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    # 价格相对均线位置
    df['price_to_ma5'] = (df['close'] - df['ma5']) / df['ma5']
    df['price_to_ma10'] = (df['close'] - df['ma10']) / df['ma10']
    df['price_to_ma20'] = (df['close'] - df['ma20']) / df['ma20']
    df['price_to_ma60'] = (df['close'] - df['ma60']) / df['ma60']
    
    # 均线斜率（趋势）
    df['ma5_slope'] = (df['ma5'] - df['ma5'].shift(5)) / df['ma5'].shift(5)
    df['ma10_slope'] = (df['ma10'] - df['ma10'].shift(5)) / df['ma10'].shift(5)
    df['ma20_slope'] = (df['ma20'] - df['ma20'].shift(5)) / df['ma20'].shift(5)
    
    # 均线交叉
    df['ma5_above_ma10'] = (df['ma5'] > df['ma10']).astype(int)
    df['ma5_above_ma20'] = (df['ma5'] > df['ma20']).astype(int)
    df['ma10_above_ma20'] = (df['ma10'] > df['ma20']).astype(int)
    
    # 涨跌幅
    df['return_1d'] = df['close'].pct_change()
    df['return_5d'] = df['close'].pct_change(5)
    df['return_10d'] = df['close'].pct_change(10)
    df['return_20d'] = df['close'].pct_change(20)
    
    # 波动率
    df['volatility_5d'] = df['return_1d'].rolling(5).std()
    df['volatility_20d'] = df['return_1d'].rolling(20).std()
    
    # 最高最低价差
    df['high_low_pct'] = (df['high'] - df['low']) / df['close']
    df['high_close_pct'] = (df['high'] - df['close']) / df['close']
    df['close_low_pct'] = (df['close'] - df['low']) / df['close']
    
    # 2. RSI指标
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # RSI超买超卖
    df['rsi_oversell'] = (df['rsi'] < 30).astype(int)
    df['rsi_overbuy'] = (df['rsi'] > 70).astype(int)
    
    # 3. MACD指标
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd_dif'] = ema12 - ema26
    df['macd_dea'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = (df['macd_dif'] - df['macd_dea']) * 2
    
    # MACD信号
    df['macd_above_zero'] = (df['macd_dif'] > 0).astype(int)
    df['macd_cross_up'] = ((df['macd_dif'] > df['macd_dea']) & 
                           (df['macd_dif'].shift(1) <= df['macd_dea'].shift(1))).astype(int)
    df['macd_cross_down'] = ((df['macd_dif'] < df['macd_dea']) & 
                             (df['macd_dif'].shift(1) >= df['macd_dea'].shift(1))).astype(int)
    
    # 4. KDJ指标
    lowv = df['low'].rolling(9).min()
    highv = df['high'].rolling(9).max()
    rsv = (df['close'] - lowv) / (highv - lowv) * 100
    df['kdj_k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
    df['kdj_d'] = df['kdj_k'].ewm(alpha=1/3, adjust=False).mean()
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
    
    # KDJ信号
    df['kdj_oversell'] = (df['kdj_j'] < 20).astype(int)
    df['kdj_overbuy'] = (df['kdj_j'] > 80).astype(int)
    df['kdj_cross_up'] = ((df['kdj_k'] > df['kdj_d']) & 
                          (df['kdj_k'].shift(1) <= df['kdj_d'].shift(1))).astype(int)
    
    # 5. 布林带
    df['boll_mid'] = df['close'].rolling(20).mean()
    df['boll_std'] = df['close'].rolling(20).std()
    df['boll_upper'] = df['boll_mid'] + 2 * df['boll_std']
    df['boll_lower'] = df['boll_mid'] - 2 * df['boll_std']
    
    df['boll_position'] = (df['close'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'])
    df['boll_width'] = (df['boll_upper'] - df['boll_lower']) / df['boll_mid']
    
    # 布林带信号
    df['boll_below_lower'] = (df['close'] < df['boll_lower']).astype(int)
    df['boll_above_upper'] = (df['close'] > df['boll_upper']).astype(int)
    
    # 6. 成交量特征
    df['volume_ma5'] = df['volume'].rolling(5).mean()
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    
    df['volume_ratio'] = df['volume'] / df['volume_ma5']
    df['volume_ratio_20'] = df['volume'] / df['volume_ma20']
    
    # 放量缩量
    df['volume_expand'] = (df['volume_ratio'] > 2).astype(int)
    df['volume_shrink'] = (df['volume_ratio'] < 0.5).astype(int)
    
    # 量价关系
    df['price_up_volume_up'] = ((df['return_1d'] > 0) & (df['volume_ratio'] > 1)).astype(int)
    df['price_down_volume_down'] = ((df['return_1d'] < 0) & (df['volume_ratio'] < 1)).astype(int)
    
    # 7. 时间特征
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_month_start'] = df['date'].dt.is_month_start.astype(int)
    df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
    
    # 8. 缠论分型（简化版）
    # 底分型：低点比前后两天都低
    df['bottom_fractal'] = ((df['low'] < df['low'].shift(1)) & 
                            (df['low'] < df['low'].shift(-1))).astype(int)
    
    # 顶分型：高点比前后两天都高
    df['top_fractal'] = ((df['high'] > df['high'].shift(1)) & 
                         (df['high'] > df['high'].shift(-1))).astype(int)
    
    # 9. 蜡烛图形态（简化版）
    # 大阳线：涨幅>3%，收盘接近最高
    df['big_bull'] = ((df['return_1d'] > 0.03) & 
                      (df['close_close_pct'] < 0.1)).astype(int)
    
    # 大阴线：跌幅>3%，收盘接近最低
    df['big_bear'] = ((df['return_1d'] < -0.03) & 
                      (df['close_low_pct'] < 0.1)).astype(int)
    
    # 锤头线：实体小，下影线长
    body = abs(df['close'] - df['open'])
    lower_shadow = df['close'] - df['low'] if df['close'] > df['open'] else df['open'] - df['low']
    df['hammer'] = ((body / df['close'] < 0.01) & 
                    (lower_shadow / df['close'] > 0.02)).astype(int)
    
    # 10. 连续涨跌（简化版，最近5天）
    df['up_days_5'] = (df['return_1d'].shift(1) > 0).astype(int).rolling(5).sum()
    df['down_days_5'] = (df['return_1d'].shift(1) < 0).astype(int).rolling(5).sum()
    
    return df


def create_labels(data: pd.DataFrame, forward_days: int = 5, 
                  profit_threshold: float = 0.05, 
                  loss_threshold: float = -0.05) -> pd.DataFrame:
    """创建标签"""
    df = data.copy()
    
    # 计算未来N天收益率
    df['future_return'] = df['close'].shift(-forward_days) / df['close'] - 1
    
    # 标签定义
    # 1 = 买入信号（未来涨超5%）
    # 0 = 中性（不训练）
    # -1 = 卖出信号（未来跌超5%）
    df['label'] = 0
    df.loc[df['future_return'] > profit_threshold, 'label'] = 1
    df.loc[df['future_return'] < loss_threshold, 'label'] = -1
    
    return df


def prepare_training_data(symbols: List[str], 
                          forward_days: int = 5,
                          profit_threshold: float = 0.05) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """准备训练数据"""
    print('='*80)
    print('准备训练数据')
    print('='*80, flush=True)
    
    all_features = []
    all_labels = []
    
    start_time = time.time()
    
    for i, symbol in enumerate(symbols):
        try:
            data = load_stock_data(symbol)
            if data is None or len(data) < 200:
                continue
            
            # 计算特征
            features_df = calc_features(data)
            
            # 创建标签
            labeled_df = create_labels(features_df, forward_days, profit_threshold)
            
            # 去除无效数据
            labeled_df = labeled_df.dropna()
            
            # 只保留有明确标签的数据（买入或卖出）
            valid_data = labeled_df[labeled_df['label'] != 0]
            
            if len(valid_data) < 10:
                continue
            
            # 选择特征列
            feature_cols = [col for col in labeled_df.columns 
                           if col not in ['date', 'open', 'high', 'low', 'close', 'volume',
                                          'future_return', 'label', 'symbol']]
            
            X = valid_data[feature_cols].values
            y = valid_data['label'].values
            
            # 转换标签：-1变为0（卖出），1变为1（买入）
            y = (y == 1).astype(int)  # 只预测买入信号
            
            all_features.append(X)
            all_labels.append(y)
            
            if (i + 1) % 500 == 0:
                elapsed = time.time() - start_time
                print(f"⏳ {i+1}/{len(symbols)} | 特征数:{len(feature_cols)} | 样本数:{sum(len(f) for f in all_features)} | 耗时:{elapsed:.0f}秒", flush=True)
        
        except Exception as e:
            pass
    
    # 合并
    X_all = np.vstack(all_features)
    y_all = np.concatenate(all_labels)
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ 数据准备完成", flush=True)
    print(f"  总样本数：{len(X_all)}", flush=True)
    print(f"  特征数：{X_all.shape[1]}", flush=True)
    print(f"  买入信号：{sum(y_all == 1)} ({sum(y_all == 1)/len(y_all)*100:.1f}%)", flush=True)
    print(f"  卖险信号：{sum(y_all == 0)} ({sum(y_all == 0)/len(y_all)*100:.1f}%)", flush=True)
    print(f"  耗时：{elapsed:.0f}秒", flush=True)
    
    return X_all, y_all, feature_cols


def train_model(X: np.ndarray, y: np.ndarray, model_type: str = 'xgboost'):
    """训练模型"""
    print('\n' + '='*80)
    print(f'训练模型：{model_type}')
    print('='*80, flush=True)
    
    # 划分训练测试集
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    start_time = time.time()
    
    if model_type == 'xgboost' and HAS_XGB:
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            eval_metric='auc',
            use_label_encoder=False,
            random_state=42
        )
        model.fit(X_train_scaled, y_train)
    
    elif model_type == 'lightgbm' and HAS_LGB:
        model = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary',
            random_state=42,
            verbose=-1
        )
        model.fit(X_train_scaled, y_train)
    
    elif model_type == 'random_forest' and HAS_SKLEARN:
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train_scaled, y_train)
    
    elif model_type == 'gradient_boosting' and HAS_SKLEARN:
        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        model.fit(X_train_scaled, y_train)
    
    else:
        print("❌ 模型库不可用，使用随机森林", flush=True)
        if HAS_SKLEARN:
            model = RandomForestClassifier(n_estimators=50, random_state=42)
            model.fit(X_train_scaled, y_train)
        else:
            return None, None, None
    
    elapsed = time.time() - start_time
    
    # 预测
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]  # 买入概率
    
    # 评估
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    print(f"\n📊 模型性能", flush=True)
    print(f"  准确率：{accuracy:.4f}", flush=True)
    print(f"  精确率：{precision:.4f}（预测买入中真正上涨的比例）", flush=True)
    print(f" 召回率：{recall:.4f}（真正上涨中被预测到的比例）", flush=True)
    print(f"  F1分数：{f1:.4f}", flush=True)
    print(f"  训练耗时：{elapsed:.0f}秒", flush=True)
    
    # 特征重要性
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
    
    return model, scaler, {'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1': f1}


def backtest_ml_strategy(model, scaler, feature_cols: List[str], 
                         symbols: List[str], threshold: float = 0.6):
    """回测机器学习策略"""
    print('\n' + '='*80)
    print('回测机器学习策略')
    print('='*80, flush=True)
    
    results = []
    
    for symbol in symbols:
        try:
            data = load_stock_data(symbol)
            if data is None or len(data) < 200:
                continue
            
            # 计算特征
            features_df = calc_features(data)
            
            # 准备预测数据
            features_df = features_df.dropna()
            
            if len(features_df) < 50:
                continue
            
            X = features_df[feature_cols].values
            X_scaled = scaler.transform(X)
            
            # 预测买入概率
            probs = model.predict_proba(X_scaled)[:, 1]
            
            # 回测
            capital = 100000
            position = 0
            cost_price = 0
            buy_idx = 0
            trades = []
            
            for i in range(len(features_df)):
                prob = probs[i]
                close = float(features_df['close'].iloc[i])
                
                # 持仓检查
                if position > 0:
                    hold_days = i - buy_idx
                    
                    # 止损10%
                    loss = (close - cost_price) / cost_price
                    if loss <= -0.10:
                        trades.append({'profit_pct': loss, 'reason': 'stop_loss'})
                        position = 0
                        continue
                    
                    # 止盈15%
                    if loss >= 0.15:
                        trades.append({'profit_pct': loss, 'reason': 'take_profit'})
                        position = 0
                        continue
                    
                    # 最大持仓15天
                    if hold_days >= 15:
                        trades.append({'profit_pct': loss, 'reason': 'max_hold'})
                        position = 0
                        continue
                
                # 买入信号（概率 > threshold）
                if position == 0 and prob > threshold:
                    trades.append({'type': 'buy', 'prob': prob})
                    position = 1
                    cost_price = close * 1.001
                    buy_idx = i
            
            # 强制平仓
            if position > 0 and trades:
                last_close = float(features_df['close'].iloc[-1])
                loss = (last_close - cost_price) / cost_price
                trades.append({'profit_pct': loss, 'reason': 'force'})
            
            # 统计
            sell_trades = [t for t in trades if 'profit_pct' in t]
            if sell_trades:
                win_trades = [t for t in sell_trades if t['profit_pct'] > 0]
                win_rate = len(win_trades) / len(sell_trades)
                avg_profit = np.mean([t['profit_pct'] for t in sell_trades])
                
                results.append({
                    'symbol': symbol,
                    'trades': len(sell_trades),
                    'win_rate': win_rate,
                    'avg_profit': avg_profit
                })
        
        except:
            pass
    
    if results:
        avg_win_rate = np.mean([r['win_rate'] for r in results])
        avg_profit = np.mean([r['avg_profit'] for r in results])
        total_trades = sum([r['trades'] for r in results])
        
        print(f"\n📊 回测结果", flush=True)
        print(f"  覆盖股票：{len(results)} 只", flush=True)
        print(f"  总交易数：{total_trades} 次", flush=True)
        print(f"  平均胜率：{avg_win_rate*100:.1f}%", flush=True)
        print(f"  平均收益：{avg_profit*100:+.2f}%", flush=True)
        
        # Top表现
        sorted_results = sorted(results, key=lambda x: -x['avg_profit'])
        print(f"\n🏆 Top 10 表现最佳股票", flush=True)
        print("| 代码 | 交易 | 胜率 | 平均收益 |", flush=True)
        for r in sorted_results[:10]:
            print(f"| {r['symbol']} | {r['trades']} | {r['win_rate']*100:.1f}% | {r['avg_profit']*100:+.2f}% |", flush=True)
    
    return results


def main():
    """主流程"""
    print('='*80)
    print('机器学习选股系统 - 自动发现盈利模式')
    print('='*80, flush=True)
    
    # 检查库
    print("\n📦 检查机器学习库...", flush=True)
    print(f"  sklearn: {'✅' if HAS_SKLEARN else '❌'}", flush=True)
    print(f"  xgboost: {'✅' if HAS_XGB else '❌'}", flush=True)
    print(f"  lightgbm: {'✅' if HAS_LGB else '❌'}", flush=True)
    
    if not HAS_SKLEARN:
        print("\n❌ 缺少sklearn库，请安装：pip install scikit-learn", flush=True)
        return
    
    # 加载股票列表
    stock_files = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    print(f"\n📊 股票数量：{len(stock_files)} 只", flush=True)
    
    # 配置
    forward_days = 5  # 预测未来5天
    profit_threshold = 0.05  # 涨超5%为买入信号
    
    print(f"\n⚙️ 配置：", flush=True)
    print(f"  预测周期：{forward_days}天", flush=True)
    print(f"  盈利阈值：+{int(profit_threshold*100)}%", flush=True)
    print(f"  亏损阈值：-{int(profit_threshold*100)}%", flush=True)
    
    # 准备数据
    X, y, feature_cols = prepare_training_data(stock_files[:500], forward_days, profit_threshold)
    
    if len(X) < 100:
        print("\n❌ 样本数太少，无法训练", flush=True)
        return
    
    # 训练模型
    model_types = ['random_forest']
    if HAS_XGB:
        model_types.append('xgboost')
    if HAS_LGB:
        model_types.append('lightgbm')
    
    best_model = None
    best_scaler = None
    best_score = 0
    best_type = None
    
    for model_type in model_types:
        model, scaler, metrics = train_model(X, y, model_type)
        
        if metrics['precision'] > best_score:
            best_score = metrics['precision']
            best_model = model
            best_scaler = scaler
            best_type = model_type
    
    print(f"\n🏆 最佳模型：{best_type}，精确率：{best_score:.4f}", flush=True)
    
    # 回测
    if best_model:
        backtest_ml_strategy(best_model, best_scaler, feature_cols, 
                            stock_files[:200], threshold=0.6)
    
    # 保存模型
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    model_path = MODEL_DIR / f'ml_selector_{timestamp}.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': best_model,
            'scaler': best_scaler,
            'feature_cols': feature_cols,
            'best_type': best_type
        }, f)
    
    print(f"\n💾 模型已保存：{model_path}", flush=True)
    
    # 特征重要性
    if hasattr(best_model, 'feature_importances_'):
        importance = best_model.feature_importances_
        importance_df = pd.DataFrame({
            'feature': feature_cols,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        print(f"\n📊 Top 20 重要特征", flush=True)
        print(importance_df.head(20).to_string(), flush=True)
        
        importance_df.to_csv(RESULTS_DIR / f'feature_importance_{timestamp}.csv',
                            index=False, encoding='utf-8-sig')


if __name__ == '__main__':
    main()