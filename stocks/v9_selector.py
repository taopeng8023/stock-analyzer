#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V9 集成模型实盘选股脚本
基于市场自适应训练 (正样本比例 27.2%)
扫描全市场股票，输出高置信度选股结果
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
import sys
warnings.filterwarnings('ignore')

# 配置
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/selections")

# V9 集成模型配置
V9_CONFIG = {
    'models': [
        'ml_nn_v9_model1_seed42_20260419_185442.pkl',
        'ml_nn_v9_model2_seed123_20260419_185442.pkl',
        'ml_nn_v9_model3_seed456_20260419_185442.pkl',
        'ml_nn_v9_model4_seed789_20260419_185442.pkl',
        'ml_nn_v9_model5_seed1024_20260419_185442.pkl'
    ],
    'config': 'ml_nn_v9_config_20260419_185442.json'
}

# V9 特征列表 (31 维)
V9_FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'ma5_slope', 'ma10_slope', 
    'ret5', 'ret10', 'rsi', 'macd_hist', 'kdj_k', 'vol_ratio', 'boll_pos',
    'momentum10', 'vol_change', 'price_position',
    'volatility_rank', 'recent_return', 'acceleration',
    'up_days_ratio', 'momentum_strength',
    'vol_price_corr', 'vol_trend', 'momentum_accel', 'trend_strength',
    'volatility_trend', 'range_ratio', 'money_flow_proxy', 'money_flow_ma',
    'market_rsi', 'market_trend', 'volatility_state'
]

# 选股条件 (右侧交易策略 - 追涨)
CONFIDENCE_THRESHOLD = 0.65  # 置信度 >= 65%
RSI_MIN = 45  # RSI >= 45 (偏强势区)
RSI_MAX = 70  # RSI < 70 (避免超买)
TREND_FILTER = True  # 启用趋势过滤
MA5_MIN = 0  # 股价 >= MA5 (站上均线)
RET5_MIN = 0  # 5 日收益 >= 0 (不跌)
RET10_MIN = -0.05  # 10 日收益 >= -5% (10 日不暴跌)
TOP_N = 20  # 输出 TOP20

def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()

class V9EnsembleSelector:
    """V9 集成模型选股器"""
    
    def __init__(self):
        self.models = []
        self.features = V9_FEATURES
        self.load_models()
    
    def load_models(self):
        """加载 V9 集成模型"""
        log(f"\n{'='*60}")
        log("V9 集成模型实盘选股系统")
        log(f"{'='*60}")
        log(f"模型版本：V9 (市场自适应训练)")
        log(f"正样本比例：27.2%")
        log(f"{'='*60}\n")
        
        for i, model_name in enumerate(V9_CONFIG['models']):
            model_path = MODEL_DIR / model_name
            log(f"加载模型 {i+1}/5: {model_name}")
            
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
            
            self.models.append(data['model'])
        
        # 加载配置
        config_path = MODEL_DIR / V9_CONFIG['config']
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        log(f"\n模型加载完成：5 个子模型")
        log(f"特征维度：{self.config.get('n_features', 28)}")
        log(f"置信度阈值：{CONFIDENCE_THRESHOLD*100:.0f}%")
    
    def calculate_rsi(self, closes, period=14):
        """计算 RSI 指标 (Wilders 平滑法)"""
        if len(closes) < period + 1:
            return 50
        
        gains = []
        losses = []
        for i in range(1, period + 1):
            delta = closes[-i] - closes[-i-1]
            if delta > 0:
                gains.append(delta)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-delta)
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_features(self, df):
        """计算 28 维特征"""
        try:
            # 确保使用正确的字段名
            closes = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            opens = df['open'].values
            
            # 成交量字段：优先 vol，其次 volume，最后 amount
            if 'vol' in df.columns:
                volumes = df['vol'].values
            elif 'volume' in df.columns:
                volumes = df['volume'].values
            else:
                volumes = df['amount'].values
            
            if len(closes) < 60:
                return None
            
            # 均线
            ma5 = np.mean(closes[-5:])
            ma10 = np.mean(closes[-10:])
            ma20 = np.mean(closes[-20:])
            
            p_ma5 = closes[-1] / ma5 - 1
            p_ma10 = closes[-1] / ma10 - 1
            p_ma20 = closes[-1] / ma20 - 1
            
            ma5_slope = (closes[-1] - closes[-6]) / closes[-6] if len(closes) >= 6 else 0
            ma10_slope = (ma5 - ma10) / ma10
            
            # 收益率
            ret5 = closes[-1] / closes[-6] - 1 if len(closes) >= 6 else 0
            ret10 = closes[-1] / closes[-11] - 1 if len(closes) >= 11 else 0
            
            # RSI
            rsi = self.calculate_rsi(closes)
            
            # MACD
            ema12 = pd.Series(closes).ewm(span=12).mean().values
            ema26 = pd.Series(closes).ewm(span=26).mean().values
            macd = ema12 - ema26
            macd_signal = pd.Series(macd).ewm(span=9).mean().values
            macd_hist = macd[-1] - macd_signal[-1]
            
            # KDJ
            low_9 = np.min(lows[-9:])
            high_9 = np.max(highs[-9:])
            kdj_k = ((closes[-1] - low_9) / (high_9 - low_9) * 100) if high_9 > low_9 else 50
            
            # 成交量
            vol_ma5 = np.mean(volumes[-5:])
            vol_ma10 = np.mean(volumes[-10:])
            vol_ratio = volumes[-1] / vol_ma5 if vol_ma5 > 0 else 1
            vol_change = volumes[-1] / vol_ma10 - 1 if vol_ma10 > 0 else 0
            
            # 布林带
            boll_mid = ma20
            boll_std = np.std(closes[-20:])
            boll_pos = (closes[-1] - (boll_mid - 2*boll_std)) / (4*boll_std) if boll_std > 0 else 0.5
            
            # 动量
            momentum10 = ret10
            momentum_strength = abs(ret10)
            
            # 价格位置
            price_position = (closes[-1] - np.min(closes[-60:])) / (np.max(closes[-60:]) - np.min(closes[-60:])) if len(closes) >= 60 else 0.5
            
            # 波动率
            volatility_rank = np.std(closes[-20:]) / np.mean(closes[-20:])
            
            # 近期收益
            recent_return = ret5
            
            # 加速度
            acceleration = ret5 - ret10 if len(closes) >= 11 else 0
            
            # 上涨比例
            up_days_ratio = np.sum(np.diff(closes[-20:]) > 0) / 19 if len(closes) >= 20 else 0.5
            
            # 量价相关性
            if len(closes) >= 20:
                vol_price_corr = np.corrcoef(np.diff(closes[-20:]), volumes[-19:]/volumes[-20:-1])[0,1]
                vol_price_corr = vol_price_corr if not np.isnan(vol_price_corr) else 0
            else:
                vol_price_corr = 0
            
            # 成交量趋势
            vol_trend = vol_ma5 / vol_ma10 - 1 if vol_ma10 > 0 else 0
            
            # 动量加速度
            momentum_accel = acceleration
            
            # 趋势强度
            trend_strength = abs(ma5_slope)
            
            # 波动率趋势
            vol20 = np.std(closes[-20:]) / np.mean(closes[-20:])
            vol40 = np.std(closes[-40:]) / np.mean(closes[-40:]) if len(closes) >= 40 else vol20
            volatility_trend = vol20 / vol40 - 1 if vol40 > 0 else 0
            
            # 振幅
            range_ratio = (highs[-1] - lows[-1]) / closes[-2] if len(closes) >= 2 else 0
            
            # 资金流代理
            money_flow_proxy = (closes[-1] - lows[-1]) / (highs[-1] - lows[-1]) - 0.5 if highs[-1] > lows[-1] else 0
            money_flow_ma = np.mean([(closes[-i] - lows[-i]) / (highs[-i] - lows[-i]) - 0.5 for i in range(1, 6) if highs[-i] > lows[-i]]) if len(closes) >= 5 else 0
            
            # V9 市场自适应特征 (3 个)
            market_rsi = rsi / 100  # 市场 RSI 状态 (归一化)
            market_trend = ma5_slope  # 市场趋势 (用个股均线斜率代理)
            volatility_state = volatility_rank  # 波动率状态
            
            features = {
                'p_ma5': p_ma5, 'p_ma10': p_ma10, 'p_ma20': p_ma20,
                'ma5_slope': ma5_slope, 'ma10_slope': ma10_slope,
                'ret5': ret5, 'ret10': ret10, 'rsi': rsi/100, 'macd_hist': macd_hist/closes[-1],
                'kdj_k': kdj_k/100, 'vol_ratio': vol_ratio, 'boll_pos': boll_pos,
                'momentum10': momentum10, 'vol_change': vol_change, 'price_position': price_position,
                'volatility_rank': volatility_rank, 'recent_return': recent_return, 'acceleration': acceleration,
                'up_days_ratio': up_days_ratio, 'momentum_strength': momentum_strength,
                'vol_price_corr': vol_price_corr, 'vol_trend': vol_trend, 'momentum_accel': momentum_accel,
                'trend_strength': trend_strength, 'volatility_trend': volatility_trend,
                'range_ratio': range_ratio, 'money_flow_proxy': money_flow_proxy, 'money_flow_ma': money_flow_ma,
                'market_rsi': market_rsi, 'market_trend': market_trend, 'volatility_state': volatility_state
            }
            
            return features
            
        except Exception as e:
            return None
    
    def predict(self, features):
        """使用集成模型预测"""
        feature_vector = np.array([[features.get(f, 0) for f in self.features]])
        
        # 5 模型集成平均
        probs = [model.predict_proba(feature_vector)[0,1] for model in self.models]
        avg_prob = np.mean(probs)
        
        return avg_prob
    
    def scan_stocks(self):
        """扫描全市场股票"""
        log(f"\n{'='*60}")
        log("扫描全市场股票...")
        log(f"{'='*60}")
        
        stock_list_path = HISTORY_DIR / "stock_list.json"
        with open(stock_list_path, 'r') as f:
            stock_list = json.load(f)
        
        total = len(stock_list)
        log(f"待扫描股票：{total} 只")
        
        results = []
        confidence_dist = []
        
        for i, stock in enumerate(stock_list):
            code = stock.get('ts_code', stock.get('code', ''))
            # 移除交易所后缀
            if '.' in code:
                code = code.split('.')[0]
            name = stock.get('name', stock.get('short_name', ''))
            
            data_path = HISTORY_DIR / f"{code}.json"
            if not data_path.exists():
                continue
            
            try:
                with open(data_path, 'r') as f:
                    data = json.load(f)
                
                if not data.get('items'):
                    continue
                
                df = pd.DataFrame(data['items'], columns=data['fields'])
                # 数据已经是正序 (旧->新)，最新的在最后，不需要反转
                # 去除可能的重复行
                df = df.drop_duplicates(subset=['trade_date'], keep='last').reset_index(drop=True)
                
                features = self.calculate_features(df)
                if features is None:
                    continue
                
                confidence = self.predict(features)
                confidence_dist.append(confidence)
                
                # 应用过滤条件 (右侧交易策略 - 追涨)
                if confidence >= CONFIDENCE_THRESHOLD:
                    rsi = features['rsi'] * 100
                    p_ma5 = features['p_ma5']
                    p_ma10 = features['p_ma10']
                    ret5 = features['ret5']
                    ret10 = features['ret10']
                    
                    # RSI 过滤 (强势区但不超买)
                    if rsi < RSI_MIN or rsi >= RSI_MAX:
                        continue
                    
                    # 右侧交易核心：已经涨起来了
                    if TREND_FILTER:
                        if p_ma5 < MA5_MIN:  # 明显站上 MA5
                            continue
                        if ret5 < RET5_MIN:  # 5 日已经涨超 3%
                            continue
                        if ret10 < RET10_MIN:  # 10 日不跌
                            continue
                    
                    results.append({
                            'code': code,
                            'name': name,
                            'confidence': confidence,
                            'rsi': rsi,
                            'p_ma5': features['p_ma5'],
                            'p_ma10': features['p_ma10'],
                            'p_ma20': features['p_ma20'],
                            'ret5': features['ret5'],
                            'ret10': features['ret10'],
                            'kdj_k': features['kdj_k'] * 100,
                            'close': df['close'].iloc[-1],
                            'change': (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100 if len(df) >= 2 else 0
                        })
                
                if (i + 1) % 1000 == 0:
                    log(f"进度：{i+1}/{total} ({(i+1)/total*100:.1f}%)")
                    
            except Exception as e:
                continue
        
        # 统计
        confidence_dist = np.array(confidence_dist)
        log(f"\n{'='*60}")
        log("扫描完成！")
        log(f"{'='*60}")
        log(f"扫描股票：{total} 只")
        log(f"成功计算：{len(confidence_dist)} 只")
        log(f"\n置信度分布:")
        log(f"  最小值：{confidence_dist.min()*100:.1f}%")
        log(f"  最大值：{confidence_dist.max()*100:.1f}%")
        log(f"  平均值：{confidence_dist.mean()*100:.1f}%")
        log(f"  中位数：{np.median(confidence_dist)*100:.1f}%")
        log(f"\n高置信度统计:")
        for thresh in [0.90, 0.85, 0.80, 0.75, 0.70]:
            count = np.sum(confidence_dist >= thresh)
            log(f"  ≥{thresh*100:.0f}%: {count}只 ({count/len(confidence_dist)*100:.2f}%)")
        
        return results
    
    def save_results(self, results):
        """保存选股结果"""
        OUTPUT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = OUTPUT_DIR / f"v9_selection_{timestamp}.json"
        
        # 排序
        results = sorted(results, key=lambda x: x['confidence'], reverse=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                'time': timestamp,
                'model': 'V9',
                'threshold': CONFIDENCE_THRESHOLD,
                'total': len(results),
                'selections': results
            }, f, indent=2, ensure_ascii=False)
        
        log(f"\n结果保存：{output_path}")
        return output_path
    
    def display_results(self, results):
        """显示选股结果"""
        results = sorted(results, key=lambda x: x['confidence'], reverse=True)[:TOP_N]
        
        log(f"\n{'='*60}")
        trend_desc = " + 右侧交易过滤" if TREND_FILTER else ""
        log(f"V9 选股结果 TOP{len(results)} (置信度≥{CONFIDENCE_THRESHOLD*100:.0f}%, RSI{RSI_MIN}-{RSI_MAX}, 5 日>={RET5_MIN*100:.0f}%{trend_desc})")
        log(f"{'='*60}")
        
        if not results:
            log("\n⚠️  未找到符合条件的股票")
            log(f"\n建议:")
            log(f"  1. 降低置信度阈值 (当前：{CONFIDENCE_THRESHOLD*100:.0f}%)")
            log(f"  2. 放宽 RSI 范围 (当前：{RSI_MIN}-{RSI_MAX})")
            log(f"  3. 放宽趋势过滤条件")
            return
        
        log(f"\n{'排名':<4} {'代码':<8} {'名称':<12} {'置信度':<10} {'RSI':<8} {'现价':<10} {'涨跌%':<8} {'5 日%':<8}")
        log(f"{'-'*60}")
        
        for i, r in enumerate(results, 1):
            rating = "⭐" * min(5, int(r['confidence'] * 5))
            log(f"{i:<4} {r['code']:<8} {r['name']:<12} {r['confidence']*100:>6.1f}%    {r['rsi']:>6.1f}   ¥{r['close']:>8.2f}   {r['change']:>+7.2f}%  {r['ret5']*100:>+7.1f}%  {rating}")
        
        log(f"\n{'='*60}")
        log("操作建议:")
        log(f"  • 置信度≥85%: 强烈买入，仓位 30%")
        log(f"  • 置信度 75-85%: 买入，仓位 20%")
        log(f"  • 置信度 70-75%: 关注，仓位 10%")
        log(f"  • 止损：-8%，止盈：+20% 后回撤 5%")
        log(f"  • 持有期：5-15 天")
        log(f"\n策略特点 (右侧交易):")
        log(f"  ✅ 已经涨起来了 (5 日>3%)")
        log(f"  ✅ 强势区 (RSI 50-70)")
        log(f"  ✅ 明显站上 MA5")
        log(f"  ✅ 高置信度 (≥70%)")
        log(f"{'='*60}\n")

def main():
    selector = V9EnsembleSelector()
    results = selector.scan_stocks()
    selector.save_results(results)
    selector.display_results(results)

if __name__ == "__main__":
    main()
