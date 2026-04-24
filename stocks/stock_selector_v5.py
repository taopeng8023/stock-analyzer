#!/usr/bin/env python3
"""
选股系统 V5 - 折中优化版
使用全量训练最优模型（P@90%=93.04%）
支持置信度筛选、抽样回测、全量回测
"""
import json, pickle, time, numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.metrics import precision_score
import warnings
warnings.filterwarnings('ignore')

# 配置
MODEL_FILE = Path("/Users/taopeng/.openclaw/workspace/stocks/models/ml_nn_full_balanced_20260417_1338.pkl")
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/selections")

class StockSelectorV5:
    """选股系统V5 - 折中优化版"""
    
    def __init__(self, model_file=None):
        if model_file:
            self.model_file = Path(model_file)
        else:
            self.model_file = MODEL_FILE
        
        self.load_model()
    
    def load_model(self):
        """加载模型"""
        print(f"加载模型: {self.model_file}", flush=True)
        
        with open(self.model_file, 'rb') as f:
            data = pickle.load(f)
        
        self.model = data['model']
        self.scaler = data['scaler']
        self.features = data['features']
        self.metadata = data['metadata']
        
        print(f"模型版本: {self.metadata['version']}", flush=True)
        print(f"训练股票: {self.metadata['total_stocks']}", flush=True)
        print(f"训练样本: {self.metadata['total_samples']}", flush=True)
        print(f"AUC: {self.metadata['auc']:.4f}", flush=True)
        print(f"网络结构: {self.metadata['network']}", flush=True)
        print(f"学习率: {self.metadata['learning_rate']}", flush=True)
    
    def extract_features(self, closes, volumes, highs, lows, i):
        """提取特征（与训练时完全一致）"""
        c = closes[i]
        ma5 = np.mean(closes[i-5:i+1])
        ma10 = np.mean(closes[i-10:i+1])
        ma20 = np.mean(closes[i-20:i+1])
        
        # 特征名称与训练时一致
        f = {
            'p_ma5': (c - ma5) / ma5,
            'p_ma10': (c - ma10) / ma10,
            'p_ma20': (c - ma20) / ma20,
            'vol5': np.std([closes[j] - closes[j-1] for j in range(i-4, i+1)]) / c  # 波动率
        }
        
        # RSI计算（14天）
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
        
        # 按features顺序返回
        return [f.get(k, 0) for k in self.features]
    
    def predict_stock(self, code, top_n=5):
        """预测单只股票"""
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
                        'close': c, 'vol': float(d.get('vol', 0)),
                        'high': float(d.get('high', c)), 'low': float(d.get('low', c)),
                        'date': str(d.get('trade_date', ''))
                    })
            
            if len(data) < 60:
                return None
            
            closes = [d['close'] for d in data]
            volumes = [d['vol'] for d in data]
            highs = [d['high'] for d in data]
            lows = [d['low'] for d in data]
            dates = [d['date'] for d in data]
            
            # 提取最新5天的特征
            recent_features = []
            for i in range(len(data)-5, len(data)):
                if i >= 60:
                    f = self.extract_features(closes, volumes, highs, lows, i)
                    recent_features.append(f)
            
            if len(recent_features) == 0:
                return None
            
            # 标准化并预测
            X = np.array(recent_features)
            X_s = self.scaler.transform(X)
            proba = self.model.predict_proba(X_s)[:, 1]
            
            # 平均置信度
            avg_conf = np.mean(proba)
            max_conf = np.max(proba)
            
            # 最近价格
            latest_close = closes[-1]
            latest_date = dates[-1]
            
            return {
                'code': code,
                'confidence': avg_conf,
                'max_confidence': max_conf,
                'close': latest_close,
                'date': latest_date,
                'all_probs': proba
            }
        except Exception as e:
            return None
    
    def select_stocks(self, confidence_threshold=0.85, limit=100):
        """选股"""
        print(f"\n开始选股（置信度≥{confidence_threshold*100:.0f}%，限制{limit}股）...", flush=True)
        
        files = sorted(HISTORY_DIR.glob("*.json"))
        print(f"扫描股票: {len(files)} 只", flush=True)
        
        results = []
        start = time.time()
        
        for i, fp in enumerate(files):
            code = fp.stem
            
            if (i+1) % 500 == 0:
                print(f"  已扫描 {i+1}/{len(files)} 股...", flush=True)
            
            result = self.predict_stock(code)
            
            if result and result['confidence'] >= confidence_threshold:
                results.append(result)
        
        # 排序
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 限制数量
        if limit:
            results = results[:limit]
        
        elapsed = time.time() - start
        
        print(f"\n选股完成:", flush=True)
        print(f"  扫描股票: {len(files)} 只", flush=True)
        print(f"  符合条件: {len(results)} 只", flush=True)
        print(f"  耗时: {elapsed:.1f}s", flush=True)
        
        return results
    
    def save_selection(self, results, filename=None):
        """保存选股结果"""
        if not filename:
            ts = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"selection_v5_{ts}.json"
        
        output_file = OUTPUT_DIR / filename
        
        with open(output_file, 'w') as f:
            json.dump({
                'version': 'V5_折中优化版',
                'model': str(self.model_file),
                'timestamp': datetime.now().isoformat(),
                'count': len(results),
                'results': results,
                'metadata': self.metadata
            }, f, indent=2)
        
        print(f"\n保存结果: {output_file}", flush=True)
        
        return output_file
    
    def backtest_sample(self, sample_size=100, confidence_threshold=0.85):
        """抽样回测"""
        print(f"\n抽样回测（{sample_size}股，置信度≥{confidence_threshold*100:.0f}%）...", flush=True)
        
        files = sorted(HISTORY_DIR.glob("*.json"))
        
        # 随机抽样
        np.random.seed(42)
        sample_files = np.random.choice(files, sample_size, replace=False)
        
        correct = 0
        total = 0
        returns = []
        
        for fp in sample_files:
            try:
                with open(fp) as f:
                    raw = json.load(f)
                
                items, fields = raw['items'], raw['fields']
                if len(items) < 60:
                    continue
                
                data = []
                for item in items:
                    d = dict(zip(fields, item))
                    c = float(d.get('close', 0))
                    if c > 0:
                        data.append({
                            'close': c, 'date': str(d.get('trade_date', ''))
                        })
                
                if len(data) < 60:
                    continue
                
                # 取最后一天前5天预测
                closes = [d['close'] for d in data]
                dates = [d['date'] for d in data]
                
                i = len(data) - 5
                if i < 60:
                    continue
                
                # 提取特征
                volumes = [0] * len(data)  # 简化
                highs = closes
                lows = closes
                
                f = self.extract_features(closes, volumes, highs, lows, i)
                X_s = self.scaler.transform([f])
                proba = self.model.predict_proba(X_s)[0, 1]
                
                # 判断是否预测上涨
                if proba >= confidence_threshold:
                    total += 1
                    
                    # 实际5天后涨幅
                    future_close = closes[-1]
                    current_close = closes[i]
                    ret = (future_close - current_close) / current_close
                    
                    returns.append(ret)
                    
                    # 是否涨超3%
                    if ret > 0.03:
                        correct += 1
            except:
                continue
        
        if total == 0:
            print(f"  无符合条件的预测", flush=True)
            return None
        
        precision = correct / total
        avg_return = np.mean(returns)
        
        print(f"\n抽样回测结果:", flush=True)
        print(f"  样本数: {sample_size}", flush=True)
        print(f"  预测数: {total}", flush=True)
        print(f"  正确数: {correct}", flush=True)
        print(f"  精确率: {precision*100:.2f}%", flush=True)
        print(f"  平均收益: {avg_return*100:.2f}%", flush=True)
        
        return {
            'sample_size': sample_size,
            'predictions': total,
            'correct': correct,
            'precision': precision,
            'avg_return': avg_return,
            'returns': returns
        }
    
    def backtest_full(self, confidence_threshold=0.85):
        """全量回测"""
        print(f"\n全量回测（置信度≥{confidence_threshold*100:.0f}%）...", flush=True)
        
        files = sorted(HISTORY_DIR.glob("*.json"))
        print(f"扫描股票: {len(files)} 只", flush=True)
        
        correct = 0
        total = 0
        returns = []
        stocks_with_signal = []
        
        start = time.time()
        
        for i, fp in enumerate(files):
            if (i+1) % 500 == 0:
                print(f"  已扫描 {i+1}/{len(files)} 股...", flush=True)
            
            try:
                with open(fp) as f:
                    raw = json.load(f)
                
                items, fields = raw['items'], raw['fields']
                if len(items) < 60:
                    continue
                
                data = []
                for item in items:
                    d = dict(zip(fields, item))
                    c = float(d.get('close', 0))
                    if c > 0:
                        data.append({
                            'close': c, 'vol': float(d.get('vol', 0)),
                            'high': float(d.get('high', c)), 'low': float(d.get('low', c)),
                            'date': str(d.get('trade_date', ''))
                        })
                
                if len(data) < 60:
                    continue
                
                closes = [d['close'] for d in data]
                volumes = [d['vol'] for d in data]
                highs = [d['high'] for d in data]
                lows = [d['low'] for d in data]
                dates = [d['date'] for d in data]
                
                # 对每个历史点预测
                for j in range(60, len(data) - 5):
                    date = dates[j]
                    if not (date.startswith('2024') or date.startswith('2025') or date.startswith('2026')):
                        continue
                    
                    f = self.extract_features(closes, volumes, highs, lows, j)
                    X_s = self.scaler.transform([f])
                    proba = self.model.predict_proba(X_s)[0, 1]
                    
                    if proba >= confidence_threshold:
                        total += 1
                        
                        future_close = closes[j+5]
                        current_close = closes[j]
                        ret = (future_close - current_close) / current_close
                        
                        returns.append(ret)
                        
                        if ret > 0.03:
                            correct += 1
                            stocks_with_signal.append(fp.stem)
            except:
                continue
        
        elapsed = time.time() - start
        
        if total == 0:
            print(f"  无符合条件的预测", flush=True)
            return None
        
        precision = correct / total
        avg_return = np.mean(returns)
        
        print(f"\n全量回测结果:", flush=True)
        print(f"  扫描股票: {len(files)} 只", flush=True)
        print(f"  预测信号: {total} 个", flush=True)
        print(f"  正确信号: {correct} 个", flush=True)
        print(f"  精确率: {precision*100:.2f}%", flush=True)
        print(f"  平均收益: {avg_return*100:.2f}%", flush=True)
        print(f"  耗时: {elapsed:.1f}s", flush=True)
        print(f"  盈利股票数: {len(set(stocks_with_signal))} 只", flush=True)
        
        return {
            'total_stocks': len(files),
            'total_signals': total,
            'correct_signals': correct,
            'precision': precision,
            'avg_return': avg_return,
            'profit_stocks': len(set(stocks_with_signal)),
            'elapsed': elapsed
        }

# 主函数
if __name__ == "__main__":
    import sys
    
    selector = StockSelectorV5()
    
    # 命令行参数
    if len(sys.argv) > 1:
        action = sys.argv[1]
        
        if action == "select":
            # 选股
            threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.85
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
            results = selector.select_stocks(threshold, limit)
            selector.save_selection(results)
            
            # 打印TOP10
            print(f"\nTOP10推荐:", flush=True)
            for i, r in enumerate(results[:10], 1):
                print(f"  {i}. {r['code']}: 置信度{r['confidence']*100:.2f}%, 收盘{r['close']:.2f}", flush=True)
        
        elif action == "backtest_sample":
            # 抽样回测
            sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.85
            selector.backtest_sample(sample_size, threshold)
        
        elif action == "backtest_full":
            # 全量回测
            threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.85
            selector.backtest_full(threshold)
        
        else:
            print(f"用法:", flush=True)
            print(f"  python3 stock_selector_v5.py select [threshold] [limit]", flush=True)
            print(f"  python3 stock_selector_v5.py backtest_sample [sample_size] [threshold]", flush=True)
            print(f"  python3 stock_selector_v5.py backtest_full [threshold]", flush=True)
    else:
        # 默认：选股
        print(f"\n默认执行选股（置信度≥85%，限制100股）...", flush=True)
        results = selector.select_stocks(0.85, 100)
        selector.save_selection(results)
        
        print(f"\nTOP10推荐:", flush=True)
        for i, r in enumerate(results[:10], 1):
            print(f"  {i}. {r['code']}: 置信度{r['confidence']*100:.2f}%, 收盘{r['close']:.2f}", flush=True)