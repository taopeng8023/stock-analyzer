#!/usr/bin/env python3
"""
简易股票研究分析工具
不依赖 pandas，纯 Python 实现

⚠️  仅用于个人研究学习

用法:
    python3 research_simple.py --demo    # 演示分析
"""

from research_db import ResearchDatabase
from datetime import datetime


def analyze_simple(db: ResearchDatabase, ts_code: str = '600000.SH'):
    """简单分析"""
    data = db.query_daily(ts_code, limit=60)
    
    if not data:
        print(f"❌ 无 {ts_code} 数据")
        return
    
    # 反转（从旧到新）
    data = data[::-1]
    
    print(f"\n{'='*70}")
    print(f"📈 {ts_code} 简易分析")
    print(f"{'='*70}")
    
    # 基本统计
    start_price = data[0]['close']
    end_price = data[-1]['close']
    total_return = (end_price / start_price - 1) * 100
    
    print(f"\n价格统计:")
    print(f"  期间：{data[0]['trade_date']} ~ {data[-1]['trade_date']}")
    print(f"  起始价：¥{start_price:.2f}")
    print(f"  结束价：¥{end_price:.2f}")
    print(f"  总收益：{total_return:+.2f}%")
    
    # 简单均线
    closes = [d['close'] for d in data]
    ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else closes[-1]
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
    
    print(f"\n均线分析:")
    print(f"  当前价格：¥{end_price:.2f}")
    print(f"  MA5: ¥{ma5:.2f} {'↑' if end_price > ma5 else '↓'}")
    print(f"  MA20: ¥{ma20:.2f} {'↑' if end_price > ma20 else '↓'}")
    
    # 资金流
    flow_data = db.query_moneyflow(ts_code, limit=30)
    if flow_data:
        total_net = sum(f['net_mf_amount'] for f in flow_data)
        positive_days = sum(1 for f in flow_data if f['net_mf_amount'] > 0)
        
        print(f"\n资金流统计 (近{len(flow_data)}日):")
        print(f"  累计净流入：{total_net:.2f}万")
        print(f"  净流入天数：{positive_days}/{len(flow_data)}")
    
    print(f"{'='*70}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='简易股票研究分析')
    parser.add_argument('--demo', action='store_true', help='演示分析')
    parser.add_argument('--code', type=str, help='分析指定股票')
    
    args = parser.parse_args()
    
    db = ResearchDatabase()
    
    if args.demo:
        # 检查是否有数据
        stats = db.get_stats()
        if stats['daily_bar_count'] == 0:
            print("\n⚠️  数据库为空，先生成示例数据:")
            print("   python3 research_import.py --sample --days 60")
            return
        
        # 获取股票列表
        stocks = db.query_stock_list()
        if not stocks:
            print("❌ 无股票数据")
            return
        
        ts_code = stocks[0].get('ts_code', '600000.SH')
        analyze_simple(db, ts_code)
        return
    
    if args.code:
        ts_code = args.code.upper()
        if not ts_code.endswith('.SH') and not ts_code.endswith('.SZ'):
            ts_code += '.SH' if ts_code.startswith('6') else '.SZ'
        analyze_simple(db, ts_code)
        return
    
    # 默认
    db.print_stats()


if __name__ == '__main__':
    main()
