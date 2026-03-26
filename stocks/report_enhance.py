#!/usr/bin/env python3
"""
报告增强功能
- 添加数据标注（真实/估算）
- 添加历史对比
- 添加报告摘要

用法:
    python3 report_enhance.py --enhance    # 生成增强版报告
    python3 report_enhance.py --compare    # 历史对比
    python3 report_enhance.py --summary    # 报告摘要
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ============ 数据标注系统 ============

DATA_SOURCE_LABELS = {
    'real': {
        'icon': '✅',
        'label': '真实数据',
        'color': '🟢',
        'description': '来自腾讯财经真实市场数据'
    },
    'estimated': {
        'icon': '⚠️',
        'label': '估算数据',
        'color': '🟡',
        'description': '基于成交额×15% 估算'
    },
    'model': {
        'icon': '📊',
        'label': '模型分析',
        'color': '🔵',
        'description': '基于公开信息的分析模型'
    },
    'policy': {
        'icon': '🏛️',
        'label': '政策信息',
        'color': '🟣',
        'description': '来自官方公开渠道'
    }
}


def add_data_labels(report_data: dict) -> dict:
    """
    为报告添加数据标注
    
    Args:
        report_data: 原始报告数据
    
    Returns:
        带标注的报告数据
    """
    enhanced = report_data.copy()
    
    # 添加数据来源标注
    enhanced['data_sources'] = {
        'price': 'real',      # 价格 - 真实
        'change_pct': 'real',  # 涨跌幅 - 真实
        'volume': 'real',     # 成交量 - 真实
        'amount': 'real',     # 成交额 - 真实
        'main_net': 'estimated',  # 主力流入 - 估算
        'fundamental': 'model',   # 基本面 - 模型
        'policy': 'policy',       # 政策 - 官方
    }
    
    # 添加标注说明
    enhanced['labels'] = DATA_SOURCE_LABELS
    
    return enhanced


def format_with_labels(text: str, data_type: str) -> str:
    """
    格式化文本并添加标注
    
    Args:
        text: 原始文本
        data_type: 数据类型（real/estimated/model/policy）
    
    Returns:
        带标注的文本
    """
    label = DATA_SOURCE_LABELS.get(data_type, DATA_SOURCE_LABELS['model'])
    return f"{label['icon']} {text}"


# ============ 历史对比系统 ============

HISTORY_FILE = Path(__file__).parent / 'cache' / 'report_history.json'


def save_report_history(report_data: dict):
    """
    保存报告到历史记录
    
    Args:
        report_data: 报告数据
    """
    # 确保目录存在
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    
    # 加载历史
    history = load_report_history()
    
    # 添加新记录
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M:%S'),
        'data': report_data
    }
    history.append(record)
    
    # 只保留最近 30 天
    if len(history) > 30:
        history = history[-30:]
    
    # 保存
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_report_history() -> list:
    """
    加载历史记录
    
    Returns:
        历史记录列表
    """
    if not HISTORY_FILE.exists():
        return []
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        return history
    except:
        return []


def compare_with_yesterday(current_data: dict) -> dict:
    """
    与昨日报告对比
    
    Args:
        current_data: 当前报告数据
    
    Returns:
        对比结果
    """
    history = load_report_history()
    
    if not history:
        return {
            'has_history': False,
            'message': '暂无历史数据，明日开始对比'
        }
    
    # 获取昨日数据
    yesterday = history[-1]['data']
    
    # 对比各项指标
    comparison = {
        'has_history': True,
        'date': history[-1]['date'],
        'changes': {}
    }
    
    # 1. 对比股票池变化
    current_stocks = set()
    yesterday_stocks = set()
    
    if 'stocks' in current_data:
        current_stocks = {s.get('symbol', '') for s in current_data['stocks'][:10]}
    if 'stocks' in yesterday:
        yesterday_stocks = {s.get('symbol', '') for s in yesterday['stocks'][:10]}
    
    comparison['changes']['new_stocks'] = list(current_stocks - yesterday_stocks)
    comparison['changes']['removed_stocks'] = list(yesterday_stocks - current_stocks)
    
    # 2. 对比平均上涨概率
    if 'stocks' in current_data and 'stocks' in yesterday:
        current_prob = sum(s.get('probability', 0) for s in current_data['stocks'][:10]) / 10
        yesterday_prob = sum(s.get('probability', 0) for s in yesterday['stocks'][:10]) / 10
        prob_change = current_prob - yesterday_prob
        
        comparison['changes']['avg_probability'] = {
            'current': round(current_prob, 1),
            'yesterday': round(yesterday_prob, 1),
            'change': round(prob_change, 1),
            'trend': '📈' if prob_change > 0 else '📉' if prob_change < 0 else '➡️'
        }
    
    # 3. 对比政策数量
    if 'policies' in current_data and 'policies' in yesterday:
        current_count = len(current_data['policies'])
        yesterday_count = len(yesterday['policies'])
        policy_change = current_count - yesterday_count
        
        comparison['changes']['policies'] = {
            'current': current_count,
            'yesterday': yesterday_count,
            'change': policy_change,
            'trend': '➕' if policy_change > 0 else '➖' if policy_change < 0 else '➡️'
        }
    
    # 4. 对比市场情绪
    if 'market_sentiment' in current_data and 'market_sentiment' in yesterday:
        current_sentiment = current_data['market_sentiment']
        yesterday_sentiment = yesterday['market_sentiment']
        
        comparison['changes']['sentiment'] = {
            'current': current_sentiment,
            'yesterday': yesterday_sentiment,
            'trend': '😊' if current_sentiment > yesterday_sentiment else '😟' if current_sentiment < yesterday_sentiment else '😐'
        }
    
    return comparison


def format_comparison(comparison: dict) -> str:
    """
    格式化对比结果
    
    Args:
        comparison: 对比结果
    
    Returns:
        格式化的对比文本
    """
    if not comparison.get('has_history'):
        return f"📊 历史对比：{comparison.get('message', '无数据')}"
    
    lines = ["📊 **vs 昨日报告** (" + comparison.get('date', 'N/A') + ")"]
    lines.append("")
    
    changes = comparison.get('changes', {})
    
    # 股票池变化
    if 'new_stocks' in changes and changes['new_stocks']:
        lines.append(f"🆕 新入选：{', '.join(changes['new_stocks'][:3])}")
    if 'removed_stocks' in changes and changes['removed_stocks']:
        lines.append(f"❌ 剔除：{', '.join(changes['removed_stocks'][:3])}")
    
    # 平均概率变化
    if 'avg_probability' in changes:
        prob = changes['avg_probability']
        change_str = f"+{prob['change']}" if prob['change'] > 0 else f"{prob['change']}"
        lines.append(f"📈 平均概率：{prob['current']}% ({prob['trend']} {change_str}%)")
    
    # 政策变化
    if 'policies' in changes:
        policy = changes['policies']
        change_str = f"+{policy['change']}" if policy['change'] > 0 else f"{policy['change']}"
        lines.append(f"🏛️ 政策数量：{policy['current']} ({policy['trend']} {change_str})")
    
    # 情绪变化
    if 'sentiment' in changes:
        sentiment = changes['sentiment']
        lines.append(f"😊 市场情绪：{sentiment['current']} {sentiment['trend']}")
    
    return "\n".join(lines)


# ============ 报告摘要系统 ============

def generate_summary(report_data: dict) -> str:
    """
    生成 3 句话报告摘要
    
    Args:
        report_data: 报告数据
    
    Returns:
        摘要文本
    """
    summary_lines = []
    
    # 1. 市场情绪总结
    sentiment = report_data.get('market_sentiment', '中性')
    if sentiment >= 70:
        sentiment_str = "市场情绪乐观"
    elif sentiment >= 50:
        sentiment_str = "市场情绪谨慎偏多"
    elif sentiment >= 30:
        sentiment_str = "市场情绪中性"
    else:
        sentiment_str = "市场情绪谨慎"
    
    summary_lines.append(f"📊 {sentiment_str}")
    
    # 2. 重点板块
    if 'hot_sectors' in report_data and report_data['hot_sectors']:
        sectors = report_data['hot_sectors'][:2]
        summary_lines.append(f"🔥 重点关注：{', '.join(sectors)}")
    else:
        summary_lines.append("🔥 重点关注：银行、科技")
    
    # 3. 风险提示
    if 'risk_warning' in report_data:
        summary_lines.append(f"⚠️ {report_data['risk_warning']}")
    else:
        summary_lines.append("⚠️ 注意控制仓位，设置止损")
    
    return "\n".join(summary_lines)


# ============ 完整报告生成 ============

def generate_enhanced_report(current_data: dict) -> str:
    """
    生成增强版完整报告
    
    Args:
        current_data: 当前报告数据
    
    Returns:
        增强版报告文本
    """
    # 1. 添加数据标注
    enhanced_data = add_data_labels(current_data)
    
    # 2. 生成摘要
    summary = generate_summary(current_data)
    
    # 3. 历史对比
    comparison = compare_with_yesterday(current_data)
    comparison_text = format_comparison(comparison)
    
    # 4. 保存历史
    save_report_history(current_data)
    
    # 5. 组装报告
    report = []
    
    # 报告头
    report.append("="*80)
    report.append("📊 市场分析报告（增强版）")
    report.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)
    report.append("")
    
    # 摘要
    report.append("📋 **3 句话总结**")
    report.append(summary)
    report.append("")
    report.append("-"*80)
    report.append("")
    
    # 历史对比
    report.append(comparison_text)
    report.append("")
    report.append("-"*80)
    report.append("")
    
    # 原始报告内容
    if 'content' in current_data:
        report.append(current_data['content'])
    else:
        report.append("📈 详细分析内容...")
    
    report.append("")
    report.append("-"*80)
    report.append("")
    
    # 数据标注说明
    report.append("📝 **数据标注说明**")
    for key, label in enhanced_data['labels'].items():
        report.append(f"  {label['icon']} {label['label']}: {label['description']}")
    report.append("")
    report.append("="*80)
    
    return "\n".join(report)


# ============ 主函数 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='报告增强功能')
    parser.add_argument('--enhance', action='store_true', help='生成增强版报告')
    parser.add_argument('--compare', action='store_true', help='历史对比')
    parser.add_argument('--summary', action='store_true', help='报告摘要')
    
    args = parser.parse_args()
    
    # 示例数据
    sample_data = {
        'market_sentiment': 65,
        'hot_sectors': ['银行', '科技', '能源'],
        'risk_warning': '涨幅过大股票警惕回调',
        'stocks': [
            {'symbol': '000001', 'name': '平安银行', 'probability': 66.4},
            {'symbol': '600256', 'name': '广汇能源', 'probability': 65.6},
        ],
        'policies': ['央行降准', 'AI 政策', '新能源支持'],
        'content': '详细分析内容...'
    }
    
    if args.enhance:
        report = generate_enhanced_report(sample_data)
        print(report)
    elif args.compare:
        comparison = compare_with_yesterday(sample_data)
        print(format_comparison(comparison))
    elif args.summary:
        summary = generate_summary(sample_data)
        print("📋 **3 句话总结**")
        print(summary)
    else:
        parser.print_help()
        print("\n示例:")
        print("  python3 report_enhance.py --enhance  # 生成增强版报告")
        print("  python3 report_enhance.py --compare  # 查看历史对比")
        print("  python3 report_enhance.py --summary  # 生成报告摘要")


if __name__ == '__main__':
    main()
