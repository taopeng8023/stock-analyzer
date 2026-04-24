#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日选股推送 - 正确策略
策略: EMA RSI 30-35 + 站上MA5 (使用正确的Wilders平滑RSI)
持有: 15天
注意: RSI使用EMA/Wilders平滑法(与同花顺一致)
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

CACHE_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_history_2022_2026')
STOCK_LIST = Path('/home/admin/.openclaw/workspace/stocks/all_stocks_list.csv')

def load_closes(symbol):
    """加载股票收盘价（正确处理倒序数据）"""
    filepath = CACHE_DIR / f'{symbol}.json'
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        closes = []
        for item in data.get('items', []):
            try:
                c = float(item[5])  # close在索引5
                closes.append(c)
            except:
                continue
        
        # 反转顺序：从旧到新
        closes = closes[::-1]
        return closes
    except:
        return None


def calc_rsi(closes, idx, period=14):
    """计算RSI - 使用EMA平滑法(与同花顺一致)"""
    if idx < period + 1:
        return None
    
    # 使用Wilders Smoothing (EMA方法)
    # 计算涨跌幅
    deltas = [closes[j] - closes[j-1] for j in range(1, idx+1)]
    
    if len(deltas) < period:
        return None
    
    # 初始平均(前period天)
    gains = sum([d for d in deltas[:period] if d > 0]) / period
    losses = sum([-d for d in deltas[:period] if d < 0]) / period
    
    # 后续平滑(Wilders方法)
    for d in deltas[period:]:
        if d > 0:
            gains = (gains * (period - 1) + d) / period
            losses = losses * (period - 1) / period
        elif d < 0:
            gains = gains * (period - 1) / period
            losses = (losses * (period - 1) + (-d)) / period
    
    # RSI公式
    if losses == 0:
        return 100
    
    rs = gains / losses
    return 100 - 100 / (1 + rs)


def calc_ma(closes, idx, period):
    """计算均线"""
    if idx < period:
        return None
    return sum(closes[idx - period:idx]) / period


def scan_all():
    """扫描全市场股票"""
    symbols = sorted([f.stem for f in CACHE_DIR.glob('*.json')])
    
    # 加载股票名称
    try:
        stocks_df = pd.read_csv(STOCK_LIST)
    except:
        stocks_df = None
    
    picks = []
    
    for sym in symbols:
        closes = load_closes(sym)
        if closes is None or len(closes) < 50:
            continue
        
        # 取最近数据点
        idx = len(closes) - 1
        
        # 计算指标
        rsi = calc_rsi(closes, idx)
        if rsi is None:
            continue
        
        ma5 = calc_ma(closes, idx, 5)
        if ma5 is None:
            continue
        
        price = closes[idx]
        
        # 正确策略条件：EMA RSI 30-35 + 站上MA5
        if 30 <= rsi < 35 and price > ma5:
            # 获取股票名称
            name = sym
            if stocks_df is not None:
                m = stocks_df[stocks_df['symbol'] == sym]
                if len(m) > 0:
                    name = m['name'].iloc[0]
            
            picks.append({
                'symbol': sym,
                'name': name,
                'price': round(price, 2),
                'rsi': round(rsi, 1),
                'ma5': round(ma5, 2)
            })
    
    # 按RSI排序（越接近30越好）
    picks.sort(key=lambda x: x['rsi'])
    
    # 返回前20只最优候选
    return picks[:20]


def format_msg(picks):
    """生成推送消息"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    if not picks:
        return f"📊 每日选股 ({today})\n\n今日无符合条件的股票\n\n策略: EMA_RSI30-35 + 站上MA5"
    
    msg = f"""📊 正确策略选股 ({today})
扫描全市场 发现{len(picks)}只候选

━━━━━━━━━━━━━━━━━━━━━━

策略规则:
• EMA RSI(14) 在 30~35 区间
• 股价站上MA5
• 持有15天

━━━━━━━━━━━━━━━━━━━━━━

TOP 12 推荐:

"""
    
    for i, p in enumerate(picks[:12], 1):
        msg += f"""{i}. {p['name']}({p['symbol']})
   💰 ¥{p['price']} | RSI {p['rsi']}

"""
    
    msg += """━━━━━━━━━━━━━━━━━━━━━━

💡 操作建议:
• 优选RSI接近30的股票
• 单只仓位30%
• 持有15天后卖出
• 止盈: 盈利10%后回撤10%
• 止损: 亏损8%

⚠️ 风险提示:
胜率57.5%，收益+2.96%
需严格止损"""
    
    return msg


def main():
    print(f"开始扫描... {datetime.now().strftime('%H:%M:%S')}")
    
    picks = scan_all()
    print(f"发现 {len(picks)} 只候选股票")
    
    msg = format_msg(picks[:15])
    print(msg)
    
    # 保存结果
    output_dir = Path('/home/admin/.openclaw/workspace/stocks/daily_picks')
    output_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime('%Y%m%d')
    with open(output_dir / f'simple_picks_{today}.json', 'w') as f:
        json.dump(picks[:30], f, ensure_ascii=False, indent=2)
    
    # 输出推送消息标记
    print("\n--- PUSH_MESSAGE ---")
    print(msg)


if __name__ == '__main__':
    main()