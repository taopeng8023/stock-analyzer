#!/usr/bin/env python3
"""
股票数据自动推送脚本
结合本地爬虫 + 微信推送

用法:
    python3 auto_push.py              # 推送综合 Top10
    python3 auto_push.py --type main  # 推送主力排行
    python3 auto_push.py --top 20     # 推送 Top20
"""

import argparse
import sys
import os
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from local_crawler import StockCrawler
from wechat_push import push_to_corp_webhook


def format_message(stocks, rank_type='综合'):
    """格式化推送消息（真实数据 - 优化版）"""
    lines = [
        f"📊 **A 股{rank_type}排行榜**",
        f"_更新时间：{datetime.now().strftime('%m-%d %H:%M')}_",
        "",
        "_⚠️ 所有数据来自腾讯财经实时行情_"
    ]
    
    for i, s in enumerate(stocks, 1):
        change_sign = '📈' if s.get('change_pct', 0) >= 0 else '📉'
        amount_yi = s.get('amount_yuan', 0) / 100000000
        volume_wanshou = s.get('volume', 0) / 10000
        
        # 基本信息
        line1 = f"{i}. {change_sign} **{s.get('name', '')}** ({s.get('symbol', '')})"
        line2 = f"   现价：¥{s.get('price', 0):.2f} | 涨跌：{s.get('change_pct', 0):+.2f}%"
        line3 = f"   成交：{amount_yi:.2f}亿 ({volume_wanshou:.1f}万手)"
        
        lines.append(line1)
        lines.append(line2)
        lines.append(line3)
    
    return "\n".join(lines)


def is_trading_time() -> bool:
    """判断是否在 A 股交易时间"""
    now = datetime.now()
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    
    # 周末不交易
    if weekday >= 5:
        return False
    
    # 上午交易时间：9:30-11:30
    if hour == 9 and minute >= 30:
        return True
    if hour == 10:
        return True
    if hour == 11 and minute <= 30:
        return True
    
    # 下午交易时间：13:00-15:00
    if hour == 13:
        return True
    if hour == 14:
        return True
    if hour == 15 and minute <= 0:
        return True
    
    return False


def main():
    parser = argparse.ArgumentParser(description='股票数据自动推送')
    parser.add_argument('--type', choices=['score', 'main', 'volume', 'change'], default='volume',
                       help='排行类型：score=综合，main=主力，volume=成交量，change=涨跌幅')
    parser.add_argument('--top', type=int, default=30, help='前 N 只')
    parser.add_argument('--webhook', type=str, help='企业微信 Webhook 地址')
    parser.add_argument('--refresh', action='store_true', help='刷新缓存')
    parser.add_argument('--force', action='store_true', help='强制推送（忽略交易时间）')
    
    args = parser.parse_args()
    
    # 默认 Webhook
    webhook = args.webhook or "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5"
    
    # 检查交易时间
    if not args.force and not is_trading_time():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 非交易时间，跳过推送")
        return True
    
    # 初始化爬虫
    crawler = StockCrawler()
    
    # 刷新缓存
    if args.refresh:
        crawler.load_cache('stocks_cache.json', max_age_minutes=999999)  # 强制过期
        print("✅ 缓存已刷新")
    
    # 获取排行
    type_names = {
        'score': '综合',
        'main': '主力活跃',
        'volume': '成交量',
        'change': '涨跌幅',
    }
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取{type_names.get(args.type, '成交量')}排行 Top{args.top}...")
    
    # 获取排行数据（真实数据）
    stocks = crawler.get_ranking(rank_by=args.type, top_n=args.top, fetch_5day=False)
    
    if not stocks:
        print("❌ 获取数据失败")
        return False
    
    # 格式化消息
    rank_type_name = type_names.get(args.type, '成交量')
    content = format_message(stocks, rank_type=rank_type_name)
    
    # 添加交易时间提示
    if args.type == 'volume':
        title = f"📊 A 股{rank_type_name} Top{args.top}（实时）"
    else:
        title = f"📊 A 股{rank_type_name} Top{args.top}"
    
    # 推送
    print(f"📤 推送到企业微信...")
    success = push_to_corp_webhook(webhook, title, content)
    
    if success:
        print("✅ 推送成功!")
        return True
    else:
        print("❌ 推送失败")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
