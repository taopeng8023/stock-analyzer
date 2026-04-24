#!/usr/bin/env python3
"""
实际选股测试 - 检查置信度分布
"""
import json
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime

print("="*70)
print("实际选股测试")
print("="*70)

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

# 加载最新数据
print("\n加载最近交易日数据...")

# 取最新数据（应该有2026年）
files = sorted(HISTORY_DIR.glob("*.json"))[:100]

latest_date = None
stocks_data = []

for fp in files:
    try:
        with open(fp) as f:
            raw = json.load(f)
        
        items = raw['items']
        fields = raw['fields']
        
        if len(items) < 100:
            continue
        
        # 数据本身从旧到新，无需反转
        # 最新数据在末尾
        data = []
        for item in items:  # 不反转
            d = dict(zip(fields, item))
            c = float(d.get('close', 0))
            if c > 0:
                data.append({
                    'close': c, 'vol': float(d.get('vol', 0)),
                    'high': float(d.get('high', c)), 'low': float(d.get('low', c)),
                    'date': str(d.get('trade_date', ''))
                })
        
        if not data:
            continue
        
        # 最新日期
        latest = data[-1]
        date = latest['date']
        
        if latest_date is None or date > latest_date:
            latest_date = date
        
        stocks_data.append({
            'code': fp.stem,
            'data': data,
            'latest': latest
        })
    
    except:
        continue

print(f"加载 {len(stocks_data)} 股")
print(f"最新日期: {latest_date}")

# 加载模型
print("\n加载混合模型...")
with open(MODEL_DIR / 'ml_nn_production.pkl', 'rb') as f:
    model_data = pickle.load(f)

model = model_data['model']
scaler = model_data['scaler']

print(f"模型版本: {model_data['metadata'].get('version')}")
print(f"训练AUC: {model_data['metadata'].get('auc')}")

# 计算特征并预测
print("\n计算特征并预测...")

predictions = []

for stock in stocks_data:
    data = stock['data']
    code = stock['code']
    
    if len(data) < 60:
        continue
    
    # 取最新一天
    i = len(data) - 1
    
    closes = [d['close'] for d in data]
    volumes = [d['vol'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    
    c = closes[i]
    ma5 = np.mean(closes[i-5:i+1])
    ma10 = np.mean(closes[i-10:i+1])
    ma20 = np.mean(closes[i-20:i+1])
    
    f = {}
    f['p_ma5'] = (c - ma5) / ma5
    f['p_ma10'] = (c - ma10) / ma10
    f['p_ma20'] = (c - ma20) / ma20
    f['ret5'] = (c - closes[i-5]) / closes[i-5]
    
    rets = [(closes[j] - closes[j-1]) / closes[j-1] for j in range(max(1, i-20), i)]
    f['vol5'] = np.std(rets[-5:]) if len(rets) >= 5 else 0
    
    deltas = [closes[j+1] - closes[j] for j in range(max(0, i-15), i)]
    gains = sum(d for d in deltas if d > 0)
    losses = sum(-d for d in deltas if d < 0)
    f['rsi'] = 100 - 100/(1 + gains/losses) if losses > 0 else 50
    
    vol5 = np.mean(volumes[i-5:i+1])
    f['vol_ratio'] = volumes[i] / vol5 if vol5 > 0 else 1
    f['hl_pct'] = (highs[i] - lows[i]) / c
    
    std20 = np.std(closes[i-20:i+1])
    f['boll_pos'] = (c - ma20) / (2*std20) if std20 > 0 else 0
    
    X = np.array([[f.get(k, 0) for k in FEATURES]], dtype=np.float32)
    X_scaled = scaler.transform(X)
    
    prob = model.predict_proba(X_scaled)[0, 1]
    
    predictions.append({
        'code': code,
        'close': c,
        'prob': prob,
        'rsi': f['rsi'],
        'ret5': f['ret5']
    })

print(f"预测 {len(predictions)} 股")

# 置信度分布分析
probs = [p['prob'] for p in predictions]

print("\n置信度分布:")
print(f"  最小: {np.min(probs):.2%}")
print(f"  最大: {np.max(probs):.2%}")
print(f"  平均: {np.mean(probs):.2%}")
print(f"  中位数: {np.median(probs):.2%}")
print(f"  标准差: {np.std(probs):.2%}")

# 分段统计
print("\n置信度分段:")
bins = [0, 0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
labels = ['<30%', '30-50%', '50-70%', '70-80%', '80-85%', '85-90%', '90-95%', '≥95%']

for i in range(len(bins)-1):
    count = sum(1 for p in probs if bins[i] <= p < bins[i+1])
    pct = count / len(probs) * 100
    print(f"  {labels[i]}: {count}股 ({pct:.1f}%)")

# 高置信度股票
high_conf = sorted([p for p in predictions if p['prob'] >= 0.70], 
                   key=lambda x: x['prob'], reverse=True)

print("\n" + "="*70)
print("高置信度股票 (≥70%)")
print("="*70)

print(f"\nTOP10 推荐:")
for i, p in enumerate(high_conf[:10], 1):
    print(f"{i}. {p['code']}")
    print(f"   置信度: {p['prob']:.2%}")
    print(f"   收盘价: ¥{p['close']:.2f}")
    print(f"   RSI: {p['rsi']:.1f}")
    print(f"   5日涨幅: {p['ret5']:.2%}")

# 保存结果
result_file = MODEL_DIR / f"selection_result_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
with open(result_file, 'w') as f:
    json.dump({
        'date': latest_date,
        'predictions': predictions[:50],
        'high_confidence': high_conf[:20],
        'stats': {
            'min': float(np.min(probs)),
            'max': float(np.max(probs)),
            'mean': float(np.mean(probs)),
            'median': float(np.median(probs))
        }
    }, f)

print(f"\n结果保存: {result_file.name}")
print("\n完成:", datetime.now())