#!/usr/bin/env python3
"""
鹏总选股系统 - 深度推送模块 v2.0
支持多渠道推送：微信 + 钉钉 + 邮件 + 企业微信

鹏总专用 - 2026 年 3 月 26 日
"""

import json
import smtplib
import urllib.request
import urllib.parse
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
import os


class PushNotifier:
    """多渠道推送通知器"""
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.history_file = "/home/admin/.openclaw/workspace/stocks/cache/push_history.json"
        self.load_history()
    
    def _load_config(self, config_file: str) -> dict:
        """加载配置文件"""
        default_config = {
            'wechat': {
                'enabled': False,
                'corp_id': '',
                'agent_id': '',
                'corp_secret': '',
            },
            'dingtalk': {
                'enabled': False,
                'webhook': '',
                'secret': '',
            },
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.qq.com',
                'smtp_port': 587,
                'from_email': '',
                'password': '',
                'to_emails': [],
            },
            'wecom': {
                'enabled': False,
                'webhook': '',
            },
            'push_settings': {
                'daily_report_time': '08:30',  # 每日报告时间
                'after_market_time': '15:30',  # 盘后推送时间
                'emergency_push': True,  # 紧急推送
                'push_top_n': 10,  # 推送 TOP N
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并配置
                    for key in default_config:
                        if key in config:
                            default_config[key].update(config[key])
            except:
                pass
        
        return default_config
    
    def load_history(self):
        """加载推送历史"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except:
                self.history = []
        else:
            self.history = []
    
    def save_history(self):
        """保存推送历史"""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def send_wechat(self, title: str, content: str, msg_type: str = 'text') -> bool:
        """企业微信推送"""
        if not self.config['wechat']['enabled']:
            return False
        
        try:
            # 获取 access_token
            token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.config['wechat']['corp_id']}&corpsecret={self.config['wechat']['corp_secret']}"
            
            req = urllib.request.Request(token_url)
            with urllib.request.urlopen(req, timeout=10) as response:
                token_data = json.loads(response.read().decode('utf-8'))
                access_token = token_data.get('access_token')
            
            if not access_token:
                return False
            
            # 发送消息
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            if msg_type == 'text':
                data = {
                    "touser": "@all",
                    "msgtype": "text",
                    "agentid": int(self.config['wechat']['agent_id']),
                    "text": {
                        "content": f"{title}\n\n{content}"
                    },
                    "safe": 0
                }
            elif msg_type == 'markdown':
                data = {
                    "touser": "@all",
                    "msgtype": "markdown",
                    "agentid": int(self.config['wechat']['agent_id']),
                    "markdown": {
                        "content": f"#{title}\n\n{content}"
                    }
                }
            
            req = urllib.request.Request(
                send_url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('errcode') == 0
        
        except Exception as e:
            print(f"微信推送失败：{e}")
            return False
    
    def send_dingtalk(self, title: str, content: str, msg_type: str = 'text') -> bool:
        """钉钉推送"""
        if not self.config['dingtalk']['enabled']:
            return False
        
        try:
            webhook = self.config['dingtalk']['webhook']
            
            if msg_type == 'text':
                data = {
                    "msgtype": "text",
                    "text": {
                        "content": f"{title}\n\n{content}"
                    }
                }
            elif msg_type == 'markdown':
                data = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title,
                        "text": f"## {title}\n\n{content}"
                    }
                }
            
            req = urllib.request.Request(
                webhook,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('errcode') == 0
        
        except Exception as e:
            print(f"钉钉推送失败：{e}")
            return False
    
    def send_wecom(self, title: str, content: str, msg_type: str = 'text') -> bool:
        """企业微信 webhook 推送"""
        if not self.config['wecom']['enabled']:
            return False
        
        try:
            webhook = self.config['wecom']['webhook']
            
            if msg_type == 'text':
                data = {
                    "msgtype": "text",
                    "text": {
                        "content": f"{title}\n\n{content}",
                        "mentioned_list": ["@all"]
                    }
                }
            elif msg_type == 'markdown':
                data = {
                    "msgtype": "markdown",
                    "markdown": {
                        "content": f"## {title}\n\n{content}"
                    }
                }
            
            req = urllib.request.Request(
                webhook,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('errcode') == 0
        
        except Exception as e:
            print(f"企业微信推送失败：{e}")
            return False
    
    def send_email(self, subject: str, content: str, html: bool = False) -> bool:
        """邮件推送"""
        if not self.config['email']['enabled']:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email']['from_email']
            msg['To'] = ', '.join(self.config['email']['to_emails'])
            msg['Subject'] = subject
            
            if html:
                msg.attach(MIMEText(content, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(
                self.config['email']['smtp_server'],
                self.config['email']['smtp_port']
            )
            server.starttls()
            server.login(
                self.config['email']['from_email'],
                self.config['email']['password']
            )
            server.send_message(msg)
            server.quit()
            
            return True
        
        except Exception as e:
            print(f"邮件推送失败：{e}")
            return False
    
    def send_all(self, title: str, content: str, msg_type: str = 'text') -> dict:
        """全渠道推送"""
        results = {
            'wechat': False,
            'dingtalk': False,
            'wecom': False,
            'email': False,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'title': title,
        }
        
        # 企业微信
        if self.config['wechat']['enabled']:
            results['wechat'] = self.send_wechat(title, content, msg_type)
        
        # 钉钉
        if self.config['dingtalk']['enabled']:
            results['dingtalk'] = self.send_dingtalk(title, content, msg_type)
        
        # 企业微信 webhook
        if self.config['wecom']['enabled']:
            results['wecom'] = self.send_wecom(title, content, msg_type)
        
        # 邮件
        if self.config['email']['enabled']:
            results['email'] = self.send_email(title, content, msg_type == 'html')
        
        # 保存历史
        self.history.append(results)
        self.save_history()
        
        return results
    
    def push_daily_report(self, market_data: dict, top_stocks: list, top_sectors: list):
        """推送每日报告"""
        title = f"📊 鹏总选股日报 {datetime.now().strftime('%Y-%m-%d')}"
        
        content = f"""
📈 市场概览
━━━━━━━━━━━━━━━━
上证指数：{market_data.get('sh_index', 'N/A')}
深证成指：{market_data.get('sz_index', 'N/A')}
创业板指：{market_data.get('cyb_index', 'N/A')}
成交量：{market_data.get('volume', 'N/A')}亿

🏆 主力净流入 TOP 10
━━━━━━━━━━━━━━━━
"""
        
        for i, stock in enumerate(top_stocks[:10], 1):
            content += f"{i}. {stock.get('name', 'N/A')} ({stock.get('code', 'N/A')})\n"
            content += f"   主力净额：{stock.get('main_net', 0)/100000000:.2f}亿\n"
            content += f"   涨幅：{stock.get('change_pct', 0):.2f}%\n\n"
        
        content += f"""
💡 热门板块
━━━━━━━━━━━━━━━━
"""
        
        for i, sector in enumerate(top_sectors[:5], 1):
            content += f"{i}. {sector.get('name', 'N/A')}\n"
            content += f"   主力净额：{sector.get('main_net', 0)/100000000:.2f}亿\n"
            content += f"   涨幅：{sector.get('change_pct', 0):.2f}%\n\n"
        
        content += f"""
⚠️ 风险提示：股市有风险，投资需谨慎
━━━━━━━━━━━━━━━━
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self.send_all(title, content, msg_type='text')
    
    def push_stock_signal(self, stock_code: str, stock_name: str, signal: dict):
        """推送个股信号"""
        action = signal.get('action', '未知')
        icon_map = {
            '强烈推荐买入': '🟢',
            '推荐买入': '🟢',
            '观望': '🟡',
            '不建议买入': '🔴'
        }
        icon = icon_map.get(action, '⚪')
        
        title = f"{icon} 选股信号：{stock_name}({stock_code})"
        
        content = f"""
📊 分析结果
━━━━━━━━━━━━━━━━
股票：{stock_name}({stock_code})
现价：¥{signal.get('price', 0):.2f}
涨跌幅：{signal.get('change_pct', 0):.2f}%

🎯 综合评分：{signal.get('total_score', 0):.1f}
   技术面：{signal.get('tech_score', 0)}
   基本面：{signal.get('fund_score', 0)}
   资金面：{signal.get('money_score', 0)}

💡 操作建议：{icon} {action}
建议仓位：{signal.get('position', 'N/A')}

📈 收益预测
━━━━━━━━━━━━━━━━
10 日预期：{signal.get('expected_return', 0):.1f}%
成功概率：{signal.get('probability', 0):.1f}%
目标价：¥{signal.get('target_price', 0):.2f}
止损价：¥{signal.get('stop_loss', 0):.2f}

📋 策略
━━━━━━━━━━━━━━━━
"""
        
        for strategy in signal.get('strategies', []):
            content += f"• {strategy}\n"
        
        content += f"""
━━━━━━━━━━━━━━━━
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self.send_all(title, content, msg_type='text')
    
    def push_emergency(self, title: str, content: str):
        """紧急推送"""
        if not self.config['push_settings'].get('emergency_push', True):
            return
        
        title = f"🚨 紧急提醒：{title}"
        self.send_all(title, content, msg_type='text')
    
    def push_stop_loss_alert(self, stock_code: str, stock_name: str, 
                            buy_price: float, current_price: float, 
                            stop_loss_price: float):
        """止损预警"""
        loss_pct = (current_price - buy_price) / buy_price * 100
        
        title = f"⚠️ 止损预警：{stock_name}({stock_code})"
        
        content = f"""
⚠️ 止损预警
━━━━━━━━━━━━━━━━
股票：{stock_name}({stock_code})
买入价：¥{buy_price:.2f}
现价：¥{current_price:.2f}
止损价：¥{stop_loss_price:.2f}
当前亏损：{loss_pct:.2f}%

💡 操作建议
━━━━━━━━━━━━━━━━
"""
        
        if current_price <= stop_loss_price:
            content += "🔴 已触及止损线，建议立即卖出！\n"
        elif loss_pct < -5:
            content += "🟡 亏损超过 5%，注意风险！\n"
        else:
            content += "⚪ 接近止损线，密切关注！\n"
        
        content += f"""
━━━━━━━━━━━━━━━━
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self.send_all(title, content, msg_type='text')
    
    def push_take_profit_alert(self, stock_code: str, stock_name: str,
                              buy_price: float, current_price: float,
                              target_price: float):
        """止盈预警"""
        profit_pct = (current_price - buy_price) / buy_price * 100
        
        title = f"✅ 止盈提醒：{stock_name}({stock_code})"
        
        content = f"""
✅ 止盈提醒
━━━━━━━━━━━━━━━━
股票：{stock_name}({stock_code})
买入价：¥{buy_price:.2f}
现价：¥{current_price:.2f}
目标价：¥{target_price:.2f}
当前盈利：{profit_pct:.2f}%

💡 操作建议
━━━━━━━━━━━━━━━━
"""
        
        if current_price >= target_price:
            content += "🟢 已达到目标价，建议分批止盈！\n"
        elif profit_pct > 20:
            content += "🟡 盈利超过 20%，可以考虑止盈！\n"
        else:
            content += "⚪ 接近目标价，继续持有！\n"
        
        content += f"""
━━━━━━━━━━━━━━━━
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self.send_all(title, content, msg_type='text')


# 配置示例
CONFIG_TEMPLATE = """
{
    "wechat": {
        "enabled": false,
        "corp_id": "你的企业 ID",
        "agent_id": "应用 ID",
        "corp_secret": "应用 Secret"
    },
    "dingtalk": {
        "enabled": false,
        "webhook": "钉钉机器人 webhook",
        "secret": "钉钉机器人加签密钥"
    },
    "wecom": {
        "enabled": false,
        "webhook": "企业微信机器人 webhook"
    },
    "email": {
        "enabled": false,
        "smtp_server": "smtp.qq.com",
        "smtp_port": 587,
        "from_email": "your_email@qq.com",
        "password": "授权码",
        "to_emails": ["receiver@example.com"]
    },
    "push_settings": {
        "daily_report_time": "08:30",
        "after_market_time": "15:30",
        "emergency_push": true,
        "push_top_n": 10
    }
}
"""


if __name__ == "__main__":
    # 测试推送
    notifier = PushNotifier()
    
    # 测试消息
    title = "📊 鹏总选股系统测试"
    content = """
这是测试消息

✅ 推送模块已就绪
✅ 支持多渠道推送
✅ 配置灵活

━━━━━━━━━━━━━━━━
生成时间：2026-03-26 23:30:00
"""
    
    print("\n📱 测试推送功能...\n")
    results = notifier.send_all(title, content, msg_type='text')
    
    print(f"推送结果：{json.dumps(results, ensure_ascii=False, indent=2)}")
    print("\n✅ 测试完成！\n")
