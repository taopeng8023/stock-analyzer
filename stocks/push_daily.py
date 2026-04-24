#!/usr/bin/env python3
"""
股票每日推送脚本
读取配置，自动推送股票数据到微信

用法:
    python3 push_daily.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sina_stock import get_stock_quote, format_quote
from wechat_push import push_to_corp_webhook, push_to_serverchan, push_to_pushplus, format_stock_message
from datetime import datetime

# ============ 配置区 ============
# 选择一种推送方式，填写对应参数

# 企业微信（推荐）
CORP_WEBHOOK = ""  # 填入你的企业微信 webhook 地址

# Server 酱
SERVERCHAN_SENDKEY = ""  # 填入你的 SendKey

# PushPlus
PUSHPLUS_TOKEN = ""  # 填入你的 Token

# 关注的股票列表
WATCH_LIST = [
    "sh600000",  # 浦发银行
    "sh600519",  # 贵州茅台
    "sz000001",  # 平安银行
]
# ===============================


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始获取股票数据...")
    
    # 获取股票数据
    stocks = get_stock_quote(WATCH_LIST)
    
    if not stocks:
        print("❌ 获取股票数据失败")
        return False
    
    # 格式化消息
    title = f"📊 股票简报 {datetime.now().strftime('%m-%d %H:%M')}"
    content = format_stock_message(stocks)
    
    # 添加汇总信息
    up_count = sum(1 for s in stocks if s.get('change', 0) >= 0)
    down_count = len(stocks) - up_count
    summary = f"\n---\n📈 上涨：{up_count} 只  |  📉 下跌：{down_count} 只"
    content += summary
    
    print(f"📊 获取到 {len(stocks)} 只股票数据")
    print(content)
    
    # 推送
    success = False
    
    if CORP_WEBHOOK:
        print("\n📤 使用企业微信推送...")
        success = push_to_corp_webhook(CORP_WEBHOOK, title, content)
    elif SERVERCHAN_SENDKEY:
        print("\n📤 使用 Server 酱推送...")
        success = push_to_serverchan(SERVERCHAN_SENDKEY, title, content)
    elif PUSHPLUS_TOKEN:
        print("\n📤 使用 PushPlus 推送...")
        success = push_to_pushplus(PUSHPLUS_TOKEN, title, content)
    else:
        print("\n⚠️  未配置任何推送方式，请编辑 push_daily.py 填写配置")
        print("\n配置方法见 README.md")
        return False
    
    if success:
        print(f"\n✅ 推送完成！")
    else:
        print(f"\n❌ 推送失败，请检查配置")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
