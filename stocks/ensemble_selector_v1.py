#!/usr/bin/env python3
"""
三重确认选股脚本 V1
条件：RSI<45 + 跌幅>10% + 置信度>75%
扫描 data_history_2022_2026/ 目录所有股票
输出 TOP10 选股结果
"""
import json
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 配置
MODEL_FILE = Path("/Users/taopeng/.openclaw/workspace/stocks/models/ml_nn_full_balanced_20260417_1338.pkl")
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/selections")

# 选股条件
RSI_THRESHOLD = 45  # RSI < 45
DROP_THRESHOLD = 10  # 跌幅 > 10%
CONFIDENCE_THRESHOLD = 0.75  # 置信度 > 75%
TOP_N = 10  # 输出 TOP10

class EnsembleSelector:
    """三重确认选股器"""
    
    def __init__(self, model_file=None):
        self.model_file = Path(model_file) if model_file else MODEL_FILE
        self.load_model()
    
    def load_model(self):
        """加载模型"""
        print(f"加载模型：{self.model_file}", flush=True)
        
        with open(self.model_file, 'rb') as f:
            data = pickle.load(f)
        
        self.model = data['model']
        self.scaler = data['scaler']
        self.features = data['features']
        self.metadata = data['metadata']
        
        print(f"模型版本：{self.metadata['version']}", flush=True)
        print(f"AUC: {self.metadata['auc']:.4f}", flush=True)
    
    def calculate_rsi(self, closes, period=14):
        """计算 RSI 指标"""
        if len(closes) < period + 1:
            return 50  # 默认值
        
        deltas = [closes[i] - closes[i-1] for i in range(len(closes)-period, len(closes))]
        gains = sum(d for d in deltas if d > 0)
        losses = sum(-d for d in deltas if d < 0)
        
        if losses == 0:
            return 100
        
        rs = gains / (losses + 0.001)
        rsi = 100 - 100 / (1 + rs)
        return rsi
    
    def calculate_drop(self, closes, period=20):
        """计算近期最大跌幅（从高点下跌的百分比）"""
        if len(closes) < period:
            return 0
        
        recent = closes[-period:]
        high = max(recent)
        current = closes[-1]
        
        drop = (high - current) / high * 100
        return drop
    
    def extract_features(self, closes, volumes, highs, lows, i):
        """提取特征（与训练时一致）"""
        c = closes[i]
        ma5 = np.mean(closes[i-5:i+1])
        ma10 = np.mean(closes[i-10:i+1])
        ma20 = np.mean(closes[i-20:i+1])
        
        f = {
            'p_ma5': (c - ma5) / ma5,
            'p_ma10': (c - ma10) / ma10,
            'p_ma20': (c - ma20) / ma20,
            'vol5': np.std([closes[j] - closes[j-1] for j in range(i-4, i+1)]) / c,
        }
        
        # RSI 计算（14 天）
        deltas = [closes[j] - closes[j-1] for j in range(i-13, i+1)]
        gains = sum(d for d in deltas if d > 0)
        losses = sum(-d for d in deltas if d < 0)
        f['rsi'] = 100 - 100/(1 + gains/(losses+0.001)) if losses > 0 else 100
        
        # 成交量比率
        vol5 = np.mean(volumes[i-5:i+1])
        f['vol_ratio'] = volumes[i] / (vol5 + 0.001)
        
        # 振幅
        f['hl_pct'] = (highs[i] - lows[i]) / c
        
        # 布林带位置
        f['boll_pos'] = (c - ma20) / (2 * np.std(closes[i-20:i+1]) + 0.001)
        
        return [f.get(k, 0) for k in self.features]
    
    def analyze_stock(self, code):
        """分析单只股票"""
        try:
            with open(HISTORY_DIR / f"{code}.json") as f:
                raw = json.load(f)
            
            items, fields = raw['items'], raw['fields']
            if len(items) < 60:
                return None
            
            data = []
            for item in items:
                d = dict(zip(fields, item))
                c = float(d.get('close', 0))
                if c > 0:
                    data.append({
                        'close': c,
                        'vol': float(d.get('vol', 0)),
                        'high': float(d.get('high', c)),
                        'low': float(d.get('low', c)),
                        'date': str(d.get('trade_date', ''))
                    })
            
            if len(data) < 60:
                return None
            
            closes = [d['close'] for d in data]
            volumes = [d['vol'] for d in data]
            highs = [d['high'] for d in data]
            lows = [d['low'] for d in data]
            dates = [d['date'] for d in data]
            
            # 计算技术指标
            rsi = self.calculate_rsi(closes)
            drop = self.calculate_drop(closes)
            
            # 三重确认条件
            rsi_ok = rsi < RSI_THRESHOLD
            drop_ok = drop > DROP_THRESHOLD
            
            # 预测置信度
            i = len(data) - 1
            if i >= 60:
                feat = self.extract_features(closes, volumes, highs, lows, i)
                X = np.array([feat])
                X_s = self.scaler.transform(X)
                proba = self.model.predict_proba(X_s)[0, 1]
            else:
                proba = 0.5
            
            confidence_ok = proba > CONFIDENCE_THRESHOLD
            
            # 综合评分（用于排序）
            score = (1 - rsi/100) * 0.3 + (drop/20) * 0.3 + proba * 0.4
            
            return {
                'code': code,
                'rsi': float(rsi),
                'drop': float(drop),
                'confidence': float(proba),
                'score': float(score),
                'close': float(closes[-1]),
                'date': dates[-1],
                'rsi_ok': bool(rsi_ok),
                'drop_ok': bool(drop_ok),
                'confidence_ok': bool(confidence_ok),
                'all_conditions_met': bool(rsi_ok and drop_ok and confidence_ok)
            }
        except Exception as e:
            return None
    
    def select(self):
        """执行选股"""
        print(f"\n{'='*60}", flush=True)
        print(f"三重确认选股系统 V1", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"选股条件:", flush=True)
        print(f"  - RSI < {RSI_THRESHOLD}", flush=True)
        print(f"  - 跌幅 > {DROP_THRESHOLD}%", flush=True)
        print(f"  - 置信度 > {CONFIDENCE_THRESHOLD*100:.0f}%", flush=True)
        print(f"{'='*60}\n", flush=True)
        
        # 获取所有股票文件
        stock_files = list(HISTORY_DIR.glob("*.json"))
        total_stocks = len(stock_files)
        print(f"扫描股票数量：{total_stocks}", flush=True)
        
        # 分析所有股票
        results = []
        for idx, stock_file in enumerate(stock_files):
            code = stock_file.stem
            result = self.analyze_stock(code)
            
            if result:
                results.append(result)
            
            if (idx + 1) % 500 == 0:
                print(f"已处理：{idx + 1}/{total_stocks}", flush=True)
        
        print(f"\n完成分析：{len(results)} 只股票\n", flush=True)
        
        # 筛选符合所有条件的股票
        qualified = [r for r in results if r['all_conditions_met']]
        print(f"符合所有条件的股票：{len(qualified)} 只\n", flush=True)
        
        # 按综合评分排序
        qualified.sort(key=lambda x: x['score'], reverse=True)
        
        # 输出 TOP10
        top10 = qualified[:TOP_N]
        
        print(f"{'='*60}", flush=True)
        print(f"TOP{TOP_N} 选股结果", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"{'排名':<4} {'代码':<8} {'RSI':<8} {'跌幅%':<8} {'置信度':<10} {'评分':<8} {'收盘价':<10}", flush=True)
        print(f"{'-'*60}", flush=True)
        
        for i, stock in enumerate(top10, 1):
            print(f"{i:<4} {stock['code']:<8} {stock['rsi']:<8.2f} {stock['drop']:<8.2f} {stock['confidence']:<10.2%} {stock['score']:<8.4f} {stock['close']:<10.2f}", flush=True)
        
        print(f"{'='*60}\n", flush=True)
        
        # 保存结果
        self.save_results(qualified, top10)
        
        return {
            'total_scanned': len(results),
            'qualified_count': len(qualified),
            'top10': top10,
            'all_qualified': qualified
        }
    
    def save_results(self, all_qualified, top10):
        """保存选股结果"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存 TOP10
        top10_file = OUTPUT_DIR / f"ensemble_top10_{timestamp}.json"
        with open(top10_file, 'w', encoding='utf-8') as f:
            json.dump(top10, f, ensure_ascii=False, indent=2)
        print(f"TOP10 结果已保存：{top10_file}", flush=True)
        
        # 保存所有符合条件的股票
        all_file = OUTPUT_DIR / f"ensemble_all_{timestamp}.json"
        with open(all_file, 'w', encoding='utf-8') as f:
            json.dump(all_qualified, f, ensure_ascii=False, indent=2)
        print(f"全部结果已保存：{all_file}", flush=True)


def main():
    selector = EnsembleSelector()
    results = selector.select()
    
    # 输出摘要
    print(f"\n{'='*60}", flush=True)
    print(f"选股摘要", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"扫描股票总数：{results['total_scanned']}", flush=True)
    print(f"符合条件的股票数：{results['qualified_count']}", flush=True)
    print(f"TOP5 股票代码：{', '.join([s['code'] for s in results['top10'][:5]])}", flush=True)
    print(f"{'='*60}\n", flush=True)
    
    return results


if __name__ == "__main__":
    main()
