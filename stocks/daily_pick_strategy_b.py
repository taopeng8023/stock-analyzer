#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案 B 实盘选股脚本 - 超跌反弹策略

买入条件:
- RSI(14) < 40 (超卖区域)
- 近 10 天跌幅 > 12% (大幅回调)
- 股价站上 MA5 (现价 > MA5，短期企稳)

输出:
- TOP10 选股列表
- 保存到 selections/daily_pick_{date}.json
- 打印可操作建议

用法:
    python3 daily_pick_strategy_b.py
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# 配置
CACHE_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026')
STOCK_LIST = Path('/Users/taopeng/.openclaw/workspace/stocks/all_stocks_list.csv')
OUTPUT_DIR = Path('/Users/taopeng/.openclaw/workspace/stocks/selections')
OUTPUT_DIR.mkdir(exist_ok=True)


def load_closes(symbol: str) -> list:
    """
    加载股票收盘价数据
    
    Args:
        symbol: 股票代码 (如 '000001.SZ')
    
    Returns:
        收盘价列表 (从旧到新排序)
    """
    filepath = CACHE_DIR / f'{symbol}.json'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        closes = []
        for item in data.get('items', []):
            try:
                # close 在索引 5
                c = float(item[5])
                closes.append(c)
            except (ValueError, IndexError):
                continue
        
        # 数据是倒序的 (新→旧)，需要反转 (旧→新)
        closes = closes[::-1]
        return closes
    except Exception:
        return None


def calc_rsi(closes: list, period: int = 14) -> float:
    """
    计算 RSI(14) - 使用 Wilders 平滑法 (与同花顺一致)
    
    Args:
        closes: 收盘价列表
        period: RSI 周期
    
    Returns:
        RSI 值
    """
    if len(closes) < period + 1:
        return None
    
    # 计算涨跌幅
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    
    if len(deltas) < period:
        return None
    
    # 初始平均 (前 period 天)
    gains = sum([d for d in deltas[:period] if d > 0]) / period
    losses = sum([-d for d in deltas[:period] if d < 0]) / period
    
    # 后续平滑 (Wilders 方法)
    for d in deltas[period:]:
        if d > 0:
            gains = (gains * (period - 1) + d) / period
            losses = losses * (period - 1) / period
        elif d < 0:
            gains = gains * (period - 1) / period
            losses = (losses * (period - 1) + (-d)) / period
    
    # RSI 公式
    if losses == 0:
        return 100
    
    rs = gains / losses
    return 100 - 100 / (1 + rs)


def calc_ma(closes: list, period: int) -> float:
    """
    计算移动平均线
    
    Args:
        closes: 收盘价列表
        period: 均线周期
    
    Returns:
        MA 值
    """
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def calc_10day_decline(closes: list) -> float:
    """
    计算近 10 天跌幅
    
    Args:
        closes: 收盘价列表
    
    Returns:
        跌幅百分比 (负值表示下跌)
    """
    if len(closes) < 11:
        return None
    
    price_now = closes[-1]
    price_10d_ago = closes[-11]
    
    if price_10d_ago == 0:
        return None
    
    decline = (price_now - price_10d_ago) / price_10d_ago * 100
    return decline


def get_stock_name(symbol: str) -> str:
    """
    获取股票名称
    
    Args:
        symbol: 股票代码
    
    Returns:
        股票名称
    """
    try:
        stocks_df = pd.read_csv(STOCK_LIST)
        match = stocks_df[stocks_df['symbol'] == symbol]
        if len(match) > 0:
            return match['name'].iloc[0]
    except Exception:
        pass
    return symbol


def scan_stocks() -> list:
    """
    扫描全市场股票，筛选符合方案 B 条件的股票
    
    Returns:
        符合条件的股票列表
    """
    symbols = [f.stem for f in CACHE_DIR.glob('*.json')]
    
    picks = []
    
    for sym in symbols:
        closes = load_closes(sym)
        if closes is None or len(closes) < 50:
            continue
        
        # 计算指标
        rsi = calc_rsi(closes, 14)
        if rsi is None:
            continue
        
        decline_10d = calc_10day_decline(closes)
        if decline_10d is None:
            continue
        
        ma5 = calc_ma(closes, 5)
        if ma5 is None:
            continue
        
        price = closes[-1]
        
        # 方案 B 条件:
        # 1. RSI(14) < 40
        # 2. 近 10 天跌幅 > 12% (即 decline < -12)
        # 3. 股价站上 MA5 (price > ma5)
        if rsi < 40 and decline_10d < -12 and price > ma5:
            name = get_stock_name(sym)
            
            # 计算相对 MA5 位置
            ma5_pct = (price - ma5) / ma5 * 100
            
            picks.append({
                'symbol': sym,
                'name': name,
                'price': round(price, 2),
                'rsi': round(rsi, 1),
                'decline_10d': round(decline_10d, 2),
                'ma5': round(ma5, 2),
                'ma5_pct': round(ma5_pct, 2)
            })
    
    # 排序：优先 RSI 低、跌幅大的
    picks.sort(key=lambda x: (x['rsi'], x['decline_10d']))
    
    return picks


def format_output(picks: list, date_str: str) -> str:
    """
    格式化输出结果
    
    Args:
        picks: 选股结果列表
        date_str: 日期字符串
    
    Returns:
        格式化的输出文本
    """
    output = f"""
╔══════════════════════════════════════════════════════════╗
║         方案 B 实盘选股 - 超跌反弹策略                    ║
║         日期：{date_str}                                  ║
╚══════════════════════════════════════════════════════════╝

📋 筛选条件:
   • RSI(14) < 40          (超卖区域)
   • 近 10 天跌幅 > 12%      (大幅回调)
   • 股价站上 MA5           (短期企稳)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    if not picks:
        output += "⚠️  今日无符合条件的股票\n"
        output += "\n💡 建议: 市场情绪较好，超跌机会较少，可关注其他策略\n"
        return output
    
    output += f"✅ 发现 {len(picks)} 只候选股票，TOP10 如下:\n\n"
    output += "┌─────┬──────────┬────────┬───────┬────────┬──────────┐\n"
    output += "│ 排名 │  代码    │  名称  │  RSI  │  跌幅  │ 相对 MA5 │\n"
    output += "├─────┼──────────┼────────┼───────┼────────┼──────────┤\n"
    
    for i, p in enumerate(picks[:10], 1):
        rank = f"#{i}"
        symbol = p['symbol']
        name = p['name'][:6]  # 限制名称长度
        rsi = f"{p['rsi']:.1f}"
        decline = f"{p['decline_10d']:.1f}%"
        ma5_pos = f"+{p['ma5_pct']:.1f}%" if p['ma5_pct'] > 0 else f"{p['ma5_pct']:.1f}%"
        
        output += f"│ {rank:^4}│ {symbol:^10}│ {name:^6} │ {rsi:^5} │ {decline:^6} │ {ma5_pos:^8} │\n"
    
    output += "└─────┴──────────┴────────┴───────┴────────┴──────────┘\n"
    
    # 详细列表
    output += "\n📊 详细信息:\n\n"
    for i, p in enumerate(picks[:10], 1):
        output += f"{i}. {p['name']}({p['symbol']})\n"
        output += f"   💰 现价：¥{p['price']:.2f}\n"
        output += f"   📈 RSI: {p['rsi']:.1f} (超卖)\n"
        output += f"   📉 10 日跌幅：{p['decline_10d']:.1f}%\n"
        output += f"   📊 MA5: ¥{p['ma5']:.2f} (股价在其上方 {p['ma5_pct']:.1f}%)\n"
        output += "\n"
    
    # 操作建议
    output += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 操作建议:

1️⃣ 建仓策略:
   • 优选 RSI < 35 且跌幅 > 15% 的股票
   • 分批建仓：首仓 30%，回调补仓 20%
   • 单只股票总仓位不超过 30%

2️⃣ 止盈策略:
   • 目标收益：8-12%
   • 达到 10% 后启动移动止盈 (回撤 3% 卖出)

3️⃣ 止损策略:
   • 固定止损：-8%
   • 时间止损：5 天不涨卖出

4️⃣ 风险提示:
   ⚠️ 超跌股可能存在基本面问题
   ⚠️ 需结合成交量确认企稳
   ⚠️ 避免接飞刀，等待 MA5 确认

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 数据已保存：selections/daily_pick_{date}.json

"""
    
    return output


def save_results(picks: list, date_str: str):
    """
    保存选股结果到 JSON 文件
    
    Args:
        picks: 选股结果列表
        date_str: 日期字符串
    """
    # 清理日期格式
    date_clean = date_str.replace('-', '')
    output_file = OUTPUT_DIR / f'daily_pick_{date_clean}.json'
    
    result = {
        'date': date_str,
        'strategy': '方案 B - 超跌反弹',
        'conditions': {
            'rsi_14': '< 40',
            'decline_10d': '> 12%',
            'price_vs_ma5': '> 0'
        },
        'total_count': len(picks),
        'top10': picks[:10]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"📁 数据已保存：{output_file}")


def main():
    """主函数"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    print("\n" + "="*60)
    print(f"🔍 开始扫描 - 方案 B 超跌反弹策略")
    print(f"📅 日期：{today}")
    print("="*60 + "\n")
    
    # 扫描股票
    picks = scan_stocks()
    
    # 格式化输出
    output = format_output(picks, today)
    print(output)
    
    # 保存结果
    save_results(picks, today)
    
    # 总结
    print("="*60)
    if picks:
        print(f"✅ 扫描完成：发现 {len(picks)} 只符合条件的股票")
        print(f"📊 已保存 TOP10 到 selections/daily_pick_{today.replace('-', '')}.json")
    else:
        print("⚠️  扫描完成：今日无符合条件的股票")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
