#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经网络选股系统

使用部署的神经网络模型进行实时选股
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# 配置
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
MODEL_PATH = Path('/home/admin/.openclaw/workspace/stocks/models/ml_nn_production.pkl')
OUTPUT_DIR = Path('/home/admin/.openclaw/workspace/stocks/selections')

# 特征列表 (14个核心特征)
FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20',      # 价格相对MA位置
    'ma5_slope', 'ma10_slope',         # MA斜率
    'ret5', 'ret10', 'ret20',          # 收益率
    'rsi',                              # RSI
    'macd_hist',                        # MACD柱
    'kdj_k', 'kdj_d',                   # KDJ
    'vol_ratio',                        # 量比
    'boll_pos'                          # 布林带位置
]

def calculate_features(data):
    """
    从历史数据计算特征
    
    Args:
        data: list of [ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount]
    
    Returns:
        dict: 特征字典
    """
    if len(data) < 30:
        return None
    
    # 转换为DataFrame (倒序，最新在前)
    df = pd.DataFrame(data, columns=['ts_code', 'date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount'])
    
    # 转换数值
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['open'] = df['open'].astype(float)
    df['vol'] = df['vol'].astype(float)
    
    # 反转顺序 (旧->新)
    df = df.iloc[::-1].reset_index(drop=True)
    
    # 取最近30天
    df = df.tail(30).reset_index(drop=True)
    
    close = df['close'].values
    
    try:
        # MA
        ma5 = np.mean(close[-5:])
        ma10 = np.mean(close[-10:])
        ma20 = np.mean(close[-20:])
        
        # 价格相对MA位置
        p_ma5 = close[-1] / ma5 - 1
        p_ma10 = close[-1] / ma10 - 1
        p_ma20 = close[-1] / ma20 - 1
        
        # MA斜率 (5日变化率)
        ma5_slope = (ma5 - np.mean(close[-10:-5])) / np.mean(close[-10:-5])
        ma10_slope = (ma10 - np.mean(close[-20:-10])) / np.mean(close[-20:-10])
        
        # 收益率
        ret5 = (close[-1] - close[-6]) / close[-6] if len(close) >= 6 else 0
        ret10 = (close[-1] - close[-11]) / close[-11] if len(close) >= 11 else 0
        ret20 = (close[-1] - close[-21]) / close[-21] if len(close) >= 21 else 0
        
        # RSI (14日)
        deltas = np.diff(close[-15:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = close[-1]  # 简化计算
        for i in range(12, 0, -1):
            ema12 = close[-i] * 0.154 + ema12 * 0.846
        ema26 = close[-1]
        for i in range(26, 0, -1):
            ema26 = close[-i] * 0.074 + ema26 * 0.926
        macd = ema12 - ema26
        macd_hist = macd  # 简化
        
        # KDJ
        low_min = np.min(df['low'].values[-9:])
        high_max = np.max(df['high'].values[-9:])
        rsv = (close[-1] - low_min) / (high_max - low_min) * 100 if high_max > low_min else 50
        kdj_k = rsv  # 简化
        kdj_d = 50  # 简化
        
        # 量比
        vol_avg = np.mean(df['vol'].values[-5:-1])
        vol_ratio = df['vol'].values[-1] / vol_avg if vol_avg > 0 else 1
        
        # 布林带位置
        std20 = np.std(close[-20:])
        boll_upper = ma20 + 2 * std20
        boll_lower = ma20 - 2 * std20
        boll_pos = (close[-1] - boll_lower) / (boll_upper - boll_lower) if boll_upper > boll_lower else 0.5
        
        return {
            'p_ma5': p_ma5,
            'p_ma10': p_ma10,
            'p_ma20': p_ma20,
            'ma5_slope': ma5_slope,
            'ma10_slope': ma10_slope,
            'ret5': ret5,
            'ret10': ret10,
            'ret20': ret20,
            'rsi': rsi,
            'macd_hist': macd_hist,
            'kdj_k': kdj_k,
            'kdj_d': kdj_d,
            'vol_ratio': vol_ratio,
            'boll_pos': boll_pos,
            'close': close[-1],
            'pct_chg': float(df['pct_chg'].values[-1])
        }
        
    except Exception as e:
        return None


def load_model():
    """加载模型"""
    with open(MODEL_PATH, 'rb') as f:
        data = pickle.load(f)
    
    return {
        'model': data['model'],
        'scaler': data['scaler'],
        'features': data['features'],
        'metadata': data['metadata']
    }


def main():
    print("="*60)
    print("神经网络选股系统")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 加载模型
    print("\n[1] 加载模型...")
    model_data = load_model()
    model = model_data['model']
    scaler = model_data['scaler']
    feature_list = model_data['features']
    
    print(f"   模型AUC: {model_data['metadata']['auc']}")
    print(f"   90%精确率: {model_data['metadata']['precision_90']}")
    
    # 获取所有股票文件
    print("\n[2] 扫描股票数据...")
    json_files = list(DATA_DIR.glob('*.json'))
    print(f"   股票数量: {len(json_files)}")
    
    # 计算特征并预测
    print("\n[3] 特征计算 & 预测...")
    
    results = []
    error_count = 0
    
    for i, jf in enumerate(json_files):
        try:
            with open(jf, 'r') as f:
                data = json.load(f)
            
            items = data['items']
            if len(items) < 30:
                continue
            
            # 计算特征
            features = calculate_features(items)
            if not features:
                continue
            
            # 提取模型需要的特征
            X = np.array([[features.get(f, 0) for f in feature_list]])
            
            # 标准化
            X_scaled = scaler.transform(X)
            
            # 预测概率
            prob = model.predict_proba(X_scaled)[0, 1]
            
            # 记录结果
            code = jf.stem
            results.append({
                'code': code,
                'prob': prob,
                'close': features['close'],
                'pct_chg': features['pct_chg'],
                'p_ma5': features['p_ma5'],
                'p_ma10': features['p_ma10'],
                'rsi': features['rsi'],
                'vol_ratio': features['vol_ratio']
            })
            
        except Exception as e:
            error_count += 1
        
        if (i + 1) % 1000 == 0:
            print(f"   进度: {i+1}/{len(json_files)}")
    
    print(f"   完成: {len(results)} | 错误: {error_count}")
    
    # 排序并筛选
    print("\n[4] 选股结果...")
    
    results.sort(key=lambda x: x['prob'], reverse=True)
    
    # 不同置信度阈值
    high_conf = [r for r in results if r['prob'] >= 0.85]
    very_high = [r for r in results if r['prob'] >= 0.90]
    
    print(f"\n   高置信度 (≥85%): {len(high_conf)} 只")
    print(f"   极高置信度 (≥90%): {len(very_high)} 只")
    
    # 输出TOP20
    print("\n" + "="*60)
    print("TOP 20 高置信度股票")
    print("="*60)
    print(f"{'代码':<8} {'概率':<8} {'收盘':<10} {'涨跌%':<8} {'MA5偏离':<10} {'RSI':<8} {'量比':<8}")
    print("-"*60)
    
    for i, r in enumerate(results[:20]):
        print(f"{r['code']:<8} {r['prob']:.2%}   {r['close']:<10.2f} {r['pct_chg']:<8.2f} {r['p_ma5']:<10.2%} {r['rsi']:<8.1f} {r['vol_ratio']:<8.2f}")
    
    # 保存结果
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    output_file = OUTPUT_DIR / f"neural_selection_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    
    output_data = {
        'date': datetime.now().strftime('%Y%m%d'),
        'time': datetime.now().strftime('%H:%M'),
        'model_auc': model_data['metadata']['auc'],
        'model_precision_90': model_data['metadata']['precision_90'],
        'total_scanned': len(json_files),
        'valid_results': len(results),
        'high_confidence_85': len(high_conf),
        'very_high_confidence_90': len(very_high),
        'top_20': results[:20],
        'all_results': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存: {output_file}")
    
    # 简短报告
    print("\n" + "="*60)
    print("选股摘要")
    print("="*60)
    print(f"扫描股票: {len(json_files)} 只")
    print(f"有效预测: {len(results)} 只")
    print(f"高置信度: {len(high_conf)} 只 (≥85%)")
    print(f"极高置信度: {len(very_high)} 只 (≥90%)")
    print("="*60)
    
    return results


if __name__ == '__main__':
    main()