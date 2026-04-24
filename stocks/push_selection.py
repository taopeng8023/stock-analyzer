#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股结果推送模块

支持:
- 企业微信机器人
- 钉钉机器人
- 邮件推送
"""

import json
import requests
from pathlib import Path
from datetime import datetime


def push_to_wecom(content, webhook_url=None):
    """
    推送到企业微信
    
    Args:
        content: 文本内容
        webhook_url: 企业微信机器人 webhook 地址
    """
    if not webhook_url:
        print("⚠️  未配置企业微信 webhook")
        return False
    
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        result = resp.json()
        
        if result.get('errcode') == 0:
            print("✅ 企业微信推送成功")
            return True
        else:
            print(f"❌ 企业微信推送失败：{result}")
            return False
    
    except Exception as e:
        print(f"❌ 推送异常：{e}")
        return False


def push_to_dingtalk(content, webhook_url=None, secret=None):
    """
    推送到钉钉
    
    Args:
        content: 文本内容
        webhook_url: 钉钉机器人 webhook 地址
        secret: 加签密钥（可选）
    """
    if not webhook_url:
        print("⚠️  未配置钉钉 webhook")
        return False
    
    import hmac
    import hashlib
    import base64
    import urllib.parse
    import time
    
    # 加签处理
    if secret:
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
    
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "缠论 + 蜡烛图 每日选股",
            "text": content
        }
    }
    
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        result = resp.json()
        
        if result.get('errcode') == 0:
            print("✅ 钉钉推送成功")
            return True
        else:
            print(f"❌ 钉钉推送失败：{result}")
            return False
    
    except Exception as e:
        print(f"❌ 推送异常：{e}")
        return False


def format_selection_report(report):
    """格式化选股报告为 Markdown"""
    date = report.get('date', 'unknown')
    top_signals = report.get('top_signals', [])
    
    # 标题
    md = f"# 📊 缠论 + 蜡烛图 每日选股\n\n"
    md += f"**日期**: {date[:4]}-{date[4:6]}-{date[6:]}\n"
    md += f"**扫描股票**: {report.get('total_scanned', 0)} 只\n"
    md += f"**发现信号**: {report.get('total_signals', 0)} 个\n\n"
    
    # 选股列表
    md += "## 🎯 精选股票 TOP20\n\n"
    md += "| 排名 | 代码 | 形态 | 强度 | 量比 | 涨幅% |\n"
    md += "|------|------|------|------|------|------|\n"
    
    for i, s in enumerate(top_signals[:20], 1):
        md += f"| {i} | `{s['symbol']}` | {s['pattern']} | {s['signal_strength']:.2f} | {s['volume_ratio']:.2f} | {s['change_pct']:.2f}% |\n"
    
    # 操作建议
    md += "\n## 💡 操作建议\n\n"
    md += "1. **重点关注**: 信号强度 > 0.8 的股票\n"
    md += "2. **分批建仓**: 建议分 2-3 次买入\n"
    md += "3. **止损设置**: 建议设置 5-8% 止损\n"
    md += "4. **持仓周期**: 短线 3-5 天，中线 1-2 周\n\n"
    
    # 风险提示
    md += "⚠️ **风险提示**: 本策略仅供参考，不构成投资建议。股市有风险，投资需谨慎。\n"
    
    return md


def send_daily_selection(date=None):
    """发送每日选股报告"""
    # 读取最新报告
    output_dir = Path('/home/admin/.openclaw/workspace/stocks/daily_selection')
    
    if date:
        report_file = output_dir / f'selection_{date}.json'
    else:
        # 找最新的报告
        reports = sorted(output_dir.glob('selection_*.json'), reverse=True)
        if reports:
            report_file = reports[0]
        else:
            print("❌ 未找到选股报告")
            return False
    
    if not report_file.exists():
        print(f"❌ 报告文件不存在：{report_file}")
        return False
    
    # 加载报告
    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    # 格式化内容
    content = format_selection_report(report)
    
    # 读取配置
    config_file = Path('/home/admin/.openclaw/workspace/stocks/push_config.json')
    config = {}
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # 推送
    success = False
    
    # 企业微信
    if config.get('wecom_webhook'):
        if push_to_wecom(content, config['wecom_webhook']):
            success = True
    
    # 钉钉
    if config.get('dingtalk_webhook'):
        if push_to_dingtalk(content, config['dingtalk_webhook'], config.get('dingtalk_secret')):
            success = True
    
    if not success:
        print("⚠️  未配置任何推送渠道")
        print("\n📋 报告内容预览:")
        print(content)
    
    return success


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='推送选股结果')
    parser.add_argument('--date', type=str, help='选股日期 (YYYYMMDD)')
    args = parser.parse_args()
    
    send_daily_selection(args.date)
