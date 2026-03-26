#!/usr/bin/env python3
"""
工作流结果推送模块
将选股结果推送到企业微信

用法:
    python3 workflow_push.py --strategy multi --top 10 --push
    python3 workflow_push.py --pool --top 100 --push
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from wechat_push import push_to_corp_webhook
from stock_selector import StockSelector


def format_final_decision_message(stocks: list, max_chars: int = 3800) -> str:
    """
    格式化最终决策消息为 Markdown (优化版 - 控制字符数)
    按推荐程度排序：强烈推荐 > 推荐 > 谨慎推荐 > 观望
    
    Args:
        stocks: 股票列表 (dict)
        max_chars: 最大字符数 (企业微信限制 4096)
    
    Returns:
        str: Markdown 格式消息
    """
    if not stocks:
        return "暂无数据"
    
    # 按推荐程度排序
    rating_order = {'强烈推荐': 0, '推荐': 1, '谨慎推荐': 2, '关注': 3, '观望': 4}
    sorted_stocks = sorted(stocks, key=lambda x: (
        rating_order.get(x.get('rating', '观望'), 4),
        -x.get('confidence', 0),
        -x.get('final_score', 0)
    ))
    
    # 统计各评级数量
    rating_count = {}
    for s in sorted_stocks:
        rating = s.get('rating', '观望')
        rating_count[rating] = rating_count.get(rating, 0) + 1
    
    # 精简头部
    lines = [
        f"⏰{datetime.now().strftime('%m-%d %H:%M')}",
        f"📊 仅主板 | 排除创业/科创/北交所",
        f"⚠️ 仅供参考，不构成投资建议",
        ""
    ]
    
    # 按评级分组显示
    current_rating = None
    display_index = 0
    
    for s in sorted_stocks:
        # 检查字符数
        current_len = len("\n".join(lines))
        if current_len > max_chars - 200:  # 预留缓冲
            break
        
        rating = s.get('rating', '观望')
        
        # 添加评级分组标题 (精简)
        if rating != current_rating:
            current_rating = rating
            count = rating_count.get(rating, 0)
            
            if rating == '强烈推荐':
                lines.append(f"━━⭐⭐⭐强烈推荐 ({count})━━")
            elif rating == '推荐':
                lines.append(f"━━⭐⭐推荐 ({count})━━")
            elif rating == '谨慎推荐':
                lines.append(f"━━⭐谨慎推荐 ({count})━━")
            else:
                lines.append(f"━━⭕观望 ({count})━━")
            lines.append("")
        
        symbol = s.get('symbol', '')
        name = s.get('name', '')
        price = s.get('price', 0)
        change_pct = s.get('change_pct', 0)
        amount = s.get('amount', 0)
        appear_count = s.get('appear_count', 1)
        confidence = s.get('confidence', 40)
        stop_profit = s.get('stop_profit', 0)
        stop_loss = s.get('stop_loss', 0)
        reasons = s.get('reasons', [])
        
        display_index += 1
        
        # 涨跌符号
        if change_pct >= 5:
            change_sign = '📈'
        elif change_pct >= 0:
            change_sign = '📗'
        else:
            change_sign = '📉'
        
        # 成交额格式
        if amount >= 100000000:
            amount_str = f"{amount/100000000:.1f}亿"
        else:
            amount_str = f"{amount/10000:.0f}万"
        
        change_sign_text = '+' if change_pct >= 0 else ''
        
        # 评级符号
        if rating == '强烈推荐':
            rating_icon = '⭐⭐⭐'
        elif rating == '推荐':
            rating_icon = '⭐⭐'
        elif rating == '谨慎推荐':
            rating_icon = '⭐'
        else:
            rating_icon = '⭕'
        
        # 精简格式：只保留核心信息
        lines.append(f"{display_index}. {change_sign}{name}({symbol}){rating_icon}")
        lines.append(f"   ¥{price:.2f} {change_sign_text}{change_pct:.1f}% 成交{amount_str}")
        lines.append(f"   置信{confidence}% 止盈¥{stop_profit:.1f} 止损¥{stop_loss:.1f}")
        # 理由只显示前 2 个
        if reasons:
            reason_text = ' | '.join(reasons[:2])
            if len(reason_text) > 40:
                reason_text = reason_text[:37] + '...'
            lines.append(f"   💡{reason_text}")
        lines.append("")
    
    if len(sorted_stocks) > display_index:
        lines.append(f"...共{len(sorted_stocks)}只")
    
    result = "\n".join(lines)
    
    # 如果还是超长，强制截断
    if len(result) > max_chars:
        result = result[:max_chars-20] + "\n...(截断)"
    
    return result


def format_multi_pool_message(stocks: list, strategy: str) -> str:
    """
    格式化选股池消息为 Markdown
    
    Args:
        stocks: 股票列表 (dict)
        strategy: 策略类型
    
    Returns:
        str: Markdown 格式消息
    """
    if not stocks:
        return "暂无数据"
    
    lines = [
        f"_更新时间：{datetime.now().strftime('%m-%d %H:%M')}_",
        f"_数据来源：真实市场数据 (严禁估算)_",
        ""
    ]
    
    # 显示前 15 只
    for i, s in enumerate(stocks[:15], 1):
        symbol = s.get('symbol', '')
        name = s.get('name', '')
        price = s.get('price', 0)
        change_pct = s.get('change_pct', 0)
        amount = s.get('amount', 0)
        
        # 涨跌符号
        if change_pct >= 5:
            change_sign = '📈'
        elif change_pct >= 0:
            change_sign = '📗'
        else:
            change_sign = '📉'
        
        # 成交额格式
        if amount >= 100000000:
            amount_str = f"{amount/100000000:.2f}亿"
        else:
            amount_str = f"{amount/10000:.0f}万"
        
        # 主力净流入 (如果有)
        main_net = s.get('main_net', 0)
        if main_net and main_net != 0:
            if abs(main_net) >= 100000000:
                main_str = f"{main_net/100000000:.2f}亿"
            else:
                main_str = f"{main_net/10000:.0f}万"
            main_line = f"\n   💰主力：{main_str}"
        else:
            main_line = ""
        
        change_sign_text = '+' if change_pct >= 0 else ''
        
        lines.append(f"{i}. {change_sign} **{name}** ({symbol})")
        lines.append(f"   现价：¥{price:.2f} | 涨跌：{change_sign_text}{change_pct:.2f}%")
        lines.append(f"   成交：{amount_str}{main_line}")
        lines.append("")
    
    # 统计信息
    if len(stocks) > 15:
        lines.append(f"... 共 {len(stocks)} 只股票")
    
    return "\n".join(lines)


def format_main_pool_message(stocks: list) -> str:
    """
    格式化主力选股池消息
    
    Args:
        stocks: 股票列表 (dict)
    
    Returns:
        str: Markdown 格式消息
    """
    if not stocks:
        return "暂无数据"
    
    # 统计真实主力数据数量
    real_main_count = sum(1 for s in stocks if s.get('main_net', 0) != 0)
    
    lines = [
        f"_选股池数量：{len(stocks)} 只_",
        f"_真实主力数据：{real_main_count} 只_",
        f"_更新时间：{datetime.now().strftime('%m-%d %H:%M')}_",
        "",
        "⚠️ _无真实主力数据时按成交额排序 (严禁估算)_",
        ""
    ]
    
    # 显示前 15 只
    for i, s in enumerate(stocks[:15], 1):
        symbol = s.get('symbol', '')
        name = s.get('name', '')
        price = s.get('price', 0)
        change_pct = s.get('change_pct', 0)
        amount = s.get('amount', 0)
        main_net = s.get('main_net', 0)
        
        # 涨跌符号
        if change_pct >= 5:
            change_sign = '📈'
        elif change_pct >= 0:
            change_sign = '📗'
        else:
            change_sign = '📉'
        
        # 成交额格式
        if amount >= 100000000:
            amount_str = f"{amount/100000000:.2f}亿"
        else:
            amount_str = f"{amount/10000:.0f}万"
        
        # 主力净流入标识
        if main_net and main_net != 0:
            if abs(main_net) >= 100000000:
                main_str = f"{main_net/100000000:.2f}亿"
            else:
                main_str = f"{main_net/10000:.0f}万"
            source_mark = '💰'
        else:
            main_str = amount_str
            source_mark = '📊'
        
        change_sign_text = '+' if change_pct >= 0 else ''
        
        lines.append(f"{i}. {change_sign} **{name}** ({symbol})")
        lines.append(f"   现价：¥{price:.2f} | 涨跌：{change_sign_text}{change_pct:.2f}%")
        lines.append(f"   {source_mark}{main_str}")
        lines.append("")
    
    if len(stocks) > 15:
        lines.append(f"... 共 {len(stocks)} 只股票")
    
    return "\n".join(lines)


def push_workflow_result(webhook: str, strategy: str, stocks: list, 
                         top_n: int = 10, pool_mode: bool = False, 
                         is_final: bool = False, ml_enhanced: bool = False) -> bool:
    """
    推送工作流结果到企业微信
    
    Args:
        webhook: 企业微信 webhook 地址
        strategy: 策略类型
        stocks: 股票列表
        top_n: 显示数量
        pool_mode: 是否为主力选股池模式
        is_final: 是否为最终决策结果
    
    Returns:
        bool: 是否成功
    """
    if not stocks:
        print("❌ 无数据可推送")
        return False
    
    # 生成标题
    if pool_mode:
        title = f"🏦 主力选股池 Top{len(stocks)}"
        content = format_main_pool_message(stocks)
    elif is_final:
        title = f"🎯 工作流最终决策 Top{len(stocks)}"
        content = format_final_decision_message(stocks)
    else:
        strategy_names = {
            'multi': '多因子选股',
            'main': '主力净流入',
            'volume': '成交量排行',
            'change': '涨幅榜',
            'final': '最终决策',
        }
        strategy_name = strategy_names.get(strategy, '选股')
        title = f"📊 {strategy_name} Top{min(top_n, len(stocks))}"
        content = format_multi_pool_message(stocks, strategy)
    
    # 添加统一尾部
    content += "\n\n---\n"
    if is_final:
        content += "_💰 = 真实主力数据 | 📊 = 真实成交额数据_\n"
        content += "_🎯 综合多策略生成的最终决策_\n"
    else:
        content += "_💰 = 真实主力数据 | 📊 = 真实成交额数据_\n"
    content += "_⚠️ 严禁使用模拟/估算数据_"
    
    # 推送
    print(f"\n📤 推送到企业微信...")
    print(f"标题：{title}")
    print(f"股票数量：{len(stocks)} 只")
    
    success = push_to_corp_webhook(webhook, title, content)
    
    if success:
        print("✅ 推送成功!")
    else:
        print("❌ 推送失败")
    
    return success


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='工作流结果推送')
    parser.add_argument('--strategy', choices=['multi', 'main', 'volume', 'change', 'main_pool'],
                       default='multi', help='选股策略')
    parser.add_argument('--top', type=int, default=10, help='返回数量')
    parser.add_argument('--pool', action='store_true', help='主力选股池模式')
    parser.add_argument('--webhook', type=str, help='企业微信 Webhook 地址')
    parser.add_argument('--no-cache', action='store_true', help='不使用缓存')
    
    args = parser.parse_args()
    
    # 默认 Webhook
    webhook = args.webhook or "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5"
    
    # 初始化选股器
    selector = StockSelector()
    
    # 执行选股
    if args.pool or args.strategy == 'main_pool':
        stocks_data = selector.build_main_pool(top_n=args.top, use_cache=not args.no_cache)
        pool_mode = True
    else:
        stocks_data = selector.select(
            strategy=args.strategy,
            top_n=args.top,
            use_cache=not args.no_cache
        )
        pool_mode = False
    
    if not stocks_data:
        print("❌ 选股失败")
        return False
    
    # 转换为 dict
    stocks = [s.to_dict() for s in stocks_data]
    
    # 推送
    success = push_workflow_result(
        webhook=webhook,
        strategy=args.strategy,
        stocks=stocks,
        top_n=args.top,
        pool_mode=pool_mode
    )
    
    # 保存结果
    if stocks:
        cache_dir = Path(__file__).parent / 'cache'
        cache_dir.mkdir(exist_ok=True)
        
        if pool_mode:
            result_file = cache_dir / f"push_pool_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        else:
            result_file = cache_dir / f"push_{args.strategy}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'strategy': args.strategy,
                'pool_mode': pool_mode,
                'push_time': datetime.now().isoformat(),
                'count': len(stocks),
                'stocks': stocks
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 结果已保存：{result_file}")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
