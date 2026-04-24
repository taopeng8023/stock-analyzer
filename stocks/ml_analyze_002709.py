#!/usr/bin/env python3
"""
天赐材料 (002709) ML模型分析
使用V5最优模型: 标准_5天5%
"""
import os
import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime

print("="*80)
print("天赐材料 (002709) ML模型分析")
print("="*80)
print(f"分析时间: {datetime.now()}")

MODEL_DIR = "models"
DATA_DIR = "data_history_2022_2026"

# 加载V5最优模型
print("\n加载V5最优模型 (标准_5天5%)...")
model_file = os.path.join(MODEL_DIR, "ml_v5_标准_5天5pct.pkl")

with open(model_file, 'rb') as f:
    model_data = pickle.load(f)

model = model_data['model']
scaler = model_data['scaler']
features = model_data['features']
strategy = model_data['strategy']
metrics = model_data['metrics']

print(f"策略: {strategy['name']}")
print(f"预测周期: {strategy['forward']}天")
print(f"目标收益: {strategy['profit']*100:.0f}%")
print(f"模型AUC: {metrics['auc']:.4f}")
print(f"推荐阈值: {metrics['threshold']}")

# 加载天赐材料数据
print("\n加载天赐材料数据...")
stock_file = os.path.join(DATA_DIR, "002709.json")

with open(stock_file, 'r') as f:
    data = json.load(f)

if 'items' in data:
    df = pd.DataFrame(data['items'], columns=data['fields'])
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    df = df.sort_values('trade_date').reset_index(drop=True)
    
    print(f"数据范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
    print(f"数据条数: {len(df)}")
    
    # 计算特征
    def compute_features(df):
        # 价格均线位置
        df['p_ma5'] = df['close'] / df['close'].rolling(5).mean()
        df['p_ma10'] = df['close'] / df['close'].rolling(10).mean()
        df['p_ma20'] = df['close'] / df['close'].rolling(20).mean()
        df['p_ma60'] = df['close'] / df['close'].rolling(60).mean()
        
        # 均线斜率
        df['ma5_slope'] = df['close'].rolling(5).mean().pct_change()
        df['ma10_slope'] = df['close'].rolling(10).mean().pct_change()
        df['ma20_slope'] = df['close'].rolling(20).mean().pct_change()
        
        # 收益率
        df['ret1'] = df['close'].pct_change()
        df['ret5'] = df['close'].pct_change(5)
        df['ret10'] = df['close'].pct_change(10)
        df['ret20'] = df['close'].pct_change(20)
        
        # 波动率
        df['vol5'] = df['ret1'].rolling(5).std()
        df['vol10'] = df['ret1'].rolling(10).std()
        df['vol20'] = df['ret1'].rolling(20).std()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd_dif'] = ema12 - ema26
        df['macd_dea'] = df['macd_dif'].ewm(span=9).mean()
        df['macd_hist'] = df['macd_dif'] - df['macd_dea']
        
        # KDJ
        low_min = df['low'].rolling(9).min()
        high_max = df['high'].rolling(9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        df['kdj_k'] = rsv.ewm(alpha=1/3).mean()
        df['kdj_d'] = df['kdj_k'].ewm(alpha=1/3).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        # 成交量比
        df['vol_ratio'] = df['vol'] / df['vol'].rolling(5).mean()
        df['vol_ratio20'] = df['vol'] / df['vol'].rolling(20).mean()
        
        # 价格形态
        df['hl_pct'] = (df['high'] - df['low']) / df['close']
        df['hc_pct'] = (df['high'] - df['close']) / df['close']
        df['cl_pct'] = (df['close'] - df['low']) / df['close']
        
        # 布林带位置
        mid = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        df['boll_pos'] = (df['close'] - mid) / (2 * std)
        
        return df
    
    df = compute_features(df)
    
    # 最近30天数据
    recent = df.tail(60).copy()
    
    # 预测
    X = recent[features].fillna(0).values.astype(np.float32)
    X_scaled = scaler.transform(X)
    
    y_prob = model.predict_proba(X_scaled)[:, 1]
    
    # 最近10天的预测结果
    print("\n" + "="*80)
    print("最近10天预测结果")
    print("="*80)
    
    print("\n| 日期 | 收盘价 | 置信度 | 预测信号 | RSI | MACD |")
    print("|------|--------|--------|----------|-----|------|")
    
    threshold = metrics['threshold']
    
    for i in range(-10, 0):
        row = recent.iloc[i]
        prob = y_prob[i]
        signal = "✅买入" if prob >= threshold else "观望"
        
        print(f"| {row['trade_date'].strftime('%Y-%m-%d')} | {row['close']:.2f} | {prob:.1%} | {signal} | {row['rsi']:.1f} | {row['macd_hist']:.3f} |")
    
    # 最新预测
    latest = recent.iloc[-1]
    latest_prob = y_prob[-1]
    
    print("\n" + "="*80)
    print("今日分析结论")
    print("="*80)
    
    print(f"\n📊 天赐材料 (002709)")
    print(f"   最新收盘: ¥{latest['close']:.2f}")
    print(f"   预测置信度: {latest_prob:.1%}")
    print(f"   买入阈值: {threshold:.0%}")
    
    if latest_prob >= threshold:
        print(f"\n✅ **买入信号**")
        print(f"   置信度 {latest_prob:.1%} >= 阈值 {threshold:.0%}")
        print(f"   预测: 5天内涨幅超过5%")
        
        # 技术指标确认
        print(f"\n📈 技术指标确认:")
        
        if latest['rsi'] < 30:
            print(f"   RSI={latest['rsi']:.1f} 超卖区域 ✅")
        elif latest['rsi'] > 70:
            print(f"   RSI={latest['rsi']:.1f} 超买区域 ⚠️")
        else:
            print(f"   RSI={latest['rsi']:.1f} 正常区间")
        
        if latest['macd_hist'] > 0:
            print(f"   MACD柱={latest['macd_hist']:.3f} 正值 ✅")
        else:
            print(f"   MACD柱={latest['macd_hist']:.3f} 负值 ⚠️")
        
        if latest['kdj_j'] < 20:
            print(f"   KDJ_J={latest['kdj_j']:.1f} 超卖 ✅")
        elif latest['kdj_j'] > 80:
            print(f"   KDJ_J={latest['kdj_j']:.1f} 超买 ⚠️")
        else:
            print(f"   KDJ_J={latest['kdj_j']:.1f} 正常")
        
        # 均线位置
        print(f"\n📉 均线位置:")
        print(f"   MA5: {latest['p_ma5']*100:.1f}%")
        print(f"   MA10: {latest['p_ma10']*100:.1f}%")
        print(f"   MA20: {latest['p_ma20']*100:.1f}%")
        
        if latest['p_ma5'] > 1 and latest['p_ma10'] > 1:
            print(f"   价格在均线上方 ✅")
        else:
            print(f"   价格在均线附近/下方 ⚠️")
        
        # 综合评分
        score = 0
        if latest_prob >= threshold: score += 30
        if latest['rsi'] < 50: score += 20
        if latest['macd_hist'] > 0: score += 20
        if latest['kdj_j'] < 50: score += 15
        if latest['p_ma5'] > latest['p_ma10']: score += 15
        
        print(f"\n🎯 综合评分: {score}/100")
        
        if score >= 70:
            print(f"   强烈推荐买入 ⭐⭐⭐")
        elif score >= 50:
            print(f"   建议买入 ⭐⭐")
        else:
            print(f"   可考虑买入 ⭐")
            
    else:
        print(f"\n⏸️ **观望信号**")
        print(f"   置信度 {latest_prob:.1%} < 阈值 {threshold:.0%}")
        print(f"   建议: 等待置信度提升")
    
    # 风险提示
    print("\n⚠️ 风险提示:")
    print("   1. 模型基于历史数据，未来存在不确定性")
    print("   2. 单只股票分析需结合仓位管理")
    print("   3. 建议设置止损位保护")

else:
    print("数据格式异常")