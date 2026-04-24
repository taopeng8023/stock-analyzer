#!/usr/bin/env python3
"""
股票数据微信推送模块
支持多种推送方式：
1. 企业微信机器人 (推荐，最简单)
2. 微信测试号
3. Server 酱
4. PushPlus

用法:
    python wechat_push.py --method corp --webhook YOUR_WEBHOOK --msg "股票提醒"
"""

import requests
import json
import argparse
from datetime import datetime


def push_to_corp_webhook(webhook: str, title: str, content: str) -> bool:
    """
    企业微信机器人推送
    
    Args:
        webhook: 机器人 webhook 地址
        title: 消息标题
        content: 消息内容
    
    Returns:
        bool: 是否成功
    """
    url = webhook
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"### {title}\n\n{content}"
        }
    }
    
    try:
        resp = requests.post(url, json=data, timeout=10)
        result = resp.json()
        if result.get('errcode') == 0:
            print(f"✅ 企业微信推送成功")
            return True
        else:
            print(f"❌ 企业微信推送失败：{result}")
            return False
    except Exception as e:
        print(f"❌ 推送异常：{e}")
        return False


def push_to_serverchan(sendkey: str, title: str, content: str) -> bool:
    """
    Server 酱推送 (https://sct.ftqq.com/)
    
    Args:
        sendkey: Server 酱 sendkey
        title: 标题
        content: 内容
    """
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": title,
        "desp": content
    }
    
    try:
        resp = requests.post(url, data=data, timeout=10)
        result = resp.json()
        if result.get('code') == 0:
            print(f"✅ Server 酱推送成功")
            return True
        else:
            print(f"❌ Server 酱推送失败：{result}")
            return False
    except Exception as e:
        print(f"❌ 推送异常：{e}")
        return False


def push_to_pushplus(token: str, title: str, content: str, channel: str = "wechat") -> bool:
    """
    PushPlus 推送 (http://www.pushplus.plus/)
    
    Args:
        token: PushPlus token
        title: 标题
        content: 内容
        channel: 渠道 (wechat 微信/cp 企业微信/sms 短信)
    """
    url = "http://www.pushplus.plus/send"
    data = {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown",
        "channel": channel
    }
    
    try:
        resp = requests.post(url, json=data, timeout=10)
        result = resp.json()
        if result.get('code') == 200:
            print(f"✅ PushPlus 推送成功")
            return True
        else:
            print(f"❌ PushPlus 推送失败：{result}")
            return False
    except Exception as e:
        print(f"❌ 推送异常：{e}")
        return False


def push_to_test_account(appid: str, appsecret: str, openid: str, 
                        template_id: str, data: dict, url: str = "") -> bool:
    """
    微信测试号推送
    
    Args:
        appid: 测试号 appid
        appsecret: 测试号 appsecret
        openid: 用户 openid
        template_id: 模板 ID
        data: 模板数据
        url: 点击跳转链接
    """
    # 1. 获取 access_token
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={appsecret}"
    try:
        resp = requests.get(token_url, timeout=10)
        token_result = resp.json()
        access_token = token_result.get('access_token')
        
        if not access_token:
            print(f"❌ 获取 access_token 失败：{token_result}")
            return False
        
        # 2. 发送模板消息
        send_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
        payload = {
            "touser": openid,
            "template_id": template_id,
            "url": url,
            "data": data
        }
        
        resp = requests.post(send_url, json=payload, timeout=10)
        result = resp.json()
        if result.get('errcode') == 0:
            print(f"✅ 微信测试号推送成功")
            return True
        else:
            print(f"❌ 微信测试号推送失败：{result}")
            return False
    except Exception as e:
        print(f"❌ 推送异常：{e}")
        return False


def format_stock_message(stocks: list) -> str:
    """格式化股票消息为 Markdown"""
    if not stocks:
        return "暂无数据"
    
    lines = []
    for s in stocks:
        change_sign = "📈" if s.get('change', 0) >= 0 else "📉"
        lines.append(f"{change_sign} **{s['name']}** ({s['symbol']})")
        lines.append(f"   当前：¥{s['current']:.2f}  |  涨跌：{s.get('change_percent', 0):+.2f}%")
        lines.append(f"   成交：{s.get('volume', 0):,}手  |  金额：{s.get('amount_wan', 0):.2f}万")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='股票数据微信推送')
    parser.add_argument('--method', choices=['corp', 'serverchan', 'pushplus', 'test'], 
                       required=True, help='推送方式')
    parser.add_argument('--webhook', help='企业微信 webhook 地址')
    parser.add_argument('--sendkey', help='Server 酱 sendkey')
    parser.add_argument('--token', help='PushPlus token')
    parser.add_argument('--appid', help='微信测试号 appid')
    parser.add_argument('--appsecret', help='微信测试号 appsecret')
    parser.add_argument('--openid', help='微信 openid')
    parser.add_argument('--template-id', help='微信模板 ID')
    parser.add_argument('--title', default='股票提醒', help='消息标题')
    parser.add_argument('--content', help='消息内容')
    parser.add_argument('--symbols', help='股票代码列表，逗号分隔')
    
    args = parser.parse_args()
    
    # 如果提供了股票代码，获取数据
    content = args.content
    if args.symbols:
        from sina_stock import get_stock_quote
        stocks = get_stock_quote(args.symbols.split(','))
        content = format_stock_message(stocks)
    
    # 推送
    success = False
    if args.method == 'corp':
        success = push_to_corp_webhook(args.webhook, args.title, content)
    elif args.method == 'serverchan':
        success = push_to_serverchan(args.sendkey, args.title, content)
    elif args.method == 'pushplus':
        success = push_to_pushplus(args.token, args.title, content)
    elif args.method == 'test':
        # 测试号需要模板数据
        data = {
            "first": {"value": args.title, "color": "#173177"},
            "content": {"value": content, "color": "#173177"},
            "remark": {"value": f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}", "color": "#999999"}
        }
        success = push_to_test_account(args.appid, args.appsecret, args.openid, 
                                       args.template_id, data)
    
    exit(0 if success else 1)
