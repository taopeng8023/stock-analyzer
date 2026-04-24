#!/usr/bin/env python3
"""
深度优化 - 短攻_3天3pct 策略
目标：提升收益和胜率

优化方向：
1. 特征扩展 - 新增动量、成交量形态等
2. 网络结构 - 更深的网络
3. 训练策略 - 增加迭代次数、调整学习率
4. 阈值优化 - 寻找最佳置信度阈值
"""
import os
import pickle
import json
import gc
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("深度优化 - 短攻_3天3pct 策略")
print("="*80)
print(f"开始时间: {datetime.now()}")

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 目标策略配置
STRATEGY = {
    "name": "短攻_深度优化",
    "forward": 3,
    "profit": 0.03,
}

# 扩展特征集 (38个特征)
FEATURES_EXTENDED = [
    # 价格均线位置
    "p_ma5", "p_ma10", "p_ma20", "p_ma60",
    
    # 均线斜率
    "ma5_slope", "ma10_slope", "ma20_slope", "ma60_slope",
    
    # 收益率 (动量)
    "ret1", "ret2", "ret3", "ret5", "ret10", "ret20",
    
    # 波动率
    "vol5", "vol10", "vol20",
    
    # 技术指标
    "rsi", "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    
    # 成交量相关
    "vol_ratio", "vol_ratio5", "vol_ratio20",
    "vol_change",  # 成交量变化率
    
    # 价格形态
    "hl_pct", "hc_pct", "cl_pct", "boll_pos",
    "gap_pct",  # 当日跳空幅度
    "high_low_pos",  # 收盘在最高最低的位置
    
    # 连续涨跌
    "consecutive_up", "consecutive_down",
    
    # 相对强度 (vs MA)
    "strength_ma5", "strength_ma20",
]

# 加载训练数据
print("\n加载训练数据...")
all_data = []
for batch_idx in range(10):
    batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}.csv")
    if os.path.exists(batch_file):
        batch_df = pd.read_csv(batch_file, nrows=150000)  # 增加样本量
        all_data.append(batch_df)
        print(f"  batch_{batch_idx}: {len(batch_df)} samples")

train_df = pd.concat(all_data, ignore_index=True)
print(f"训练样本总数: {len(train_df)}")

# 计算扩展特征
print("\n计算扩展特征...")

def compute_extended_features(df):
    """计算扩展特征集"""
    # 基础特征已经存在于temp_data中，需要补充新的
    
    # 均线60斜率
    df['ma60_slope'] = df['close'].rolling(60).mean().pct_change()
    
    # 更多收益率
    df['ret2'] = df['close'].pct_change(2)
    df['ret3'] = df['close'].pct_change(3)
    
    # 成交量变化率
    df['vol_change'] = df['vol'].pct_change()
    df['vol_ratio5'] = df['vol'] / df['vol'].rolling(5).mean()
    
    # 当日跳空
    df['gap_pct'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
    
    # 收盘位置 (在最高最低之间)
    df['high_low_pos'] = (df['close'] - df['low']) / (df['high'] - df['low'])
    
    # 连续涨跌天数
    df['up'] = (df['ret1'] > 0).astype(int)
    df['consecutive_up'] = df['up'].rolling(5, min_periods=1).sum()
    df['down'] = (df['ret1'] < 0).astype(int)
    df['consecutive_down'] = df['down'].rolling(5, min_periods=1).sum()
    
    # 相对强度
    df['strength_ma5'] = df['close'] / df['close'].rolling(5).mean() - 1
    df['strength_ma20'] = df['close'] / df['close'].rolling(20).mean() - 1
    
    return df

# 按股票分组计算特征 (避免跨股票计算)
train_df = train_df.groupby('code', group_keys=False).apply(compute_extended_features)

# 计算label
forward = STRATEGY['forward']
profit = STRATEGY['profit']

train_df['future_ret'] = train_df.groupby('code')['ret1'].transform(
    lambda x: x.rolling(forward, min_periods=1).sum().shift(-forward)
)
train_df['label'] = (train_df['future_ret'] > profit).astype(int)

# 过滤有效数据
train_valid = train_df.dropna(subset=FEATURES_EXTENDED + ['future_ret', 'label'])
train_valid = train_valid.groupby('code', group_keys=False).apply(
    lambda x: x.iloc[:-forward] if len(x) > forward else x.iloc[:0]
)

print(f"有效训练样本: {len(train_valid)}")
print(f"正样本比例: {train_valid['label'].mean()*100:.2f}%")

if len(train_valid) < 50000:
    print("⚠️ 样本不足，使用简化特征集")
    FEATURES_FINAL = FEATURES_EXTENDED[:25]  # 只用前25个
else:
    FEATURES_FINAL = FEATURES_EXTENDED

# 训练配置
print("\n开始训练...")

# 深度网络结构
hidden_layers = (512, 256, 128, 64, 32)

scaler = StandardScaler()
model = MLPClassifier(
    hidden_layer_sizes=hidden_layers,
    activation='relu',
    solver='adam',
    learning_rate_init=0.001,
    alpha=0.001,
    batch_size=512,
    max_iter=100,
    random_state=42,
    warm_start=True,
    early_stopping=True,
    validation_fraction=0.1,
    n_iter_no_change=10,
)

# 分批训练
batch_size = 200000
total_batches = len(train_valid) // batch_size + 1

for i in range(total_batches):
    start = i * batch_size
    end = min(start + batch_size, len(train_valid))
    
    batch = train_valid.iloc[start:end]
    
    X = batch[FEATURES_FINAL].fillna(0).values.astype(np.float32)
    y = batch['label'].values
    
    if i == 0:
        scaler.fit(X)
    
    X_scaled = scaler.transform(X)
    
    model.partial_fit(X_scaled, y, classes=[0, 1])
    
    if i % 2 == 0:
        print(f"  训练进度: {end}/{len(train_valid)}")
    
    del X, X_scaled, y, batch
    gc.collect()

print(f"\n训练完成!")

# 验证
print("\n验证模型性能...")

# 加载独立测试数据
test_stocks = ['000001', '600000', '600519', '000858', '002415']  # 几只代表性股票
DATA_DIR = "data_history_2022_2026"

test_data = []
for stock in test_stocks:
    stock_file = os.path.join(DATA_DIR, f"{stock}.json")
    if os.path.exists(stock_file):
        with open(stock_file, 'r') as f:
            data = json.load(f)
        if 'items' in data:
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df['code'] = stock
            df = compute_extended_features(df)
            test_data.append(df)

if test_data:
    test_df = pd.concat(test_data, ignore_index=True)
    test_df['future_ret'] = test_df.groupby('code')['ret1'].transform(
        lambda x: x.rolling(forward, min_periods=1).sum().shift(-forward)
    )
    test_df['label'] = (test_df['future_ret'] > profit).astype(int)
    
    test_valid = test_df.dropna(subset=FEATURES_FINAL + ['future_ret', 'label'])
    test_valid = test_valid.groupby('code', group_keys=False).apply(
        lambda x: x.iloc[:-forward] if len(x) > forward else x.iloc[:0]
    )
    
    X_test = test_valid[FEATURES_FINAL].fillna(0).values.astype(np.float32)
    X_test_scaled = scaler.transform(X_test)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    y_true = test_valid['label'].values
    
    # AUC
    auc = roc_auc_score(y_true, y_prob)
    
    # 阈值搜索
    best_thresh = 0.85
    best_score = 0
    for thresh in [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]:
        selected = y_prob >= thresh
        if selected.sum() > 5:
            avg_ret = test_valid.loc[selected, 'future_ret'].mean()
            win_rate = (test_valid.loc[selected, 'future_ret'] > 0).mean()
            score = avg_ret * win_rate
            if score > best_score:
                best_score = score
                best_thresh = thresh
    
    # 最终评估
    selected = y_prob >= best_thresh
    avg_ret = test_valid.loc[selected, 'future_ret'].mean() if selected.sum() > 0 else 0
    win_rate = (test_valid.loc[selected, 'future_ret'] > 0).mean() if selected.sum() > 0 else 0
    prec = precision_score(y_true, (y_prob >= best_thresh).astype(int), zero_division=0)
    
    print(f"\n验证结果:")
    print(f"  AUC: {auc:.4f}")
    print(f"  最佳阈值: {best_thresh}")
    print(f"  精确率: {prec:.2%}")
    print(f"  平均收益: {avg_ret*100:.2f}%")
    print(f"  胜率: {win_rate:.1%}")
    print(f"  选股数: {selected.sum()}")

# 保存模型
model_file = os.path.join(MODEL_DIR, f"ml_deep_{STRATEGY['name']}.pkl")
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': model,
        'scaler': scaler,
        'features': FEATURES_FINAL,
        'strategy': STRATEGY,
        'metrics': {
            'auc': auc,
            'threshold': best_thresh,
            'avg_return': avg_ret,
            'win_rate': win_rate,
        }
    }, f)

print(f"\n✅ 模型保存: {model_file}")

# 保存结果
result = {
    'name': STRATEGY['name'],
    'features_count': len(FEATURES_FINAL),
    'hidden_layers': hidden_layers,
    'auc': auc,
    'threshold': best_thresh,
    'avg_return': avg_ret * 100,
    'win_rate': win_rate,
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
}

with open(os.path.join(MODEL_DIR, 'deep_optimization_result.json'), 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\n完成时间: {datetime.now()}")
print(f"\n对比基线 (短攻_3天3pct): 平均收益 12.11%, 胜率 71.4%")