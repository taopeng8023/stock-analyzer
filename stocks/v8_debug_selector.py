#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 模型调试选股脚本
诊断特征计算和预测置信度分布
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
import sys
import random
warnings.filterwarnings('ignore')

# 配置
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")

# V8 特征列表 (28 维)
V8_FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
    'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
    'momentum10', 'vol_change', 'price_position',
    'volatility_rank', 'recent_return', 'acceleration',
    'up_days_ratio', 'momentum_strength',
    'vol_price_corr', 'vol_trend', 'momentum_accel', 'trend_strength',
    'volatility_trend', 'range_ratio', 'money_flow_proxy', 'money_flow_ma'
]

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

class V8DebugSelector:
    """V8 调试选股器"""
    
    def __init__(self):
        self.models = []
        self.features = V8_FEATURES
        self.load_models()
    
    def load_models(self):
        """加载 V8 集成模型"""
        log(f"\n{'='*60}")
        log("V8 模型调试诊断")
        log(f"{'='*60}")
        
        model_names = [
            'ml_nn_v8_model1_seed42.pkl',
            'ml_nn_v8_model2_seed123.pkl',
            'ml_nn_v8_model3_seed456.pkl',
            'ml_nn_v8_model4_seed789.pkl',
            'ml_nn_v8_model5_seed1024.pkl'
        ]
        
        for i, model_name in enumerate(model_names):
            model_path = MODEL_DIR / model_name
            log(f"加载模型 {i+1}/5: {model_name}")
            
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
            
            self.models.append(data['model'])
        
        log(f"\n模型加载完成：5 个子模型")
    
    def extract_features_df(self, df):
        """使用 pandas 计算 V8 特征"""
        # 基础特征
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
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - 100 / (1 + rs)
        
        # 成交量
        df['vol_ma5'] = df['vol'].rolling(5).mean()
        df['vol_ratio'] = df['vol'] / (df['vol_ma5'] + 1e-10)
        
        # 布林带
        df['ma20_roll'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['boll_upper'] = df['ma20_roll'] + 2 * df['std20']
        df['boll_lower'] = df['ma20_roll'] - 2 * df['std20']
        df['boll_pos'] = (df['close'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'] + 1e-10)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_hist'] = df['macd'] - df['macd'].ewm(span=9, adjust=False).mean()
        
        # KDJ
        low_9 = df['low'].rolling(9).min()
        high_9 = df['high'].rolling(9).max()
        df['kdj_k'] = 100 * (df['close'] - low_9) / (high_9 - low_9 + 1e-10)
        
        # V5 特征
        df['momentum10'] = (df['close'] / df['close'].shift(10) - 1).clip(-0.9, 5)
        
        df['volatility5'] = df['ret5'].rolling(5).std()
        df['volatility10'] = df['ret5'].rolling(10).std()
        df['vol_change'] = (df['volatility5'] / (df['volatility10'] + 1e-10)).clip(0.1, 10)
        
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        df['price_position'] = ((df['close'] - low_20) / (high_20 - low_20 + 1e-10)).clip(0, 1)
        
        # V7 特征
        df['recent_return'] = df['close'].pct_change(3)
        df['acceleration'] = df['recent_return'] - df['recent_return'].shift(3)
        df['volatility_rank'] = df['volatility5'].rolling(60).rank(pct=True)
        df['up_days_ratio'] = (df['pct_chg'] > 0).rolling(10).mean()
        df['momentum_strength'] = (df['ret5'] - df['ret10']).clip(-0.5, 0.5)
        
        # V8 特征
        df['vol_price_corr'] = df['vol'].rolling(20).corr(df['close']).fillna(0).clip(-1, 1)
        df['vol_trend'] = (df['vol_ma5'] / (df['vol'].rolling(20).mean() + 1e-10)).clip(0.5, 2.0)
        df['momentum_accel'] = (df['ret5'] - df['ret5'].shift(5)).clip(-0.5, 0.5)
        df['trend_strength'] = (df['ma5'] - df['ma20']) / (df['ma20'] + 1e-10)
        df['volatility_trend'] = (df['volatility5'] / (df['volatility5'].shift(5) + 1e-10)).clip(0.5, 2.0)
        df['range_ratio'] = (df['high'] - df['low']) / (df['close'] + 1e-10)
        df['money_flow_proxy'] = (df['vol'] * df['pct_chg'] / 1e6).clip(-100, 100)
        df['money_flow_ma'] = df['money_flow_proxy'].rolling(5).mean()
        
        return df
    
    def predict_ensemble(self, feature_vector):
        """集成模型预测"""
        try:
            feature_vector = np.array(feature_vector).reshape(1, -1)
            
            probs = []
            for model in self.models:
                prob = model.predict_proba(feature_vector)[0][1]
                probs.append(prob)
            
            avg_prob = np.mean(probs)
            std_prob = np.std(probs)
            
            return avg_prob, std_prob
        except Exception as e:
            return 0.0, 0.0
    
    def analyze_stock(self, stock_file):
        """分析单只股票"""
        try:
            with open(stock_file, 'r') as f:
                data = json.load(f)
            
            items = data.get('items', [])
            if len(items) < 100:
                return None
            
            fields = data.get('fields', [])
            idx_map = {name: i for i, name in enumerate(fields)}
            
            required = ['trade_date', 'close', 'open', 'high', 'low', 'vol', 'pct_chg']
            if not all(r in idx_map for r in required):
                return None
            
            # 构建 DataFrame
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
            
            # 计算特征
            df = self.extract_features_df(df)
            
            # 获取最新数据
            last_row = df.iloc[-1]
            
            # 检查 NaN
            feature_values = [last_row.get(f, np.nan) for f in self.features]
            nan_count = sum(1 for v in feature_values if np.isnan(v))
            
            if nan_count > 0:
                return {
                    'code': stock_file.stem,
                    'error': f'{nan_count}个NaN特征',
                    'nan_features': [f for f, v in zip(self.features, feature_values) if np.isnan(v)][:5]
                }
            
            # 预测
            prob, std = self.predict_ensemble(feature_values)
            
            return {
                'code': stock_file.stem,
                'price': last_row['close'],
                'rsi': last_row['rsi'],
                'confidence': prob,
                'std': std,
                'features': {f: v for f, v in zip(self.features, feature_values)}
            }
        
        except Exception as e:
            return {
                'code': stock_file.stem,
                'error': str(e)
            }
    
    def run_debug(self, n_samples=50):
        """运行调试分析"""
        log(f"\n随机抽取 {n_samples} 只股票进行诊断...")
        
        stock_files = list(HISTORY_DIR.glob('*.json'))
        sampled_files = random.sample(stock_files, min(n_samples, len(stock_files)))
        
        results = []
        confidences = []
        
        for idx, stock_file in enumerate(sampled_files):
            result = self.analyze_stock(stock_file)
            if result:
                results.append(result)
                if 'confidence' in result:
                    confidences.append(result['confidence'])
            
            if (idx + 1) % 10 == 0:
                log(f"已分析 {idx+1}/{len(sampled_files)} 只股票...")
        
        return results, confidences
    
    def print_statistics(self, results, confidences):
        """打印统计信息"""
        log(f"\n{'='*60}")
        log("📊 诊断结果")
        log(f"{'='*60}")
        
        # 置信度统计
        if confidences:
            log(f"\n【置信度分布】")
            log(f"  平均值：{np.mean(confidences)*100:.1f}%")
            log(f"  中位数：{np.median(confidences)*100:.1f}%")
            log(f"  标准差：{np.std(confidences)*100:.1f}%")
            log(f"  最小值：{np.min(confidences)*100:.1f}%")
            log(f"  最大值：{np.max(confidences)*100:.1f}%")
            
            log(f"\n【置信度区间】")
            log(f"  ≥90%: {sum(1 for c in confidences if c >= 0.90)} 只 ({sum(1 for c in confidences if c >= 0.90)/len(confidences)*100:.1f}%)")
            log(f"  ≥85%: {sum(1 for c in confidences if c >= 0.85)} 只 ({sum(1 for c in confidences if c >= 0.85)/len(confidences)*100:.1f}%)")
            log(f"  ≥80%: {sum(1 for c in confidences if c >= 0.80)} 只 ({sum(1 for c in confidences if c >= 0.80)/len(confidences)*100:.1f}%)")
            log(f"  ≥75%: {sum(1 for c in confidences if c >= 0.75)} 只 ({sum(1 for c in confidences if c >= 0.75)/len(confidences)*100:.1f}%)")
            log(f"  ≥70%: {sum(1 for c in confidences if c >= 0.70)} 只 ({sum(1 for c in confidences if c >= 0.70)/len(confidences)*100:.1f}%)")
        else:
            log(f"\n⚠️  无有效置信度数据")
        
        # 错误统计
        errors = [r for r in results if 'error' in r]
        if errors:
            log(f"\n【错误统计】")
            log(f"  错误数量：{len(errors)}/{len(results)}")
            error_types = {}
            for e in errors:
                err_type = e.get('error', 'Unknown')[:30]
                error_types[err_type] = error_types.get(err_type, 0) + 1
            for err_type, count in sorted(error_types.items(), key=lambda x: -x[1])[:5]:
                log(f"  - {err_type}: {count}")
        
        # 特征值范围检查
        valid_results = [r for r in results if 'features' in r]
        if valid_results:
            log(f"\n【特征值范围检查】(前 10 个特征)")
            sample = valid_results[0]['features']
            for i, (feat, value) in enumerate(list(sample.items())[:10]):
                log(f"  {feat}: {value:.4f}")

def main():
    """主函数"""
    selector = V8DebugSelector()
    results, confidences = selector.run_debug(n_samples=100)
    selector.print_statistics(results, confidences)
    
    log(f"\n{'='*60}")
    log("💡 诊断结论")
    log(f"{'='*60}")
    
    if confidences:
        avg_conf = np.mean(confidences)
        if avg_conf < 0.5:
            log("\n⚠️  平均置信度偏低 (<50%), 可能原因:")
            log("  1. 特征计算与训练时不一致")
            log("  2. 当前市场特征与训练数据差异大")
            log("  3. 模型需要重新训练或微调")
        elif avg_conf < 0.7:
            log("\n⚠️  平均置信度中等 (50-70%), 建议:")
            log("  1. 降低选股置信度阈值 (如 70%)")
            log("  2. 检查特征计算逻辑")
        else:
            log(f"\n✅ 平均置信度正常 ({avg_conf*100:.1f}%)")
            log("  选股脚本工作正常，可适当放宽条件")
    
    log(f"\n{'='*60}")

if __name__ == '__main__':
    main()
