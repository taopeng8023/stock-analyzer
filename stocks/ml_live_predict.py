#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML实盘预测系统 - 每日自动选股

功能：
1. 使用最新模型预测全市场
2. 筛选高置信度股票
3. 推送结果到企业微信/钉钉
4. 记录预测结果供验证
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import pickle
import xgboost as xgb
from datetime import datetime
import requests

DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
RESULTS_DIR = Path('/home/admin/.openclaw/workspace/stocks/backtest_results')

FEATURES = [
    'p_ma5', 'p_ma10', 'p_ma20', 'p_ma60',
    'ma5_slope', 'ma10_slope', 'ma20_slope',
    'ret1', 'ret5', 'ret10', 'ret20',
    'vol5', 'vol10', 'vol20',
    'rsi',
    'macd_dif', 'macd_dea', 'macd_hist',
    'kdj_k', 'kdj_d', 'kdj_j',
    'vol_ratio', 'vol_ratio20',
    'hl_pct', 'hc_pct', 'cl_pct',
    'boll_pos'
]

def calc_features(df):
    """计算技术指标"""
    d = df.copy()
    
    for p in [5, 10, 20, 60]:
        d[f'ma{p}'] = d['close'].rolling(p).mean()
        d[f'p_ma{p}'] = (d['close'] - d[f'ma{p}']) / d[f'ma{p}']
    
    d['ma5_slope'] = d['ma5'] / d['ma5'].shift(5) - 1
    d['ma10_slope'] = d['ma10'] / d['ma10'].shift(5) - 1
    d['ma20_slope'] = d['ma20'] / d['ma20'].shift(10) - 1
    
    for days in [1, 5, 10, 20]:
        d[f'ret{days}'] = d['close'].pct_change(days)
    
    for days in [5, 10, 20]:
        d[f'vol{days}'] = d['ret1'].rolling(days).std()
    
    delta = d['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    d['rsi'] = 100 - 100/(1 + gain/loss.replace(0, 0.001))
    
    ema12 = d['close'].ewm(span=12, adjust=False).mean()
    ema26 = d['close'].ewm(span=26, adjust=False).mean()
    d['macd_dif'] = ema12 - ema26
    d['macd_dea'] = d['macd_dif'].ewm(span=9, adjust=False).mean()
    d['macd_hist'] = (d['macd_dif'] - d['macd_dea']) * 2
    
    lowv = d['low'].rolling(9).min()
    highv = d['high'].rolling(9).max()
    rsv = (d['close'] - lowv) / (highv - lowv + 0.001) * 100
    d['kdj_k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
    d['kdj_d'] = d['kdj_k'].ewm(alpha=1/3, adjust=False).mean()
    d['kdj_j'] = 3 * d['kdj_k'] - 2 * d['kdj_d']
    
    d['vol_ma5'] = d['vol'].rolling(5).mean()
    d['vol_ma20'] = d['vol'].rolling(20).mean()
    d['vol_ratio'] = d['vol'] / d['vol_ma5']
    d['vol_ratio20'] = d['vol'] / d['vol_ma20']
    
    d['hl_pct'] = (d['high'] - d['low']) / d['close']
    d['hc_pct'] = (d['high'] - d['close']) / d['close']
    d['cl_pct'] = (d['close'] - d['low']) / d['close']
    
    d['boll_mid'] = d['close'].rolling(20).mean()
    d['boll_std'] = d['close'].rolling(20).std()
    d['boll_upper'] = d['boll_mid'] + 2 * d['boll_std']
    d['boll_lower'] = d['boll_mid'] - 2 * d['boll_std']
    d['boll_pos'] = (d['close'] - d['boll_lower']) / (d['boll_upper'] - d['boll_lower'] + 0.001)
    
    return d

def predict_stock(symbol, model, scaler):
    """预测单只股票"""
    filepath = DATA_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data['items'], columns=data['fields'])
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        for c in ['open', 'high', 'low', 'close', 'vol']:
            df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)
        
        df = df.dropna()
        if len(df) < 60:
            return None
        
        feat = calc_features(df)
        latest = feat.iloc[-1]
        
        X = latest[FEATURES].values.astype(float).reshape(1, -1)
        if np.isnan(X).sum() > 0:
            return None
        
        # 使用XGBoost预测
        dmat = xgb.DMatrix(X)
        prob = model.predict(dmat)[0]
        
        return {
            'symbol': symbol,
            'prob': prob,
            'close': float(latest['close']),
            'rsi': float(latest['rsi']),
            'p_ma20': float(latest['p_ma20']),
            'kdj_j': float(latest['kdj_j']),
            'vol_ratio': float(latest['vol_ratio']),
            'date': str(latest['trade_date'])
        }
    except:
        return None

def get_stock_name(symbol):
    """获取股票名称（从缓存）"""
    name_file = Path('/home/admin/.openclaw/workspace/stocks/stock_names.json')
    
    if name_file.exists():
        with open(name_file, 'r') as f:
            names = json.load(f)
        return names.get(symbol, symbol)
    
    return symbol

def generate_report(results, threshold):
    """生成推送报告"""
    if not results:
        return None
    
    high_conf = [r for r in results if r['prob'] > threshold]
    
    lines = [
        f"🤖 ML选股系统 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"📊 扫描结果:",
        f"  扫描股票: {len(results)}只",
        f"  高置信度(>{threshold*100:.0f}%): {len(high_conf)}只",
        "",
        f"🏆 TOP 10 推荐买入:",
        "| 代码 | 置信度 | 现价 | RSI | 跌MA20 | KDJ-J |",
        "|------|--------|------|-----|--------|-------|"
    ]
    
    for r in high_conf[:10]:
        lines.append(f"| {r['symbol']} | {r['prob']*100:.0f}% | ¥{r['close']:.2f} | {r['rsi']:.0f} | {r['p_ma20']*100:.1f}% | {r['kdj_j']:.0f} |")
    
    lines.extend([
        "",
        "💡 交易建议:",
        f"  买入条件: 置信度 > {threshold*100:.0f}%",
        "  止盈: 盈利10%后回撤5%",
        "  止损: 亏损12%",
        "  持仓: 最长15天",
        "",
        "⚠️ 风险提示: ML预测仅供参考，请结合自身判断"
    ])
    
    return "\n".join(lines)

def push_to_wecom(content):
    """推送到企业微信"""
    config_file = Path('/home/admin/.openclaw/workspace/stocks/push_config.json')
    
    if not config_file.exists():
        print("未配置推送")
        return False
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    webhook = config.get('wecom_webhook')
    if not webhook:
        return False
    
    try:
        resp = requests.post(webhook, json={
            'msgtype': 'text',
            'text': {'content': content}
        }, timeout=10)
        
        return resp.status_code == 200
    except:
        return False

def main():
    print('='*60)
    print('ML实盘预测系统')
    print('='*60)
    
    # 加载最新模型
    model_files = sorted(MODEL_DIR.glob('ml_xgb*.json'), reverse=True)
    
    if not model_files:
        print('无XGBoost模型文件')
        return
    
    model_file = model_files[0]
    model = xgb.Booster()
    model.load_model(str(model_file))
    
    # 加载配置
    config_files = sorted(MODEL_DIR.glob('ml_*config*.json'), reverse=True)
    
    if config_files:
        with open(config_files[0], 'r') as f:
            config = json.load(f)
        threshold = config.get('threshold', 0.75)
    else:
        threshold = 0.75
    
    print(f'模型: {model_file.name}')
    print(f'阈值: {threshold*100:.0f}%')
    
    # 加载股票列表
    symbols = [f.stem for f in DATA_DIR.glob('*.json')]
    print(f'\n股票总数: {len(symbols)}只')
    
    # 主板筛选
    main_symbols = [s for s in symbols if s.startswith('60') or s.startswith('00')]
    print(f'主板股票: {len(main_symbols)}只')
    
    # 扫描
    print('\n扫描中...')
    
    results = []
    
    for i, s in enumerate(main_symbols):
        r = predict_stock(s, model, None)
        if r:
            results.append(r)
        
        if (i+1) % 500 == 0:
            high = len([r for r in results if r['prob'] > threshold])
            print(f'  {i+1}/{len(main_symbols)} | 有效:{len(results)} | 高置信:{high}')
    
    # 排序
    results.sort(key=lambda x: -x['prob'])
    
    # 高置信度
    high_conf = [r for r in results if r['prob'] > threshold]
    
    print(f'\n扫描完成')
    print(f'有效结果: {len(results)}只')
    print(f'高置信度(>{threshold*100:.0f}%): {len(high_conf)}只')
    
    if high_conf:
        print(f'\n🏆 TOP 10:')
        for r in high_conf[:10]:
            print(f"  {r['symbol']} | {r['prob']*100:.0f}% | ¥{r['close']:.2f} | RSI{r['rsi']:.0f}")
        
        # 生成报告
        report = generate_report(results, threshold)
        
        if report:
            print(f'\n{report}')
            
            # 推送
            if push_to_wecom(report):
                print('\n✅ 推送成功')
            
            # 保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            pd.DataFrame(results).to_csv(
                RESULTS_DIR / f'ml_prediction_{timestamp}.csv',
                index=False
            )
            
            print(f'\n💾 保存: ml_prediction_{timestamp}.csv')
            
            # 记录预测供验证
            prediction_log = {
                'timestamp': timestamp,
                'threshold': threshold,
                'total_scanned': len(results),
                'high_confidence': len(high_conf),
                'top5': high_conf[:5]
            }
            
            with open(RESULTS_DIR / f'prediction_log_{timestamp}.json', 'w') as f:
                json.dump(prediction_log, f, indent=2)

if __name__ == '__main__':
    main()