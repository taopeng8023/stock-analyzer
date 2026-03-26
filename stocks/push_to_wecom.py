#!/usr/bin/env python3
"""
鹏总选股系统 - 企业微信选股信号推送
自动推送综合评分≥70 的股票

使用方法:
1. 配置企业微信 webhook
2. 运行脚本自动推送选股信号

鹏总专用 - 2026 年 3 月 26 日
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deep_push import PushNotifier
from stock_analyzer.stock_analyzer_v2 import EnhancedStockAnalyzer
import json
from datetime import datetime


def push_stock_signal(stock_code: str, config_file: str = 'push_config.json'):
    """分析股票并推送选股信号"""
    
    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    notifier = PushNotifier(config_path)
    
    # 分析股票
    analyzer = EnhancedStockAnalyzer()
    report = analyzer.analyze(stock_code)
    
    if 'error' in report:
        print(f"❌ 分析失败：{report['error']}")
        return
    
    # 检查是否需要推送
    total_score = report['scores']['total']
    min_score = notifier.config['push_settings'].get('min_score_to_push', 70)
    
    if total_score < min_score:
        print(f"⚪ 评分{total_score:.1f} < {min_score}，不推送")
        return
    
    # 构建推送消息
    stock_name = report['stock_name']
    current_price = report['current_price']
    change_pct = report['change_pct']
    
    advice = report['buy_advice']
    icon = advice['icon']
    action = advice['action']
    position = advice['position']
    
    prediction = report['prediction']
    prob = report['success_probability']
    targets = report['target_prices']
    
    # Markdown 格式消息
    content = f"""## {icon} 选股信号：{stock_name}({stock_code})

### 📊 分析结果
- **现价**: ¥{current_price:.2f} ({change_pct:+.2f}%)
- **综合评分**: **{total_score:.1f}分**
  - 技术面：{report['scores']['technical']}
  - 基本面：{report['scores']['fundamental']}
  - 资金面：{report['scores']['money_flow']}

### 💡 操作建议
- **建议**: {icon} **{action}**
- **仓位**: {position}

### 📈 收益预测
- **10 日预期**: {prediction['expected_return']:+.1f}%
- **成功概率**: {prob['probability']:.1f}% ({prob['level']})
- **目标价**: ¥{targets['target']:.2f} (+{prediction['expected_return']:.1f}%)
- **止损价**: ¥{targets['stop_loss']:.2f} (-8%)

### 📋 交易策略
"""
    
    for strategy in advice['strategies']:
        content += f"- {strategy}\n"
    
    content += f"""
---
*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*鹏总选股系统 v3.0*
"""
    
    # 推送消息
    title = f"{icon} {stock_name}({stock_code}) - {action}"
    
    print(f"\n📱 准备推送选股信号...")
    print(f"   股票：{stock_name}({stock_code})")
    print(f"   评分：{total_score:.1f}")
    print(f"   建议：{action}")
    
    # 发送到企业微信
    result = notifier.send_wecom(title, content, msg_type='markdown')
    
    if result:
        print(f"✅ 推送成功！")
    else:
        print(f"❌ 推送失败，请检查 webhook 配置")
    
    # 保存推送记录
    push_record = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stock_code': stock_code,
        'stock_name': stock_name,
        'score': total_score,
        'action': action,
        'success': result,
    }
    
    history_file = os.path.join(os.path.dirname(__file__), 'cache/push_signals.json')
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            pass
    
    history.append(push_record)
    
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"📁 推送记录已保存：{history_file}")
    
    return result


def push_top_stocks(top_n: int = 10, config_file: str = 'push_config.json'):
    """推送主力净流入 TOP N 股票"""
    
    from eastmoney_money_flow import EastmoneyMoneyFlow
    
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    notifier = PushNotifier(config_path)
    flow = EastmoneyMoneyFlow()
    
    # 获取主力排名
    rank = flow.get_main_force_rank(page=1, page_size=top_n)
    
    if not rank:
        print("❌ 获取主力排名失败")
        return
    
    # 构建推送消息
    content = f"""## 📊 主力净流入 TOP {top_n}

**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 💰 主力排名
"""
    
    for i, stock in enumerate(rank[:top_n], 1):
        code = stock.get('f12', 'N/A')
        name = stock.get('f14', 'N/A')
        price = stock.get('f2', 0) or 0
        change = stock.get('f3', 0) or 0
        main_net = (stock.get('f4001', 0) or 0) / 100000000
        main_ratio = stock.get('f4002', 0) or 0
        
        content += f"""
**{i}. {name}({code})**
- 价格：¥{price:.2f} ({change:+.2f}%)
- 主力：{main_net:.2f}亿 ({main_ratio:.2f}%)
"""
    
    content += f"""
---
*数据来源：东方财富*
*鹏总选股系统 v3.0*
"""
    
    title = f"📊 主力净流入 TOP {top_n}"
    
    print(f"\n📱 推送主力排名 TOP {top_n}...")
    result = notifier.send_wecom(title, content, msg_type='markdown')
    
    if result:
        print(f"✅ 推送成功！")
    else:
        print(f"❌ 推送失败")
    
    return result


def push_sector_rank(top_n: int = 10, config_file: str = 'push_config.json'):
    """推送板块排名"""
    
    from sector_rank import EastmoneySectorRank
    
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    notifier = PushNotifier(config_path)
    sector = EastmoneySectorRank()
    
    # 获取行业排名
    industry_rank = sector.get_industry_rank(page=1, page_size=top_n)
    
    if not industry_rank:
        print("❌ 获取板块排名失败")
        return
    
    content = f"""## 🏭 行业板块资金流向 TOP {top_n}

**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 🔥 热门板块
"""
    
    for i, sec in enumerate(industry_rank[:top_n], 1):
        code = sec.get('f12', 'N/A')
        name = sec.get('f14', 'N/A')
        price = sec.get('f2', 0) or 0
        change = sec.get('f3', 0) or 0
        main_net = (sec.get('f62', 0) or 0) / 100000000
        main_ratio = sec.get('f184', 0) or 0
        
        content += f"""
**{i}. {name}**
- 最新价：{price:.2f} ({change:+.2f}%)
- 主力：{main_net:.2f}亿 ({main_ratio:.2f}%)
"""
    
    content += f"""
---
*数据来源：东方财富*
*鹏总选股系统 v3.0*
"""
    
    title = f"🏭 行业板块 TOP {top_n}"
    
    print(f"\n📱 推送板块排名...")
    result = notifier.send_wecom(title, content, msg_type='markdown')
    
    if result:
        print(f"✅ 推送成功！")
    else:
        print(f"❌ 推送失败")
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='鹏总选股系统 - 企业微信推送')
    parser.add_argument('--stock', type=str, help='股票代码，如 601899')
    parser.add_argument('--top', type=int, help='推送主力 TOP N，如 10')
    parser.add_argument('--sector', action='store_true', help='推送板块排名')
    parser.add_argument('--config', type=str, default='push_config.json', help='配置文件')
    
    args = parser.parse_args()
    
    if args.stock:
        push_stock_signal(args.stock, args.config)
    elif args.top:
        push_top_stocks(args.top, args.config)
    elif args.sector:
        push_sector_rank(args.config)
    else:
        # 默认测试推送
        print("\n📱 鹏总选股系统 - 企业微信推送\n")
        print("用法:")
        print("  python3 push_to_wecom.py --stock 601899    # 推送个股信号")
        print("  python3 push_to_wecom.py --top 10          # 推送主力 TOP 10")
        print("  python3 push_to_wecom.py --sector          # 推送板块排名")
        print()
