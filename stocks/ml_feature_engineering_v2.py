#!/usr/bin/env python3
"""
特征工程 V2 - 扩展特征集
目标: 从14特征扩展到25+特征，提升模型预测能力
"""
import os
import sys
import json
import pickle
import time
import gc
import numpy as np
import pandas as pd
from datetime import datetime

print("="*60)
print("特征工程 V2 - 扩展特征集")
print("="*60)

TEMP_DIR = "temp_data"
MODEL_DIR = "models"

# 加载原始数据样本
print("\n加载样本数据...")
sample_df = pd.read_csv(os.path.join(TEMP_DIR, "batch_0.csv"), nrows=100)
print(f"样本数: {len(sample_df)}")

# 查看现有列
cols = sample_df.columns.tolist()
print(f"\n数据列 ({len(cols)}个):")
for c in cols[:30]:
    print(f"  - {c}")

# 定义特征组
FEATURE_GROUPS = {
    # 原有14特征 (已验证有效)
    "original": [
        "p_ma5", "p_ma10", "p_ma20",
        "ma5_slope", "ma10_slope",
        "ret5", "ret10", "ret20",
        "rsi", "macd_hist",
        "kdj_k", "kdj_d",
        "vol_ratio", "boll_pos"
    ],
    
    # 扩展均线特征
    "ma_extended": [
        "p_ma60",  # MA60相对位置
        "ma20_slope",  # MA20斜率
    ],
    
    # 成交量特征
    "volume": [
        "vol5", "vol10", "vol20",  # 成交量均线
        "vol_ratio20",  # 20日量比
    ],
    
    # MACD完整特征
    "macd_full": [
        "macd_dif", "macd_dea",  # MACD分量
    ],
    
    # KDJ完整特征
    "kdj_full": [
        "kdj_j",  # KDJ的J值
    ],
    
    # 价格形态特征
    "price_pattern": [
        "hl_pct",  # 最高最低价差比
        "hc_pct",  # 收盘价距最高价
        "cl_pct",  # 收盘价距最低价
    ],
}

# 计算需要新增的特征
print("\n分析现有特征...")
existing_cols = set(cols)
need_create = []

for group, features in FEATURE_GROUPS.items():
    missing = [f for f in features if f not in existing_cols]
    if missing:
        print(f"  {group}: 缺少 {len(missing)} 个特征")
        need_create.extend(missing)

if need_create:
    print(f"\n需要新增特征: {need_create}")
else:
    print("\n所有特征已存在，无需新增")

# 定义新特征计算函数
def compute_new_features(df):
    """计算新增技术指标特征"""
    
    # ATR (真实波动幅度) - 14日
    if 'atr' not in df.columns:
        high = df['high'] if 'high' in df.columns else df['close'] * (1 + 0.02)
        low = df['low'] if 'low' in df.columns else df['close'] * (1 - 0.02)
        close_prev = df['close'].shift(1)
        tr1 = high - low
        tr2 = abs(high - close_prev)
        tr3 = abs(low - close_prev)
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        df['atr'] = tr.rolling(14).mean() / df['close']
    
    # 威廉指标 WR - 14日
    if 'wr' not in df.columns:
        high_n = df['high'].rolling(14).max() if 'high' in df.columns else df['close'].rolling(14).max() * 1.02
        low_n = df['low'].rolling(14).min() if 'low' in df.columns else df['close'].rolling(14).min() * 0.98
        df['wr'] = (high_n - df['close']) / (high_n - low_n) * 100
    
    # CCI (商品通道指标)
    if 'cci' not in df.columns:
        tp = (df['high'] + df['low'] + df['close']) / 3 if 'high' in df.columns else df['close']
        ma_tp = tp.rolling(20).mean()
        md = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
        df['cci'] = (tp - ma_tp) / (0.015 * md)
    
    # 连续涨跌天数
    if 'up_days' not in df.columns:
        df['up_days'] = (df['close'] > df['close'].shift(1)).rolling(5).sum()
    if 'down_days' not in df.columns:
        df['down_days'] = (df['close'] < df['close'].shift(1)).rolling(5).sum()
    
    # 量价相关性 (5日)
    if 'vol_price_corr' not in df.columns:
        df['vol_price_corr'] = df['close'].rolling(5).corr(df['volume'] if 'volume' in df.columns else df['vol5'])
    
    # 价格突破信号
    if 'break_high' not in df.columns:
        high_20 = df['close'].rolling(20).max()
        df['break_high'] = (df['close'] >= high_20 * 0.98).astype(float)
    if 'break_low' not in df.columns:
        low_20 = df['close'].rolling(20).min()
        df['break_low'] = (df['close'] <= low_20 * 1.02).astype(float)
    
    # 成交量突变
    if 'vol_spike' not in df.columns:
        vol_ma = df['volume'].rolling(20).mean() if 'volume' in df.columns else df['vol20']
        df['vol_spike'] = (df['volume'] if 'volume' in df.columns else df['vol5'] > vol_ma * 2).astype(float)
    
    # 斐波那契回撤位置 (基于20日高低)
    if 'fib_pos' not in df.columns:
        high_20 = df['close'].rolling(20).max()
        low_20 = df['close'].rolling(20).min()
        range_20 = high_20 - low_20
        df['fib_pos'] = (df['close'] - low_20) / range_20
    
    return df

# 定义最终特征集
FINAL_FEATURES_V2 = [
    # 原有14特征
    "p_ma5", "p_ma10", "p_ma20",
    "ma5_slope", "ma10_slope",
    "ret5", "ret10", "ret20",
    "rsi", "macd_hist",
    "kdj_k", "kdj_d",
    "vol_ratio", "boll_pos",
    
    # 扩展均线
    "p_ma60", "ma20_slope",
    
    # 成交量
    "vol5", "vol10", "vol20", "vol_ratio20",
    
    # MACD完整
    "macd_dif", "macd_dea",
    
    # KDJ完整
    "kdj_j",
    
    # 价格形态
    "hl_pct", "hc_pct", "cl_pct",
    
    # 新增技术指标
    "atr", "wr", "cci",
    "up_days", "down_days",
    "vol_price_corr",
    "break_high", "break_low", "vol_spike",
    "fib_pos",
]

print(f"\n最终特征集 V2: {len(FINAL_FEATURES_V2)} 个")
print("="*60)

# 保存特征定义
feature_config = {
    "version": "V2",
    "total_features": len(FINAL_FEATURES_V2),
    "features": FINAL_FEATURES_V2,
    "groups": FEATURE_GROUPS,
    "created_date": datetime.now().strftime('%Y-%m-%d %H:%M')
}

with open(os.path.join(MODEL_DIR, 'feature_config_v2.json'), 'w') as f:
    json.dump(feature_config, f, indent=2)

print(f"\n特征配置已保存: models/feature_config_v2.json")

# 检查每个特征在数据中的存在情况
print("\n特征存在情况检查:")
missing_total = []
for f in FINAL_FEATURES_V2:
    if f not in existing_cols:
        missing_total.append(f)
        print(f"  ❌ {f} - 需计算")
    else:
        print(f"  ✅ {f}")

print(f"\n总结:")
print(f"  已存在特征: {len(FINAL_FEATURES_V2) - len(missing_total)}")
print(f"  需新增计算: {len(missing_total)}")
print(f"  总特征数: {len(FINAL_FEATURES_V2)}")

print("\n完成:", datetime.now())