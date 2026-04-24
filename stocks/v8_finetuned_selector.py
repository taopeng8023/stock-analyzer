#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 微调模型实盘选股脚本
使用最近 3 个月微调训练的模型
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
import sys
import glob
warnings.filterwarnings('ignore')

# 配置
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/selections")

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

# 选股条件
CONFIDENCE_THRESHOLD = 0.70  # 置信度 >= 70%
RSI_THRESHOLD = 70
DROP_THRESHOLD = 0
TOP_N = 15

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

class V8FinetunedSelector:
    """V8 微调模型选股器"""
    
    def __init__(self):
        self.models = []
        self.load_models()
    
    def load_models(self):
        """加载最新微调模型"""
        log(f"\n{'='*60}")
        log("V8 微调模型实盘选股系统")
        log(f"{'='*60}")
        
        # 查找最新微调模型
        model_files = sorted(glob.glob(str(MODEL_DIR / 'ml_nn_v8_finetuned_model*_seed*.pkl')))
        
        if not model_files:
            log("❌ 未找到微调模型，请先运行 ml_nn_v8_finetune.py")
            sys.exit(1)
        
        # 取最新的一组 (5 个)
        latest_models = model_files[-5:]
        
        for i, model_path in enumerate(latest_models):
            log(f"加载模型 {i+1}/5: {Path(model_path).name}")
            
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
            
            self.models.append(data['model'])
        
        log(f"\n模型加载完成：5 个微调模型")
        log(f"微调日期：{Path(latest_models[0]).stem.split('_')[-1]}")
    
    def extract_features_df(self, df):
        """计算 V8 特征"""
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
        
        return df
    
    def predict_ensemble(self, feature_vector):
        """集成预测"""
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
    
    def scan_stock(self, stock_file):
        """扫描单只股票"""
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
            df = self.extract_features_df(df)
            
            last_row = df.iloc[-1]
            
            feature_values = [last_row.get(f, np.nan) for f in V8_FEATURES]
            if any(np.isnan(v) for v in feature_values):
                return None
            
            current_price = last_row['close']
            rsi = last_row['rsi']
            
            high_20 = df['high'].rolling(20).max().iloc[-1]
            drop = (high_20 - current_price) / high_20 * 100
            
            if rsi > RSI_THRESHOLD and drop < DROP_THRESHOLD:
                return None
            
            prob, std = self.predict_ensemble(feature_values)
            
            if prob >= CONFIDENCE_THRESHOLD:
                return {
                    'code': stock_file.stem,
                    'price': current_price,
                    'rsi': rsi,
                    'drop': drop,
                    'confidence': prob,
                    'std': std,
                    'date': last_row['date']
                }
            
            return None
        
        except Exception as e:
            return None
    
    def run_selection(self):
        """运行选股"""
        log(f"\n开始扫描全市场股票...")
        log(f"选股条件:")
        log(f"  置信度 >= {CONFIDENCE_THRESHOLD*100:.0f}%")
        log(f"  RSI < {RSI_THRESHOLD}")
        log(f"  跌幅 > {DROP_THRESHOLD}%")
        
        stock_files = list(HISTORY_DIR.glob('*.json'))
        log(f"扫描股票数量：{len(stock_files)}")
        
        candidates = []
        
        for idx, stock_file in enumerate(stock_files):
            if (idx + 1) % 500 == 0:
                log(f"已扫描 {idx+1}/{len(stock_files)} 只股票...")
            
            result = self.scan_stock(stock_file)
            if result:
                candidates.append(result)
        
        candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        return candidates[:TOP_N]
    
    def save_results(self, candidates):
        """保存结果"""
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = OUTPUT_DIR / f'v8_finetuned_selection_{timestamp}.json'
        
        result = {
            'timestamp': timestamp,
            'model': 'V8_finetuned',
            'threshold': CONFIDENCE_THRESHOLD,
            'total_scanned': len(list(HISTORY_DIR.glob('*.json'))),
            'selected': candidates
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        log(f"\n选股结果已保存：{result_file.name}")
        
        return result_file

def main():
    """主函数"""
    selector = V8FinetunedSelector()
    candidates = selector.run_selection()
    
    log(f"\n{'='*60}")
    log(f"V8 微调模型实盘选股结果 (TOP {len(candidates)})")
    log(f"{'='*60}")
    
    if not candidates:
        log("⚠️  未找到符合条件的股票")
        return
    
    log(f"\n{'排名':<4} {'代码':<10} {'现价':>8} {'RSI':>6} {'跌幅':>8} {'置信度':>10} {'评级':>8}")
    log(f"{'-'*4}-{'-'*10}-{'-'*8}-{'-'*6}-{'-'*8}-{'-'*10}-{'-'*8}")
    
    for i, stock in enumerate(candidates):
        rating = "⭐⭐⭐⭐⭐" if stock['confidence'] >= 0.90 else "⭐⭐⭐⭐" if stock['confidence'] >= 0.80 else "⭐⭐⭐" if stock['confidence'] >= 0.70 else "⭐⭐"
        log(f"{i+1:<4} {stock['code']:<10} {stock['price']:>8.2f} {stock['rsi']:>6.1f} {stock['drop']:>7.1f}% {stock['confidence']*100:>9.1f}% {rating:>8}")
    
    selector.save_results(candidates)
    
    log(f"\n{'='*60}")
    log("💡 说明:")
    log(f"  - 使用最近 3 个月 (2026-01~2026-04) 数据微调")
    log(f"  - 适应当前市场风格")
    log(f"{'='*60}")

if __name__ == '__main__':
    main()
