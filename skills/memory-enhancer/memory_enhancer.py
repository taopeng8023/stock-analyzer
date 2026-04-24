#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 记忆增强系统 - 自动归档 + 关键词触发 + 定期整理
实现三大功能：
1. 自动归档 - 对话结束时自动总结写入记忆
2. 关键词触发 - 提到"记住"时自动存档
3. 定期整理 - 每周整理一次记忆文件
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 工作空间目录
WORKSPACE = Path('/home/admin/.openclaw/workspace')
MEMORY_DIR = WORKSPACE / 'memory'
MEMORY_FILE = WORKSPACE / 'MEMORY.md'

# 确保目录存在
MEMORY_DIR.mkdir(exist_ok=True)

# ============== 配置区域 ==============

# 关键词触发列表
MEMORY_KEYWORDS = [
    '记住',
    '记一下',
    '记下来',
    '存档',
    '保存这个',
    '记住这个',
    '别忘了',
    '重要',
    '标记',
    'record',
    'remember',
    'save this',
]

# 自动归档触发词（对话结束时）
ARCHIVE_TRIGGER = [
    '今天先到这',
    '下次再聊',
    '明天继续',
    '告辞',
    '拜拜',
    '再见',
    '结束',
    '总结',
]

# 每周整理时间（周日凌晨 2 点）
WEEKLY_ORGANIZE_DAY = 6  # 周日
WEEKLY_ORGANIZE_HOUR = 2

# ============== 记忆管理函数 ==============

def get_today_memory_path() -> Path:
    """获取今日记忆文件路径"""
    today = datetime.now().strftime('%Y-%m-%d')
    return MEMORY_DIR / f'{today}.md'

def parse_user_message(message: str) -> Dict:
    """解析用户消息，检测是否需要记忆"""
    result = {
        'need_memory': False,
        'memory_content': None,
        'memory_type': 'keyword',  # keyword | archive | weekly
        'urgency': 'normal'  # normal | important
    }
    
    # 检测关键词
    for keyword in MEMORY_KEYWORDS:
        if keyword in message:
            result['need_memory'] = True
            
            # 提取记忆内容（关键词后面的内容）
            pattern = f'{keyword}[：: ]*(.+)'
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                result['memory_content'] = match.group(1).strip()
            else:
                # 如果没有具体内容，记住整句话
                result['memory_content'] = message
            
            # 检测紧急程度
            if '重要' in message or '紧急' in message:
                result['urgency'] = 'important'
            
            break
    
    return result

def extract_session_summary(conversation: List[Dict]) -> str:
    """从对话中提取摘要"""
    # 简化版：提取最后几条关键消息
    summary_parts = []
    
    for msg in conversation[-10:]:  # 只看最后 10 条
        if msg.get('role') == 'user':
            content = msg.get('content', '')
            # 提取事实性信息
            if any(kw in content for kw in ['我是', '我叫', '我喜欢', '我想要', '我的', '成本', '持仓', '价格']):
                summary_parts.append(content)
    
    return '\n'.join(summary_parts) if summary_parts else None

def save_to_daily_memory(content: str, category: str = '对话记录'):
    """保存到今日记忆文件"""
    filepath = get_today_memory_path()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 读取现有内容
    existing = ''
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            existing = f.read()
    
    # 追加新内容
    new_entry = f'\n\n## [{timestamp}] {category}\n\n{content}\n'
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(existing + new_entry)
    
    return filepath

def save_to_longterm_memory(content: str, category: str = '重要信息'):
    """保存到长期记忆文件 (MEMORY.md)"""
    timestamp = datetime.now().strftime('%Y-%m-%d')
    
    # 读取现有内容
    existing = ''
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            existing = f.read()
    
    # 检查是否已存在类似内容（避免重复）
    if content[:20] in existing:
        return MEMORY_FILE, False  # 已存在
    
    # 查找 Notes 部分并插入
    notes_marker = '## Notes'
    if notes_marker in existing:
        # 插入到 Notes 之前
        parts = existing.split(notes_marker, 1)
        new_entry = f'\n## {category} ({timestamp})\n\n- {content}\n\n'
        final_content = parts[0] + new_entry + notes_marker + parts[1]
    else:
        # 追加到末尾
        new_entry = f'\n\n## {category} ({timestamp})\n\n- {content}\n'
        final_content = existing + new_entry
    
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    return MEMORY_FILE, True

def organize_weekly_memory():
    """每周整理记忆文件"""
    today = datetime.now()
    
    # 检查是否是整理日
    if today.weekday() != WEEKLY_ORGANIZE_DAY:
        return None, '不是整理日'
    
    # 读取本周记忆文件
    week_start = today - timedelta(days=today.weekday())
    week_files = []
    
    for i in range(7):
        date = week_start + timedelta(days=i)
        filepath = MEMORY_DIR / f'{date.strftime("%Y-%m-%d")}.md'
        if filepath.exists():
            week_files.append(filepath)
    
    if not week_files:
        return None, '本周无记忆文件'
    
    # 提取重要内容到 MEMORY.md
    important_items = []
    
    for filepath in week_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标记为重要的内容
        for line in content.split('\n'):
            if '重要' in line or '成本' in line or '持仓' in line or '偏好' in line:
                important_items.append(f'- {line.strip()}')
    
    if important_items:
        # 去重
        important_items = list(set(important_items))
        
        # 写入长期记忆
        timestamp = today.strftime('%Y-%m-%d')
        new_section = f'\n\n## 周度整理 ({timestamp})\n\n' + '\n'.join(important_items) + '\n'
        
        existing = ''
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                existing = f.read()
        
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            f.write(existing + new_section)
        
        return MEMORY_FILE, f'整理 {len(important_items)} 条重要信息'
    
    return None, '无重要内容需要整理'

def process_memory_request(message: str, conversation: List[Dict] = None) -> Dict:
    """处理记忆请求"""
    result = {
        'action': 'none',
        'message': '无需记忆操作',
        'file': None,
        'saved': False
    }
    
    # 1. 检测关键词触发
    parsed = parse_user_message(message)
    if parsed['need_memory'] and parsed['memory_content']:
        if parsed['urgency'] == 'important':
            # 重要信息保存到长期记忆
            filepath, saved = save_to_longterm_memory(parsed['memory_content'], '用户记忆')
            result['action'] = 'longterm_save'
            result['file'] = str(filepath)
            result['saved'] = saved
            result['message'] = f'✅ 已保存到长期记忆：{parsed["memory_content"][:50]}...'
        else:
            # 普通信息保存到今日记忆
            filepath = save_to_daily_memory(parsed['memory_content'], '对话记录')
            result['action'] = 'daily_save'
            result['file'] = str(filepath)
            result['saved'] = True
            result['message'] = f'📝 已保存到今日记忆：{parsed["memory_content"][:50]}...'
        
        return result
    
    # 2. 检测归档触发
    for trigger in ARCHIVE_TRIGGER:
        if trigger in message:
            if conversation:
                summary = extract_session_summary(conversation)
                if summary:
                    filepath = save_to_daily_memory(summary, '会话摘要')
                    result['action'] = 'archive'
                    result['file'] = str(filepath)
                    result['saved'] = True
                    result['message'] = '📦 已自动归档本次会话摘要'
                    return result
    
    return result

# ============== 命令行接口 ==============

def main():
    """命令行测试接口"""
    import sys
    
    print("=" * 60)
    print("🧠 AI 记忆增强系统 - 测试模式")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\n用法:")
        print("  python3 memory_enhancer.py \"记住：我持仓 002709 成本 45 元\"")
        print("  python3 memory_enhancer.py --weekly  # 执行周度整理")
        print("  python3 memory_enhancer.py --status  # 查看记忆状态")
        return
    
    if sys.argv[1] == '--weekly':
        filepath, msg = organize_weekly_memory()
        print(f"\n📅 周度整理：{msg}")
        if filepath:
            print(f"   文件：{filepath}")
        return
    
    if sys.argv[1] == '--status':
        print("\n📊 记忆文件状态:")
        print(f"   长期记忆：{MEMORY_FILE.exists()}")
        print(f"   今日记忆：{get_today_memory_path().exists()}")
        
        # 统计本周文件
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        count = 0
        for i in range(7):
            date = week_start + timedelta(days=i)
            filepath = MEMORY_DIR / f'{date.strftime("%Y-%m-%d")}.md'
            if filepath.exists():
                count += 1
        print(f"   本周记忆文件：{count}/7")
        return
    
    # 测试消息处理
    message = sys.argv[1]
    result = process_memory_request(message, [])
    
    print(f"\n💬 消息：{message}")
    print(f"📋 操作：{result['action']}")
    print(f"✅ 状态：{result['message']}")
    if result['file']:
        print(f"📁 文件：{result['file']}")

if __name__ == '__main__':
    main()
