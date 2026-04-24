#!/usr/bin/env python3
"""
神经网络选股系统 - V9
结合三年混合模型 + 资金流排行
"""
import json
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime

print("="*70)
print("神经网络选股系统 V9")
print("="*70)
print(datetime.now())

HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
MODEL_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/models")
DATA_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data")

FEATURES = ['p_ma5', 'p_ma10', 'p_ma20', 'ret5', 'vol5', 'rsi', 'vol_ratio', 'hl_pct', 'boll_pos']

# 加载模型
print("\n加载生产模型...")
with open(MODEL_DIR / 'ml_nn_production.pkl', 'rb') as f:
    model_data = pickle.load(f)

model = model_data['model']
scaler = model_data['scaler']

meta = model_data.get('metadata', {})
print(f"模型版本: {meta.get('version', '?')}")
print(f"训练AUC: {meta.get('auc', 0):.4f}")
print(f"推荐阈值: ≥60%")

# 加载资金流数据（如果有）
zjlx_file = DATA_DIR / "zjlx_ranking_20260415.json"
zjlx_data = []
if zjlx_file.exists():
    with open(zjlx_file) as f:
        zjlx_raw = json.load(f)
    zjlx_data = zjlx_raw if isinstance(zjlx_raw, list) else zjlx_raw.get('data', [])
    print(f"资金流数据: {len(zjlx_data)}股")

# 加载最新股票数据并预测
print("\n扫描股票数据...")

files = sorted(HISTORY_DIR.glob("*.json"))
print(f"股票总数: {len(files)}")

predictions = []
errors = 0

for fp in files:
    try:
        with open(fp) as f:
            raw = json.load(f)
        
        items = raw['items']
        fields = raw['fields']
        
        if len(items) < 60:
            continue
        
        # 解析数据（从旧到新）
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
        
        # 取最新一天
        i = len(data) - 1
        latest = data[i]
        
        # 检查是否是最近交易日
        if not latest['date'].startswith('2026'):
            continue
        
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
        
        # 查找资金流排行
        zjlx_rank = None
        zjlx_flow = None
        for z in zjlx_data:
            if z.get('代码') == fp.stem or z.get('code') == fp.stem:
                zjlx_rank = z.get('排行', z.get('rank'))
                zjlx_flow = z.get('主力净流入', z.get('flow'))
                break
        
        predictions.append({
            'code': fp.stem,
            'date': latest['date'],
            'close': c,
            'prob': prob,
            'rsi': f['rsi'],
            'ret5': f['ret5'],
            'zjlx_rank': zjlx_rank,
            'zjlx_flow': zjlx_flow
        })
    
    except Exception as e:
        errors += 1

print(f"成功预测: {len(predictions)}股")
print(f"失败: {errors}股")

if len(predictions) == 0:
    print("无预测数据")
    exit(1)

# 置信度分布
probs = [p['prob'] for p in predictions]
print(f"\n置信度分布:")
print(f"  最小: {np.min(probs):.2%}")
print(f"  最大: {np.max(probs):.2%}")
print(f"  平均: {np.mean(probs):.2%}")

# 分段统计
high_50 = [p for p in predictions if p['prob'] >= 0.50]
high_60 = [p for p in predictions if p['prob'] >= 0.60]
high_70 = [p for p in predictions if p['prob'] >= 0.70]

print(f"\n置信度≥50%: {len(high_50)}股")
print(f"置信度≥60%: {len(high_60)}股")
print(f"置信度≥70%: {len(high_70)}股")

# 按置信度排序
high_60.sort(key=lambda x: x['prob'], reverse=True)

# 选股结果
print("\n" + "="*70)
print("神经网络选股结果 (置信度≥60%)")
print("="*70)

if len(high_60) == 0:
    print("无高置信度股票")
else:
    print(f"\nTOP20 推荐:")
    print("-"*70)
    
    for i, p in enumerate(high_60[:20], 1):
        code = p['code']
        prob = p['prob']
        close = p['close']
        rsi = p['rsi']
        ret5 = p['ret5']
        zjlx = p['zjlx_rank']
        
        # 评级
        if prob >= 0.70:
            rating = "⭐⭐⭐⭐⭐ 强烈买入"
        elif prob >= 0.65:
            rating = "⭐⭐⭐⭐ 买入"
        else:
            rating = "⭐⭐⭐ 关注"
        
        # 资金流加分
        if zjlx and zjlx <= 20:
            rating += " +资金流TOP20"
        
        print(f"\n{i}. {code}")
        print(f"   置信度: {prob:.2%}")
        print(f"   收盘价: ¥{close:.2f}")
        print(f"   RSI: {rsi:.1f} | 5日涨幅: {ret5:.2%}")
        if zjlx:
            print(f"   资金流排行: #{zjlx}")
        print(f"   评级: {rating}")

# 保存结果
result_file = DATA_DIR / f"nn_selection_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
with open(result_file, 'w') as f:
    json.dump({
        'date': predictions[0]['date'] if predictions else '',
        'model_version': meta.get('version'),
        'threshold': '≥60%',
        'total_predicted': len(predictions),
        'high_confidence': len(high_60),
        'top20': [{
            'code': p['code'],
            'prob': float(p['prob']),
            'close': float(p['close']),
            'rsi': float(p['rsi']),
            'zjlx_rank': p['zjlx_rank']
        } for p in high_60[:20]]
    }, f)

print(f"\n结果保存: {result_file.name}")

# 综合评分（结合ML+资金流）
print("\n" + "="*70)
print("综合评分 TOP10 (ML置信度 + 资金流排行)")
print("="*70)

combined = []
for p in high_60:
    score = p['prob'] * 100  # ML置信度
    
    # 资金流加分
    if p['zjlx_rank']:
        if p['zjlx_rank'] <= 10:
            score += 20
        elif p['zjlx_rank'] <= 20:
            score += 10
        elif p['zjlx_rank'] <= 50:
            score += 5
    
    combined.append({
        'code': p['code'],
        'score': score,
        'prob': p['prob'],
        'zjlx_rank': p['zjlx_rank'],
        'close': p['close']
    })

combined.sort(key=lambda x: x['score'], reverse=True)

for i, c in enumerate(combined[:10], 1):
    print(f"\n{i}. {c['code']}")
    print(f"   综合评分: {c['score']:.1f}")
    print(f"   ML置信度: {c['prob']:.2%}")
    if c['zjlx_rank']:
        print(f"   资金流: #{c['zjlx_rank']}")
    print(f"   收盘价: ¥{c['close']:.2f}")

print("\n完成:", datetime.now())