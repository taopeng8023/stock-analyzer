#!/usr/bin/env python3
"""
天赐材料 (002709) 多模型对比分析
"""
import os
import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime

print("="*80)
print("天赐材料 (002709) 多模型对比分析")
print("="*80)

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 加载多个模型
models = [
    ("ml_v5_标准_5天5pct.pkl", "5天5%", 0.9),
    ("ml_v5_短攻_3天5pct.pkl", "3天5%", 0.8),
    ("ml_v5_短攻_3天3pct.pkl", "3天3%", 0.9),
    ("ml_v5_超短_3天2pct.pkl", "3天2%", 0.9),
]

# 加载天赐材料数据
stock_file = os.path.join(DATA_DIR, "002709.json")
with open(stock_file, 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data['items'], columns=data['fields'])
df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
df = df.sort_values('trade_date').reset_index(drop=True)

print(f"最新数据: {df['trade_date'].max().strftime('%Y-%m-%d')}")
print(f"最新收盘: ¥{df['close'].iloc[-1]:.2f}")

# 计算特征
def compute_features(df):
    df['p_ma5'] = df['close'] / df['close'].rolling(5).mean()
    df['p_ma10'] = df['close'] / df['close'].rolling(10).mean()
    df['p_ma20'] = df['close'] / df['close'].rolling(20).mean()
    df['p_ma60'] = df['close'] / df['close'].rolling(60).mean()
    
    df['ma5_slope'] = df['close'].rolling(5).mean().pct_change()
    df['ma10_slope'] = df['close'].rolling(10).mean().pct_change()
    df['ma20_slope'] = df['close'].rolling(20).mean().pct_change()
    
    df['ret1'] = df['close'].pct_change()
    df['ret5'] = df['close'].pct_change(5)
    df['ret10'] = df['close'].pct_change(10)
    df['ret20'] = df['close'].pct_change(20)
    
    df['vol5'] = df['ret1'].rolling(5).std()
    df['vol10'] = df['ret1'].rolling(10).std()
    df['vol20'] = df['ret1'].rolling(20).std()
    
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd_dif'] = ema12 - ema26
    df['macd_dea'] = df['macd_dif'].ewm(span=9).mean()
    df['macd_hist'] = df['macd_dif'] - df['macd_dea']
    
    low_min = df['low'].rolling(9).min()
    high_max = df['high'].rolling(9).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    df['kdj_k'] = rsv.ewm(alpha=1/3).mean()
    df['kdj_d'] = df['kdj_k'].ewm(alpha=1/3).mean()
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
    
    df['vol_ratio'] = df['vol'] / df['vol'].rolling(5).mean()
    df['vol_ratio20'] = df['vol'] / df['vol'].rolling(20).mean()
    
    df['hl_pct'] = (df['high'] - df['low']) / df['close']
    df['hc_pct'] = (df['high'] - df['close']) / df['close']
    df['cl_pct'] = (df['close'] - df['low']) / df['close']
    
    mid = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['boll_pos'] = (df['close'] - mid) / (2 * std)
    
    return df

df = compute_features(df)
recent = df.tail(30)

print("\n" + "="*80)
print("多模型预测对比")
print("="*80)

print("\n| 模型 | 目标 | 周期 | 置信度 | 阈值 | 信号 |")
print("|------|------|------|--------|------|------|")

results = []

for model_file, name, thresh in models:
    path = os.path.join(MODEL_DIR, model_file)
    if not os.path.exists(path):
        continue
    
    with open(path, 'rb') as f:
        data = pickle.load(f)
    
    model = data['model']
    scaler = data['scaler']
    features = data['features']
    
    X = recent[features].fillna(0).values.astype(np.float32)
    X_scaled = scaler.transform(X)
    
    prob = model.predict_proba(X_scaled)[-1, 1]
    signal = "买入✅" if prob >= thresh else "观望"
    
    parts = name.split('天')
    days = parts[0] + "天"
    pct = parts[1]
    
    print(f"| {name} | {pct} | {days} | {prob:.1%} | {thresh:.0%} | {signal} |")
    
    results.append({
        'name': name,
        'prob': prob,
        'thresh': thresh,
        'signal': signal,
    })

# 技术指标
print("\n" + "="*80)
print("技术指标分析")
print("="*80)

latest = df.iloc[-1]

print(f"\n📊 天赐材料 (002709)")
print(f"   收盘价: ¥{latest['close']:.2f}")
print(f"   日涨跌: {latest['ret1']*100:.2f}%")

print(f"\n📈 技术指标:")
print(f"   RSI: {latest['rsi']:.1f}")
if latest['rsi'] < 30:
    print(f"      → 超卖区域，可能反弹")
elif latest['rsi'] > 70:
    print(f"      → 超买区域，注意风险")
else:
    print(f"      → 正常区间")

print(f"   MACD柱: {latest['macd_hist']:.3f}")
if latest['macd_hist'] > 0:
    print(f"      → 多头趋势")
else:
    print(f"      → 空头趋势")

print(f"   KDJ_K: {latest['kdj_k']:.1f}")
print(f"   KDJ_D: {latest['kdj_d']:.1f}")
print(f"   KDJ_J: {latest['kdj_j']:.1f}")

print(f"\n📉 均线位置:")
print(f"   MA5偏离: {(latest['p_ma5']-1)*100:.2f}%")
print(f"   MA10偏离: {(latest['p_ma10']-1)*100:.2f}%")
print(f"   MA20偏离: {(latest['p_ma20']-1)*100:.2f}%")

if latest['p_ma5'] > 1.02:
    print(f"      → 短期强势")
elif latest['p_ma5'] < 0.98:
    print(f"      → 短期弱势")

# 综合判断
print("\n" + "="*80)
print("综合判断")
print("="*80)

buy_signals = sum(1 for r in results if r['signal'] == "买入✅")
max_prob = max(r['prob'] for r in results)

print(f"\n模型信号: {buy_signals}/{len(results)} 个建议买入")
print(f"最高置信度: {max_prob:.1%}")

# 结合持仓信息
print(f"\n💡 持仓建议:")
print(f"   当前持仓: 500股 @ ¥48.25")
print(f"   最新价格: ¥{latest['close']:.2f}")
print(f"   当前盈亏: {(latest['close']/48.25-1)*100:.2f}%")

if buy_signals >= 2 or max_prob >= 0.5:
    print(f"\n✅ 建议: 继续持有/加仓")
    print(f"   多模型看好，技术面配合")
else:
    print(f"\n⏸️ 建议: 持有观望")
    print(f"   等待更好入场时机")

print(f"\n⚠️ 止损位建议: ¥43.50 (约-10%)")