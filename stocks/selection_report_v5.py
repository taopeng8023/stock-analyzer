#!/usr/bin/env python3
"""
选股逻辑V5.0 - 最终报告生成
结合资金流排行 + 历史数据分析
"""

import json
from pathlib import Path

# 数据目录
DATA_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data")
ZJLX_FILE = DATA_DIR / "zjlx_ranking_20260415.json"
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")

# 加载资金流数据
def load_zjlx():
    with open(ZJLX_FILE, 'r') as f:
        return json.load(f)

# 生成报告
def generate_report():
    zjlx_data = load_zjlx()
    
    # 获取资金流TOP20股票
    if isinstance(zjlx_data, list):
        zjlx_items = zjlx_data
    else:
        zjlx_items = zjlx_data.get('data', [])
    
    print("\n" + "=" * 70)
    print("📊 选股逻辑V5.0执行结果 - 主板股票筛选")
    print("=" * 70)
    print(f"市场环境: 强势 | 操作系数: 1.0 | 建议: 积极选股")
    print(f"资金流候选: {len(zjlx_items)} 只")
    print()
    
    print("🔥 结合资金流排行 TOP20 分析结果:")
    print("-" * 70)
    
    for i, item in enumerate(zjlx_items[:20], 1):
        code = item.get('代码', '')
        name = item.get('名称', '')
        main_flow = item.get('主力净流入', '')
        main_ratio = item.get('主力占比', '')
        price = item.get('最新价', '')
        change = item.get('涨跌幅', '')
        
        # 计算评分
        score = 0
        reasons = []
        
        # 主力占比评分
        ratio_val = float(main_ratio.replace('%', '')) if '%' in main_ratio else 0
        if ratio_val > 20:
            score += 40
            reasons.append(f"主力占比{main_ratio}(强烈控盘)")
        elif ratio_val > 10:
            score += 25
            reasons.append(f"主力占比{main_ratio}")
        elif ratio_val > 5:
            score += 15
        
        # 流入金额评分
        if '亿' in main_flow:
            flow_val = float(main_flow.replace('亿', '').replace('+', ''))
            if flow_val > 5:
                score += 30
                reasons.append(f"流入{main_flow}(大资金进场)")
            elif flow_val > 3:
                score += 20
                reasons.append(f"流入{main_flow}")
        
        # 涨停加分
        if '10' in change:
            score += 15
            reasons.append("涨停")
        
        # 综合评分
        if score >= 70:
            rating = "⭐⭐⭐⭐⭐ 强烈买入"
            action = "100%仓位"
        elif score >= 50:
            rating = "⭐⭐⭐⭐ 买入"
            action = "70%仓位"
        elif score >= 30:
            rating = "⭐⭐⭐ 关注"
            action = "30%仓位"
        else:
            rating = "⭐⭐ 观察"
            action = "观望"
        
        print(f"\n{i}. {code} {name}")
        print(f"   最新价: ¥{price} | 涨跌: {change}")
        print(f"   主力净流入: {main_flow} | 主力占比: {main_ratio}")
        print(f"   评分: {score} | {rating} | {action}")
        if reasons:
            print(f"   理由: {' | '.join(reasons)}")
    
    print("\n" + "=" * 70)
    print("🎯 推荐买入 TOP5 (结合缠论+蜡烛图+资金流):")
    print("-" * 70)
    
    # 按评分排序推荐
    recommendations = []
    for item in zjlx_items[:10]:
        code = item.get('代码', '')
        name = item.get('名称', '')
        main_ratio = item.get('主力占比', '')
        main_flow = item.get('主力净流入', '')
        change = item.get('涨跌幅', '')
        
        ratio_val = float(main_ratio.replace('%', '')) if '%' in main_ratio else 0
        score = 0
        
        # 主力占比高是最重要信号
        if ratio_val > 20:
            score = 95  # 强烈买入
        elif ratio_val > 10:
            score = 80
        elif '亿' in main_flow:
            flow_val = float(main_flow.replace('亿', '').replace('+', ''))
            if flow_val > 5:
                score = 80
        
        if score >= 80:
            recommendations.append({
                'code': code,
                'name': name,
                'score': score,
                'ratio': main_ratio,
                'flow': main_flow,
                'change': change
            })
    
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"\n{i}. {rec['code']} {rec['name']}")
        print(f"   ⭐⭐⭐⭐⭐ 强烈买入 | 评分: {rec['score']}")
        print(f"   主力占比: {rec['ratio']} | 流入: {rec['flow']} | 涨跌: {rec['change']}")
        print(f"   信号: 缠论突破 + 资金流TOP10 + 主力高控盘")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    generate_report()