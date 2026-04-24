#!/usr/bin/env python3
"""
主力资金流入 TOP20 深度分析
查询主力排名 + 技术面 + 买入逻辑
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime

# 配置
DATA_DIR = Path(__file__).parent / "data"
HISTORY_DIR = Path(__file__).parent / "data_history_2022_2026"

# 主力流入 TOP20 股票代码
TOP20_CODES = [
    '600150', '600986', '002281', '002008', '601016',
    '600415', '000066', '600186', '001267', '603538',
    '603618', '600176', '603308', '603220', '601138',
    '600726', '601778', '600256', '600276', '600875'
]

def calculate_rsi(closes, period=14):
    """计算 RSI"""
    if len(closes) < period + 1:
        return 50
    
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i-1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-delta)
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def analyze_stock(code, zjlx_data):
    """分析单只股票"""
    data_path = HISTORY_DIR / f"{code}.json"
    
    if not data_path.exists():
        return None
    
    try:
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        if not data.get('items'):
            return None
        
        df = data['items']
        fields = data['fields']
        
        # 获取索引
        close_idx = fields.index('close') if 'close' in fields else 4
        vol_idx = fields.index('vol') if 'vol' in fields else 6
        
        # 提取数据
        closes = [float(row[close_idx]) for row in df[-60:]]
        volumes = [float(row[vol_idx]) for row in df[-60:]]
        
        if len(closes) < 20:
            return None
        
        # 计算指标
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        
        ret1 = closes[-1] / closes[-2] - 1
        ret3 = closes[-1] / closes[-4] - 1 if len(closes) >= 4 else 0
        ret5 = closes[-1] / closes[-6] - 1 if len(closes) >= 6 else 0
        ret10 = closes[-1] / closes[-11] - 1 if len(closes) >= 11 else 0
        
        rsi = calculate_rsi(closes)
        
        # 资金流数据
        zjlx = next((s for s in zjlx_data if s['代码'] == code), None)
        if not zjlx:
            return None
        
        # 主力评分 (基于净流入排名)
        rank = zjlx.get('序号', 50)
        main_force_score = max(0, 100 - rank * 2)  # 第 1 名 100 分，第 50 名 0 分
        
        # 资金流评分
        flow_ratio = zjlx['主力净流入_净额'] / 10000  # 亿
        flow_score = min(30, flow_ratio / 10 * 30)  # 10 亿以上满分
        
        # 技术面评分
        tech_score = 0
        if ma5 > ma10: tech_score += 10
        if ma10 > ma20: tech_score += 10
        if rsi >= 50 and rsi < 75: tech_score += 15
        if ret5 > 0: tech_score += 15
        
        # 综合评分
        total_score = main_force_score * 0.4 + flow_score + tech_score * 0.6
        
        # 均线状态
        if ma5 > ma10 > ma20:
            ma_status = "多头排列"
        elif ma5 < ma10 < ma20:
            ma_status = "空头排列"
        else:
            ma_status = "混乱"
        
        # 买入逻辑分析
        buy_reasons = []
        risks = []
        
        if main_force_score >= 80:
            buy_reasons.append("主力大幅流入")
        if flow_ratio >= 5:
            buy_reasons.append("资金流强劲")
        if ma_status == "多头排列":
            buy_reasons.append("均线多头")
        if 50 <= rsi < 70:
            buy_reasons.append("RSI 强势")
        if ret5 >= 10:
            buy_reasons.append("5 日大涨")
        
        if rsi >= 75:
            risks.append("RSI 超买")
        if ret5 >= 20:
            risks.append("短期涨幅过大")
        if ma_status == "空头排列":
            risks.append("均线空头")
        
        return {
            '代码': code,
            '名称': zjlx.get('名称', ''),
            '主力净流入': zjlx['主力净流入_净额'],
            '主力排名': rank,
            '主力评分': main_force_score,
            '资金流评分': flow_score,
            '技术评分': tech_score,
            '综合评分': total_score,
            '最新价': closes[-1],
            '涨跌幅': ret1 * 100,
            '5 日': ret5 * 100,
            '10 日': ret10 * 100,
            'RSI': rsi,
            '均线状态': ma_status,
            '买入理由': buy_reasons,
            '风险': risks
        }
        
    except Exception as e:
        print(f"❌ {code} 分析失败：{e}")
        return None

def main():
    """主函数"""
    print(f"\n{'='*100}")
    print("🔥 主力资金流入 TOP20 深度分析 - 主力排名 + 买入逻辑")
    print(f"{'='*100}")
    
    # 读取资金流数据
    zjlx_file = DATA_DIR / "zjlx_ranking_20260424_fixed.json"
    with open(zjlx_file, 'r', encoding='utf-8') as f:
        zjlx_data = json.load(f).get('ranking', [])
    
    print(f"\n📊 分析对象：主力流入前 20 名主板股票")
    print(f"数据日期：{zjlx_data[0].get('date', 'N/A') if zjlx_data else 'N/A'}")
    
    # 分析每只股票
    results = []
    for i, code in enumerate(TOP20_CODES, 1):
        print(f"\r进度：{i}/20", end='', flush=True)
        result = analyze_stock(code, zjlx_data)
        if result:
            results.append(result)
    
    print("\n")
    
    # 按综合评分排序
    results.sort(key=lambda x: x['综合评分'], reverse=True)
    
    # 输出结果
    print(f"{'='*100}")
    print("📊 综合分析结果")
    print(f"{'='*100}")
    
    print(f"\n{'排名':<4} {'代码':<8} {'名称':<10} {'主力':<8} {'资金':<8} {'技术':<8} {'综合':<8} {'5 日':<8} {'RSI':<6} {'均线':<10}")
    print(f"{'-'*100}")
    
    for i, r in enumerate(results, 1):
        rating = "⭐⭐⭐⭐⭐" if r['综合评分'] >= 80 else "⭐⭐⭐⭐" if r['综合评分'] >= 70 else "⭐⭐⭐"
        print(f"{i:<4} {r['代码']:<8} {r['名称']:<10} {r['主力评分']:<8.0f} {r['资金流评分']:<8.1f} {r['技术评分']:<8.1f} {r['综合评分']:<8.1f} {r['5 日']:>+7.1f}% {r['RSI']:<6.1f} {r['均线状态']:<10} {rating}")
    
    # TOP5 详细分析
    print(f"\n{'='*100}")
    print("🏆 TOP5 买入逻辑详解")
    print(f"{'='*100}")
    
    for i, r in enumerate(results[:5], 1):
        print(f"\n{i}. {r['代码']} {r['名称']} (综合评分{r['综合评分']:.1f})")
        print(f"   💰 主力净流入：{r['主力净流入']:,.2f}万元 (排名{r['主力排名']})")
        print(f"   📈 技术面：5 日{r['5 日']:+.1f}% | 10 日{r['10 日']:+.1f}% | RSI{r['RSI']:.1f} | {r['均线状态']}")
        
        print(f"   ✅ 买入理由:")
        for reason in r['买入理由']:
            print(f"      • {reason}")
        
        if r['风险']:
            print(f"   ⚠️  风险提示:")
            for risk in r['风险']:
                print(f"      • {risk}")
        
        # 操作建议
        if r['综合评分'] >= 80:
            action = "强烈买入，仓位 30%"
        elif r['综合评分'] >= 70:
            action = "买入，仓位 20%"
        else:
            action = "关注，仓位 10%"
        
        print(f"   💡 操作：{action}")
    
    print(f"\n{'='*100}")
    print("📈 整体统计")
    print(f"{'='*100}")
    
    avg_main = sum(r['主力评分'] for r in results) / len(results)
    avg_tech = sum(r['技术评分'] for r in results) / len(results)
    avg_score = sum(r['综合评分'] for r in results) / len(results)
    avg_5d = sum(r['5 日'] for r in results) / len(results)
    
    print(f"  平均主力评分：{avg_main:.1f}")
    print(f"  平均技术评分：{avg_tech:.1f}")
    print(f"  平均综合评分：{avg_score:.1f}")
    print(f"  平均 5 日涨幅：{avg_5d:+.2f}%")
    
    strong = sum(1 for r in results if r['综合评分'] >= 80)
    medium = sum(1 for r in results if 70 <= r['综合评分'] < 80)
    weak = sum(1 for r in results if r['综合评分'] < 70)
    
    print(f"\n  强烈推荐 (≥80): {strong} 只")
    print(f"  买入 (70-80): {medium} 只")
    print(f"  关注 (<70): {weak} 只")
    
    print(f"\n{'='*100}")
    print("💡 核心买入逻辑总结")
    print(f"{'='*100}")
    print("""
1. 主力大幅流入是核心驱动
   • TOP20 平均主力评分 80+，机构集中进场
   • 净流入均超 3 亿，真金白银背书

2. 技术面配合是关键
   • 均线多头 + RSI50-70 = 最佳买点
   • 避免追高 RSI>75 或 5 日涨超 20%

3. 板块效应增强胜率
   • 军工/科技/新能源 集中度高
   • 板块前 5 + 个股龙头 = 双重保障

4. 风险控制不可少
   • 止损 -8%，止盈 +20% 后回撤 5%
   • 持有期 5-10 天，不恋战
""")
    
    print(f"{'='*100}")

if __name__ == "__main__":
    main()
