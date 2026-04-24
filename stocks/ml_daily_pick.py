#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML每日选股推送系统
自动扫描全市场，使用机器学习模型预测，推送高置信度股票

流程：
1. 加载ML模型
2. 扫描全市场最新数据
3. 计算特征，预测买入概率
4. 筛选高置信度股票
5. 推送结果（企业微信/钉钉）
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import warnings
from pathlib import Path
import pickle
import requests

warnings.filterwarnings('ignore')

CACHE_DIR = Path(__file__).parent / 'data_tushare'
MODEL_DIR = Path(__file__).parent / 'models'
RESULTS_DIR = Path(__file__).parent / 'backtest_results'


def load_model():
    """加载最新模型"""
    model_files = sorted(MODEL_DIR.glob('ml_selector_full_*.pkl'), reverse=True)
    if not model_files:
        model_files = sorted(MODEL_DIR.glob('ml_selector_v2_*.pkl'), reverse=True)
    
    if not model_files:
        print("❌ 未找到模型文件")
        return None
    
    model_file = model_files[0]
    
    with open(model_file, 'rb') as f:
        data = pickle.load(f)
    
    print(f"✅ 加载模型: {model_file.name}")
    print(f"  置信度阈值: {data.get('threshold', 0.65)}")
    print(f"  预测周期: {data.get('forward_days', 5)}天")
    print(f"  精确率: {data.get('high_precision', 0.82)*100:.1f}%")
    
    # 补充默认值
    if 'threshold' not in data:
        data['threshold'] = 0.65
    if 'forward_days' not in data:
        data['forward_days'] = 5
    if 'profit_pct' not in data:
        data['profit_pct'] = 0.03
    if 'features' not in data:
        data['features'] = [
            'p_ma5', 'p_ma10', 'p_ma20',
            'ma5_slope', 'ma20_slope',
            'ret1', 'ret5', 'ret10',
            'vol5', 'vol20',
            'rsi',
            'macd_dif', 'macd_dea', 'macd_hist',
            'kdj_k', 'kdj_d', 'kdj_j',
            'vol_ratio',
            'hl_pct'
        ]
    
    return data


def load_stock_data(symbol):
    """加载股票数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    if not filepath.exists():
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data['items'], columns=data['fields'])
        df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna()
    except:
        return None


def calc_features(df):
    """计算特征"""
    data = df.copy()
    
    # 均线
    data['ma5'] = data['close'].rolling(5).mean()
    data['ma10'] = data['close'].rolling(10).mean()
    data['ma20'] = data['close'].rolling(20).mean()
    data['ma60'] = data['close'].rolling(60).mean()
    
    # 价格相对均线
    data['p_ma5'] = (data['close'] - data['ma5']) / data['ma5']
    data['p_ma10'] = (data['close'] - data['ma10']) / data['ma10']
    data['p_ma20'] = (data['close'] - data['ma20']) / data['ma20']
    data['p_ma60'] = (data['close'] - data['ma60']) / data['ma60']
    
    # 均线斜率
    data['ma5_slope'] = data['ma5'] / data['ma5'].shift(5) - 1
    data['ma10_slope'] = data['ma10'] / data['ma10'].shift(5) - 1
    data['ma20_slope'] = data['ma20'] / data['ma20'].shift(10) - 1
    
    # 涨跌幅
    data['ret1'] = data['close'].pct_change()
    data['ret5'] = data['close'].pct_change(5)
    data['ret10'] = data['close'].pct_change(10)
    data['ret20'] = data['close'].pct_change(20)
    
    # 波动率
    data['vol5'] = data['ret1'].rolling(5).std()
    data['vol10'] = data['ret1'].rolling(10).std()
    data['vol20'] = data['ret1'].rolling(20).std()
    
    # RSI
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss.replace(0, 0.001)
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = data['close'].ewm(span=12, adjust=False).mean()
    ema26 = data['close'].ewm(span=26, adjust=False).mean()
    data['macd_dif'] = ema12 - ema26
    data['macd_dea'] = data['macd_dif'].ewm(span=9, adjust=False).mean()
    data['macd_hist'] = (data['macd_dif'] - data['macd_dea']) * 2
    
    # KDJ
    lowv = data['low'].rolling(9).min()
    highv = data['high'].rolling(9).max()
    rsv = (data['close'] - lowv) / (highv - lowv + 0.001) * 100
    data['kdj_k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
    data['kdj_d'] = data['kdj_k'].ewm(alpha=1/3, adjust=False).mean()
    data['kdj_j'] = 3 * data['kdj_k'] - 2 * data['kdj_d']
    
    # 成交量
    data['vol_ma5'] = data['volume'].rolling(5).mean()
    data['vol_ma20'] = data['volume'].rolling(20).mean()
    data['vol_ratio'] = data['volume'] / data['vol_ma5']
    data['vol_ratio20'] = data['volume'] / data['vol_ma20']
    
    # 价格形态
    data['hl_pct'] = (data['high'] - data['low']) / data['close']
    data['hc_pct'] = (data['high'] - data['close']) / data['close']
    data['cl_pct'] = (data['close'] - data['low']) / data['close']
    
    # 布林带位置
    data['boll_mid'] = data['close'].rolling(20).mean()
    data['boll_std'] = data['close'].rolling(20).std()
    data['boll_upper'] = data['boll_mid'] + 2 * data['boll_std']
    data['boll_lower'] = data['boll_mid'] - 2 * data['boll_std']
    data['boll_pos'] = (data['close'] - data['boll_lower']) / (data['boll_upper'] - data['boll_lower'] + 0.001)
    
    return data


def scan_market(model_data, symbols):
    """扫描市场"""
    model = model_data['model']
    scaler = model_data['scaler']
    features = model_data['features']
    threshold = model_data['threshold']
    
    print(f"\n📊 扫描市场: {len(symbols)} 只股票")
    print(f"  置信度阈值: {threshold*100:.0f}%")
    
    results = []
    
    for i, symbol in enumerate(symbols):
        try:
            df = load_stock_data(symbol)
            if df is None or len(df) < 60:
                continue
            
            feat_df = calc_features(df)
            
            # 取最新一行
            latest = feat_df.iloc[-1]
            
            # 检查特征完整性
            feat_vals = latest[features].values
            if np.any(np.isnan(feat_vals)):
                continue
            
            # 预测
            X = feat_vals.reshape(1, -1)
            X_s = scaler.transform(X)
            prob = model.predict_proba(X_s)[0, 1]
            
            # 筛选高置信度
            if prob > threshold:
                close = latest['close']
                rsi = latest['rsi']
                ma20 = latest['ma20']
                p_ma20 = (close - ma20) / ma20
                
                results.append({
                    'symbol': symbol,
                    'prob': prob,
                    'close': close,
                    'rsi': rsi,
                    'p_ma20': p_ma20,
                    'vol_ratio': latest['vol_ratio']
                })
            
            if (i + 1) % 500 == 0:
                print(f"  ⏳ {i+1}/{len(symbols)} | 发现:{len(results)}")
        
        except:
            pass
    
    # 排序
    results.sort(key=lambda x: -x['prob'])
    
    return results


def generate_report(results, threshold, model_info=None):
    """生成推送报告"""
    if not results:
        return "今日未发现高置信度买入信号"
    
    model_info = model_info or {}
    
    # 格式化
    lines = [
        f"🤖 ML选股系统 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"📊 扫描结果:",
        f"  置信度阈值: {threshold*100:.0f}%",
        f"  发现信号: {len(results)} 只",
        f"",
        f"🏆 TOP 10 高置信度股票:",
        f"| 代码 | 置信度 | 现价 | RSI | 跌MA20 |",
        f"|------|--------|------|-----|--------|"
    ]
    
    for r in results[:10]:
        prob_str = f"{r['prob']*100:.0f}%"
        rsi_str = f"{r['rsi']:.0f}"
        drop_str = f"{r['p_ma20']*100:.1f}%"
        close_str = f"{r['close']:.2f}"
        lines.append(f"| {r['symbol']} | {prob_str} | {close_str} | {rsi_str} | {drop_str} |")
    
    lines.append("")
    lines.append("💡 策略说明:")
    lines.append(f"  预测未来{model_info.get('forward_days', 5)}天涨超{int(model_info.get('profit_pct', 0.03)*100)}%")
    lines.append(f"  模型精确率: {model_info.get('high_precision', 0.82)*100:.1f}%")
    lines.append("  买入条件: 置信度 > 阈值")
    lines.append("  止损: 10% | 止盈: 12%")
    lines.append("")
    lines.append("⚠️ 风险提示: ML预测仅供参考，请结合自身判断")
    
    return "\n".join(lines)


def push_to_wecom(content):
    """推送到企业微信"""
    config_file = Path(__file__).parent / 'push_config.json'
    
    if not config_file.exists():
        print("❌ 未配置推送")
        return False
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    webhook = config.get('wecom_webhook')
    if not webhook:
        print("❌ 未配置企业微信webhook")
        return False
    
    try:
        resp = requests.post(webhook, json={
            'msgtype': 'text',
            'text': {'content': content}
        }, timeout=10)
        
        if resp.status_code == 200:
            print("✅ 企业微信推送成功")
            return True
        else:
            print(f"❌ 推送失败: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False


def main():
    """主流程"""
    print('='*80)
    print('ML每日选股推送系统')
    print('='*80)
    
    # 加载模型
    model_data = load_model()
    if not model_data:
        return
    
    # 加载股票列表
    symbols = list(set([f.stem for f in CACHE_DIR.glob('*.json')]))
    print(f"\n📊 股票池: {len(symbols)} 只")
    
    # 扫描
    results = scan_market(model_data, symbols)
    
    # 生成报告
    report = generate_report(results, model_data['threshold'], model_data)
    
    print("\n" + "="*80)
    print(report)
    
    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(RESULTS_DIR / f'ml_daily_pick_{timestamp}.csv',
                          index=False, encoding='utf-8-sig')
        print(f"\n💾 结果已保存: ml_daily_pick_{timestamp}.csv")
    
    # 推送
    push_to_wecom(report)
    
    return results


if __name__ == '__main__':
    main()