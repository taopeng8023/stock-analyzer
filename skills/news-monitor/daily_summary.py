#!/usr/bin/env python3
"""
消息监控技能 - 每日汇总推送脚本
用于每天早上的汇总推送

用法:
    python3 daily_summary.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# 添加路径
_script_dir = Path(__file__).resolve().parent
stocks_path = _script_dir.parent.parent / 'stocks'
sys.path.insert(0, str(stocks_path))
sys.path.insert(0, str(_script_dir))

from news_monitor import NewsMonitorSkill


def get_yesterday_history(history_file: Path) -> list:
    """获取昨天的消息历史"""
    if not history_file.exists():
        return []
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # 获取昨天的消息（简单按时间过滤）
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        
        messages = []
        for msg in history.get('messages', []):
            timestamp = msg.get('timestamp', '')
            if timestamp.startswith(yesterday_str):
                messages.append(msg)
        
        return messages
    except Exception as e:
        print(f"⚠️  读取历史失败：{e}")
        return []


def filter_unpushed_messages(messages: list) -> list:
    """筛选未推送的消息（A 股相关且影响等级≥3 星）"""
    from news_monitor import NewsMonitorSkill
    
    monitor = NewsMonitorSkill()
    unpushed = []
    
    for msg in messages:
        text = msg.get('title', '') + ' ' + msg.get('content', '')
        
        # 检查 A 股相关性
        if not monitor._is_a_share_related(text):
            continue
        
        # 简单分析影响等级
        analysis = monitor.analyze_impact(msg)
        if analysis.get('should_push', False):
            unpushed.append({
                'message': msg,
                'analysis': analysis
            })
    
    return unpushed


def format_summary_message(unpushed_list: list) -> str:
    """格式化汇总消息"""
    lines = []
    
    # 标题
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%m 月 %d 日')
    
    lines.append(f"📰 **A 股重要消息汇总**")
    lines.append(f"_统计时间：{date_str} 全天_")
    lines.append(f"_汇总推送：{datetime.now().strftime('%H:%M')}._")
    lines.append("")
    lines.append(f"📊 **共 {len(unpushed_list)} 条重要消息**")
    lines.append("")
    
    # 分类统计
    positive_count = sum(1 for u in unpushed_list if u['analysis'].get('direction') == 'positive')
    negative_count = sum(1 for u in unpushed_list if u['analysis'].get('direction') == 'negative')
    neutral_count = len(unpushed_list) - positive_count - negative_count
    
    if positive_count > 0:
        lines.append(f"🟢 正面消息：{positive_count}条")
    if negative_count > 0:
        lines.append(f"🔴 负面消息：{negative_count}条")
    if neutral_count > 0:
        lines.append(f"⚪ 中性消息：{neutral_count}条")
    
    lines.append("")
    lines.append("="*50)
    lines.append("")
    
    # 按星级排序，显示 Top10
    unpushed_list.sort(key=lambda x: len(x['analysis'].get('stars', '')), reverse=True)
    
    for i, item in enumerate(unpushed_list[:10], 1):
        msg = item['message']
        analysis = item['analysis']
        
        stars = analysis.get('stars', '')
        direction = analysis.get('direction_text', '⚪')
        title = msg.get('title', '无标题')
        source = msg.get('source', '未知')
        
        lines.append(f"**{i}. {direction} {stars}**")
        lines.append(f"   {title}")
        lines.append(f"   _来源：{source}_")
        lines.append("")
    
    if len(unpushed_list) > 10:
        lines.append(f"_... 还有 {len(unpushed_list) - 10} 条消息_")
        lines.append("")
    
    lines.append("="*50)
    lines.append("")
    lines.append("_⚠️ 消息仅供参考，不构成投资建议_")
    
    return "\n".join(lines)


def main():
    """运行每日汇总推送"""
    print("="*60)
    print("📰 消息监控 - 每日汇总推送")
    print(f"运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print()
    
    # 初始化
    config = {
        'webhook': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5'
    }
    monitor = NewsMonitorSkill(config=config)
    
    # 获取昨天的消息历史
    history_file = _script_dir / 'cache' / 'news_history.json'
    messages = get_yesterday_history(history_file)
    
    print(f"📊 昨天消息总数：{len(messages)}条")
    
    if not messages:
        print("😴 昨天无消息")
        return
    
    # 筛选未推送的消息
    unpushed = filter_unpushed_messages(messages)
    print(f"📋 未推送的重要消息：{len(unpushed)}条")
    
    if not unpushed:
        print("✅ 昨天的消息已全部推送")
        return
    
    # 生成汇总消息
    summary_content = format_summary_message(unpushed)
    
    # 推送
    title = f"📰 A 股重要消息汇总 ({len(unpushed)}条)"
    
    success = monitor.push_function(monitor.webhook, title, summary_content)
    
    if success:
        print(f"✅ 汇总推送成功!")
        print(f"   推送消息数：{len(unpushed)}条")
        print(f"   汇总为：1 条")
    else:
        print(f"❌ 汇总推送失败")
    
    print()
    print("="*60)


if __name__ == '__main__':
    main()
