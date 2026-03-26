#!/usr/bin/env python3
"""
消息监控技能 - 收盘后每小时推送脚本
用于股市收盘后（15:00-23:00）每小时推送一次

用法:
    python3 after_market_push.py
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加路径
_script_dir = Path(__file__).resolve().parent
stocks_path = _script_dir.parent.parent / 'stocks'
sys.path.insert(0, str(stocks_path))
sys.path.insert(0, str(_script_dir))

from news_monitor import NewsMonitorSkill


def main():
    """运行收盘后推送"""
    print("="*60)
    print("📰 消息监控 - 收盘后推送")
    print(f"运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print()
    
    # 初始化
    config = {
        'webhook': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5'
    }
    monitor = NewsMonitorSkill(config=config)
    
    # 获取消息
    news_list = monitor.fetch_news()
    
    if not news_list:
        print("😴 无新消息")
        return
    
    # 分析并推送
    push_count = 0
    skip_count = 0
    
    for news in news_list:
        analysis = monitor.analyze_impact(news)
        
        confidence = analysis.get('sentiment_confidence', 0)
        print(f"  📊 {analysis['direction_text']} {analysis['stars']} (置信度：{confidence:.0%})")
        
        if analysis['should_push']:
            monitor.push_news(analysis)
            push_count += 1
        else:
            skip_count += 1
    
    print()
    print(f"✅ 获取到 {len(news_list)} 条新消息")
    print(f"✅ 本次推送 {push_count} 条消息")
    print(f"⏭️  跳过 {skip_count} 条（未达推送门槛）")
    
    # 打印健康报告
    if monitor.health_monitor:
        print()
        print("="*60)
        print("📊 数据源健康状态")
        print("="*60)
        
        health = monitor.health_monitor.get_all_health()
        healthy_count = sum(1 for h in health.values() if h['status'] == 'healthy')
        warning_count = sum(1 for h in health.values() if h['status'] in ['warning', 'degraded'])
        error_count = sum(1 for h in health.values() if h['status'] == 'error')
        
        print(f"🟢 健康：{healthy_count}个")
        if warning_count > 0:
            print(f"🟡 警告：{warning_count}个")
        if error_count > 0:
            print(f"🔴 异常：{error_count}个")


if __name__ == '__main__':
    main()
