#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日选股推送脚本
策略: RSI 30-50 + 均线多头 + 股价站上MA5
推送: 企业微信/微信
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
import warnings
import requests

warnings.filterwarnings('ignore')

# 股票数据缓存目录
CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
OUTPUT_DIR = Path('/home/admin/.openclaw/workspace/stocks/daily_picks')
OUTPUT_DIR.mkdir(exist_ok=True)

# 推送配置
PUSH_CONFIG = Path('/home/admin/.openclaw/workspace/stocks/push_config.json')


def load_stock_data(symbol):
    """加载股票历史数据"""
    filepath = CACHE_DIR / f'{symbol}.json'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'fields' in data and 'items' in data:
            df = pd.DataFrame(data['items'], columns=data['fields'])
            df = df.rename(columns={'trade_date': 'date'})
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date').reset_index(drop=True)
            
            for col in ['open', 'high', 'low', 'close', 'vol']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
    except:
        return None


def calc_ma(close, period):
    """计算均线"""
    return close.rolling(window=period).mean()


def calc_rsi(close, period=14):
    """计算RSI"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calc_kdj(df, n=9):
    """计算KDJ"""
    lowv = df['low'].rolling(n).min()
    highv = df['high'].rolling(n).max()
    rsv = (df['close'] - lowv) / (highv - lowv) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def get_stock_name(symbol):
    """获取股票名称"""
    stock_list_file = Path('/home/admin/.openclaw/workspace/stocks/all_stocks_list.csv')
    if stock_list_file.exists():
        try:
            stock_list = pd.read_csv(stock_list_file)
            match = stock_list[stock_list['symbol'] == symbol]
            if len(match) > 0:
                return match['name'].iloc[0]
        except:
            pass
    return symbol


def scan_stocks(top_n=10):
    """扫描全市场股票"""
    symbols = [f.stem for f in CACHE_DIR.glob('*.json')]
    
    picks = []
    
    for sym in symbols:
        df = load_stock_data(sym)
        if df is None or len(df) < 50:
            continue
        
        # 只取最近数据
        recent = df.tail(30).copy()
        
        # 计算指标
        recent['ma5'] = calc_ma(recent['close'], 5)
        recent['ma10'] = calc_ma(recent['close'], 10)
        recent['ma20'] = calc_ma(recent['close'], 20)
        recent['rsi'] = calc_rsi(recent['close'], 14)
        k, d, j = calc_kdj(recent, 9)
        recent['j'] = j
        
        # 最新数据
        latest = recent.iloc[-1]
        
        if pd.isna(latest['rsi']) or pd.isna(latest['ma5']):
            continue
        
        # 计算信号强度
        score = 0
        signals = []
        
        rsi = float(latest['rsi'])
        ma5 = float(latest['ma5'])
        ma10 = float(latest['ma10'])
        ma20 = float(latest['ma20'])
        j_val = float(latest['j']) if not pd.isna(latest['j']) else 50
        price = float(latest['close'])
        
        # 条件1: RSI在30-50区间 (2分)
        if 30 < rsi < 50:
            score += 2
            signals.append('RSI超卖')
        
        # 条件2: MA5 > MA10 (1分)
        if ma5 > ma10:
            score += 1
            signals.append('均线多头')
        
        # 条件3: 股价 > MA5 (1分)
        if price > ma5:
            score += 1
            signals.append('站上MA5')
        
        # 条件4: J值 < 40 (1分 加分)
        if j_val < 40:
            score += 1
            signals.append('KDJ低位')
        
        # 条件5: 股价 > MA20 (1分 加分)
        if price > ma20:
            score += 1
            signals.append('趋势向上')
        
        # 入选门槛: 至少4分
        if score >= 4:
            name = get_stock_name(sym)
            picks.append({
                'symbol': sym,
                'name': name,
                'price': price,
                'rsi': round(rsi, 1),
                'j_val': round(j_val, 1),
                'score': score,
                'signals': signals,
                'date': latest['date'].strftime('%Y-%m-%d')
            })
    
    # 按信号强度排序
    picks.sort(key=lambda x: (x['score'], -x['rsi']), reverse=True)
    
    return picks[:top_n]


def format_message(picks, date_str):
    """格式化推送消息"""
    if not picks:
        return f"""
📊 每日选股结果 ({date_str})

今日无符合条件的股票

筛选条件:
• RSI(14) 在 30~50 区间
• MA5 > MA10 (均线多头)
• 股价 > MA5
• J值 < 40 (加分)
• 股价 > MA20 (加分)

建议: 今日观望，等待信号
"""
    
    msg = f"""
📊 每日选股结果 ({date_str})

筛选条件: RSI超卖 + 均线多头
入选股票: {len(picks)} 只

━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, pick in enumerate(picks, 1):
        score_stars = '⭐' * min(pick['score'], 6)
        signals_str = '、'.join(pick['signals'])
        
        msg += f"""
{i}. {pick['name']} ({pick['symbol']})
   💰 价格: ¥{pick['price']:.2f}
   📈 RSI: {pick['rsi']}
   📊 J值: {pick['j_val']}
   ⭐ 强度: {pick['score']}分 {score_stars}
   ✓ 满足: {signals_str}

"""
    
    msg += """
━━━━━━━━━━━━━━━━━━━━━━

💡 操作建议:
• 优先信号强度 ≥5分
• 单只仓位 30%
• 持有 5~10 天
• 止盈: 移动止盈10%
• 止损: 固定止损 -8%

⚠️ 提醒: 熊市谨慎，仓位降低
"""
    
    return msg


def push_wechat(message):
    """推送到微信"""
    try:
        # 使用OpenClaw的message工具
        import subprocess
        result = subprocess.run([
            'openclaw', 'message', 'send',
            '--to', 'o9cq809xA2SNsQbJ5C02yWacjepU@im.wechat',
            '--channel', 'openclaw-weixin',
            '--message', message
        ], capture_output=True, text=True, timeout=30)
        
        return result.returncode == 0
    except Exception as e:
        print(f'推送失败: {e}')
        return False


def save_results(picks, date_str):
    """保存选股结果"""
    output_file = OUTPUT_DIR / f'daily_picks_{date_str}.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': date_str,
            'count': len(picks),
            'picks': picks
        }, f, ensure_ascii=False, indent=2)
    
    print(f'已保存: {output_file}')


def main():
    """主函数"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    print('='*50)
    print(f'📊 每日选股扫描 - {today}')
    print('='*50)
    print()
    
    # 扫描股票
    picks = scan_stocks(top_n=10)
    
    print(f'扫描完成: 发现 {len(picks)} 只候选股票')
    print()
    
    # 格式化消息
    message = format_message(picks, today)
    
    # 打印结果
    print(message)
    
    # 保存结果
    save_results(picks, today)
    
    # 推送消息
    if push_wechat(message):
        print('✅ 推送成功')
    else:
        print('❌ 推送失败')


if __name__ == '__main__':
    main()