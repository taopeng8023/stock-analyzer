#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票短期买入推荐系统 v2.0
整合资金流评分的综合评分模型
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# ==================== 配置 ====================

# 股票池（51 只）
STOCK_POOL = [
    {"code": "002475", "name": "立讯精密", "sector": "苹果链/AI"},
    {"code": "300308", "name": "中际旭创", "sector": "CPO"},
    {"code": "300383", "name": "光环新网", "sector": "IDC"},
    {"code": "300394", "name": "天孚通信", "sector": "光器件"},
    {"code": "600487", "name": "亨通光电", "sector": "光通信"},
    {"code": "600549", "name": "厦门钨业", "sector": "稀土"},
    {"code": "688781", "name": "华鑫股份", "sector": "券商"},
    {"code": "688525", "name": "佰维存储", "sector": "存储芯片"},
    {"code": "301682", "name": "胜宏科技", "sector": "PCB"},
    {"code": "603601", "name": "再升科技", "sector": "新材料"},
    {"code": "002281", "name": "光迅科技", "sector": "光模块"},
    {"code": "600498", "name": "烽火通信", "sector": "通信设备"},
    {"code": "600111", "name": "北方稀土", "sector": "稀土"},
    {"code": "600589", "name": "ST 榕泰", "sector": "化工"},
    {"code": "601869", "name": "长飞光纤", "sector": "光纤"},
    {"code": "000988", "name": "华工科技", "sector": "激光"},
    {"code": "002428", "name": "云南锗业", "sector": "半导体材料"},
    {"code": "601899", "name": "紫金矿业", "sector": "有色金属"},
    {"code": "600522", "name": "中天科技", "sector": "海缆"},
    {"code": "688521", "name": "芯原股份", "sector": "芯片设计"},
    {"code": "300017", "name": "网宿科技", "sector": "CDN"},
    {"code": "603986", "name": "兆易创新", "sector": "存储芯片"},
    {"code": "688313", "name": "仕佳光子", "sector": "光芯片"},
    {"code": "002371", "name": "北方华创", "sector": "半导体设备"},
    {"code": "601985", "name": "中国核电", "sector": "核电"},
    {"code": "002460", "name": "赣锋锂业", "sector": "锂电池"},
    {"code": "002467", "name": "二六三", "sector": "通信服务"},
    {"code": "603618", "name": "杭电股份", "sector": "电缆"},
    {"code": "600157", "name": "永泰能源", "sector": "煤炭"},
    {"code": "603799", "name": "华友钴业", "sector": "钴镍"},
    {"code": "603993", "name": "洛阳钼业", "sector": "有色金属"},
    {"code": "300763", "name": "锦浪科技", "sector": "逆变器"},
    {"code": "000592", "name": "平潭发展", "sector": "林业"},
    {"code": "601138", "name": "工业富联", "sector": "AI 服务器"},
    {"code": "300136", "name": "信维通信", "sector": "天线"},
    {"code": "300548", "name": "博创科技", "sector": "光模块"},
    {"code": "688041", "name": "海光信息", "sector": "CPU"},
    {"code": "000426", "name": "兴业银锡", "sector": "有色金属"},
    {"code": "688167", "name": "炬光科技", "sector": "激光雷达"},
    {"code": "300751", "name": "迈为股份", "sector": "光伏设备"},
    {"code": "002466", "name": "天齐锂业", "sector": "锂电池"},
    {"code": "002580", "name": "圣阳股份", "sector": "电池"},
    {"code": "600726", "name": "华电能源", "sector": "电力"},
    {"code": "000690", "name": "宝新能源", "sector": "电力"},
    {"code": "600011", "name": "华能国际", "sector": "电力"},
    {"code": "002353", "name": "杰瑞股份", "sector": "油服"},
    {"code": "000960", "name": "锡业股份", "sector": "有色金属"},
    {"code": "300442", "name": "润泽科技", "sector": "IDC"},
    {"code": "603179", "name": "新泉股份", "sector": "汽车零部件"},
    {"code": "600875", "name": "东方电气", "sector": "电力设备"},
]

# 评分维度权重
WEIGHTS = {
    "技术面": 0.25,    # 25 分
    "资金面": 0.20,    # 20 分（含资金流评分）
    "题材面": 0.25,    # 25 分
    "基本面": 0.15,    # 15 分
    "风险面": 0.15,    # 15 分
}

# ==================== 评分函数 ====================

def calculate_technical_score(price_change: float, volume_ratio: float, position_52w: float) -> float:
    """技术面评分（0-25 分）"""
    score = 12.5  # 基础分
    
    # 涨跌幅评分（最高 +8 分）
    if price_change >= 9.5:  # 涨停
        score += 8
    elif price_change >= 5:
        score += 6
    elif price_change >= 2:
        score += 4
    elif price_change >= 0:
        score += 2
    elif price_change <= -5:
        score -= 6
    elif price_change <= -2:
        score -= 3
    
    # 量比评分（最高 +5 分）
    if volume_ratio >= 3:
        score += 5
    elif volume_ratio >= 2:
        score += 3
    elif volume_ratio >= 1:
        score += 1
    elif volume_ratio <= 0.5:
        score -= 3
    
    # 52 周位置评分
    if position_52w <= 30:  # 低位
        score += 4
    elif position_52w <= 50:
        score += 2
    elif position_52w >= 90:  # 高位风险
        score -= 4
    
    return max(0, min(25, score))

def calculate_fund_score(main_net_inflow: float, main_ratio: float, super_ratio: float) -> float:
    """
    资金流评分（0-20 分）
    main_net_inflow: 主力净流入（万元）
    main_ratio: 主力净流入占比（%）
    super_ratio: 超大单净流入占比（%）
    """
    score = 10.0  # 基础分
    
    # 主力净流入占比评分（最高 +6 分）
    if main_ratio >= 10:
        score += 6
    elif main_ratio >= 5:
        score += 4
    elif main_ratio >= 2:
        score += 2
    elif main_ratio >= 0:
        score += 1
    elif main_ratio <= -10:
        score -= 6
    elif main_ratio <= -5:
        score -= 4
    elif main_ratio <= -2:
        score -= 2
    elif main_ratio < 0:
        score -= 1
    
    # 超大单净流入评分（最高 +4 分）
    if super_ratio >= 5:
        score += 4
    elif super_ratio >= 2:
        score += 2
    elif super_ratio >= 0:
        score += 1
    elif super_ratio <= -5:
        score -= 4
    elif super_ratio <= -2:
        score -= 2
    elif super_ratio < 0:
        score -= 1
    
    return max(0, min(20, score))

def calculate_theme_score(sector: str, is_hot_concept: bool) -> float:
    """题材面评分（0-25 分）"""
    score = 12.5  # 基础分
    
    # 热门板块加分
    hot_sectors = ["CPO", "光模块", "AI 服务器", "存储芯片", "半导体设备", "有色金属", "锂电池"]
    if sector in hot_sectors:
        score += 8
    elif "光" in sector or "电" in sector or "芯片" in sector:
        score += 5
    elif is_hot_concept:
        score += 6
    
    return max(0, min(25, score))

def calculate_fundamental_score(pe_ttm: float, profit_growth: float, debt_ratio: float) -> float:
    """基本面评分（0-15 分）"""
    score = 7.5  # 基础分
    
    # PE 评分
    if 0 < pe_ttm <= 20:
        score += 3
    elif 20 < pe_ttm <= 40:
        score += 1
    elif pe_ttm <= 0:  # 亏损
        score -= 3
    elif pe_ttm > 80:
        score -= 2
    
    # 利润增长评分
    if profit_growth >= 50:
        score += 4
    elif profit_growth >= 20:
        score += 2
    elif profit_growth >= 0:
        score += 1
    elif profit_growth <= -30:
        score -= 3
    
    # 负债率评分
    if debt_ratio <= 40:
        score += 2
    elif debt_ratio <= 60:
        score += 0
    elif debt_ratio >= 80:
        score -= 2
    
    return max(0, min(15, score))

def calculate_risk_score(position_52w: float, is_loss: bool, has_limit_down: bool) -> float:
    """风险面评分（0-15 分）"""
    score = 7.5  # 基础分
    
    # 52 周位置风险
    if position_52w >= 90:
        score -= 4
    elif position_52w >= 75:
        score -= 2
    elif position_52w <= 20:
        score += 3
    
    # 亏损风险
    if is_loss:
        score -= 3
    
    # 跌停风险
    if has_limit_down:
        score -= 4
    
    return max(0, min(15, score))

def calculate_comprehensive_score(stock_data: Dict) -> Dict:
    """计算综合评分（100 分制）"""
    # 各维度评分
    tech_score = calculate_technical_score(
        stock_data.get("price_change", 0),
        stock_data.get("volume_ratio", 1),
        stock_data.get("position_52w", 50)
    )
    
    fund_score = calculate_fund_score(
        stock_data.get("main_net_inflow", 0),
        stock_data.get("main_ratio", 0),
        stock_data.get("super_ratio", 0)
    )
    
    theme_score = calculate_theme_score(
        stock_data.get("sector", ""),
        stock_data.get("is_hot_concept", False)
    )
    
    fundamental_score = calculate_fundamental_score(
        stock_data.get("pe_ttm", 30),
        stock_data.get("profit_growth", 0),
        stock_data.get("debt_ratio", 50)
    )
    
    risk_score = calculate_risk_score(
        stock_data.get("position_52w", 50),
        stock_data.get("is_loss", False),
        stock_data.get("has_limit_down", False)
    )
    
    # 加权总分（100 分制）
    # tech_score: 0-25, fund_score: 0-20, theme_score: 0-25, fundamental_score: 0-15, risk_score: 0-15
    total_score = (
        tech_score +  # 25 分
        fund_score +  # 20 分
        theme_score +  # 25 分
        fundamental_score +  # 15 分
        risk_score  # 15 分
    )
    # 总分 0-100 分
    
    # 短期盈利概率估算
    if total_score >= 80:
        win_prob = 75
    elif total_score >= 70:
        win_prob = 65
    elif total_score >= 60:
        win_prob = 55
    elif total_score >= 50:
        win_prob = 45
    else:
        win_prob = 35
    
    return {
        **stock_data,
        "tech_score": round(tech_score, 1),
        "fund_score": round(fund_score, 1),
        "theme_score": round(theme_score, 1),
        "fundamental_score": round(fundamental_score, 1),
        "risk_score": round(risk_score, 1),
        "total_score": round(total_score, 1),
        "win_probability": win_prob,
    }

def get_rating(score: float) -> str:
    """获取评级（100 分制）"""
    if score >= 80:
        return "⭐⭐⭐⭐⭐ 强烈推荐"
    elif score >= 70:
        return "⭐⭐⭐⭐ 推荐"
    elif score >= 60:
        return "⭐⭐⭐ 谨慎推荐"
    elif score >= 50:
        return "⭐⭐ 观望"
    else:
        return "⭐ 回避"

def generate_recommendation(stock: Dict) -> Dict:
    """生成个股推荐建议"""
    score = stock["total_score"]
    
    if score >= 80:
        position = "20-25%"
        stop_loss = "-8%"
        take_profit = "+15-20%"
    elif score >= 70:
        position = "15-20%"
        stop_loss = "-10%"
        take_profit = "+10-15%"
    elif score >= 60:
        position = "10-15%"
        stop_loss = "-10%"
        take_profit = "+8-12%"
    elif score >= 50:
        position = "5-10%"
        stop_loss = "-12%"
        take_profit = "+5-8%"
    else:
        position = "观望"
        stop_loss = "-"
        take_profit = "-"
    
    return {
        "position": position,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
    }

# ==================== 主函数 ====================

def main():
    """主函数"""
    print("=" * 80)
    print(" " * 25 + "股票短期买入推荐系统 v2.0")
    print(" " * 28 + "（整合资金流评分）")
    print("=" * 80)
    
    # 示例数据（实际使用时从 API 或浏览器获取）
    sample_stocks = [
        {
            "code": "002475", "name": "立讯精密", "sector": "苹果链/AI",
            "price": 50.97, "price_change": 9.99, "volume_ratio": 3.14,
            "position_52w": 71, "pe_ttm": 23.49, "profit_growth": 25, "debt_ratio": 45,
            "main_net_inflow": 296900, "main_ratio": 22.76, "super_ratio": 27.70,
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
        {
            "code": "300308", "name": "中际旭创", "sector": "CPO",
            "price": 628.00, "price_change": 4.11, "volume_ratio": 1.8,
            "position_52w": 95, "pe_ttm": 81.61, "profit_growth": 80, "debt_ratio": 25,
            "main_net_inflow": 150000, "main_ratio": 8.5, "super_ratio": 6.2,
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
        {
            "code": "300394", "name": "天孚通信", "sector": "光器件",
            "price": 316.74, "price_change": 6.04, "volume_ratio": 1.5,
            "position_52w": 81, "pe_ttm": 134.38, "profit_growth": 60, "debt_ratio": 20,
            "main_net_inflow": 80000, "main_ratio": 7.2, "super_ratio": 5.1,
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
        {
            "code": "601899", "name": "紫金矿业", "sector": "有色金属",
            "price": 18.50, "price_change": 2.5, "volume_ratio": 1.2,
            "position_52w": 65, "pe_ttm": 18.5, "profit_growth": 35, "debt_ratio": 48,
            "main_net_inflow": 120000, "main_ratio": 9.5, "super_ratio": 7.8,
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
        {
            "code": "601138", "name": "工业富联", "sector": "AI 服务器",
            "price": 50.22, "price_change": 2.83, "volume_ratio": 1.08,
            "position_52w": 60, "pe_ttm": 28.26, "profit_growth": 15, "debt_ratio": 55,
            "main_net_inflow": 50000, "main_ratio": 3.8, "super_ratio": 2.5,
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
    ]
    
    # 计算综合评分
    results = []
    for stock in sample_stocks:
        result = calculate_comprehensive_score(stock)
        result["recommendation"] = generate_recommendation(result)
        results.append(result)
    
    # 按总分排序
    sorted_results = sorted(results, key=lambda x: x["total_score"], reverse=True)
    
    # 输出 TOP 5 推荐
    print("\n" + "=" * 80)
    print("📈 短期买入推荐 TOP 5")
    print("=" * 80)
    print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'总分':<6} {'资金流':<8} {'胜率':<6} {'评级':<20}")
    print("-" * 80)
    
    for i, stock in enumerate(sorted_results[:5], 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        print(f"{medal} {stock['code']:<8} {stock['name']:<10} {stock['total_score']:<6.1f} "
              f"{stock['fund_score']:<8.1f} {stock['win_probability']:<6.0f}% "
              f"{get_rating(stock['total_score'])}")
    
    # 详细分析
    print("\n" + "=" * 80)
    print("📊 详细评分分析")
    print("=" * 80)
    
    for i, stock in enumerate(sorted_results[:5], 1):
        print(f"\n【第{i}名】{stock['name']} ({stock['code']}) - 总分：{stock['total_score']:.1f}")
        print(f"  技术面：{stock['tech_score']:.1f}/25  |  资金面：{stock['fund_score']:.1f}/20  |  "
              f"题材面：{stock['theme_score']:.1f}/25")
        print(f"  基本面：{stock['fundamental_score']:.1f}/15  |  风险面：{stock['risk_score']:.1f}/15")
        print(f"  主力净流入：{stock['main_net_inflow']:,.0f}万  |  主力占比：{stock['main_ratio']:.2f}%  |  "
              f"超大单占比：{stock['super_ratio']:.2f}%")
        print(f"  💡 建议：仓位{stock['recommendation']['position']} | 止盈{stock['recommendation']['take_profit']} | "
              f"止损{stock['recommendation']['stop_loss']}")
    
    # 保存结果
    output_dir = "/home/admin/.openclaw/workspace/data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/stock_recommend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sorted_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存至：{output_file}")
    
    # 组合策略
    print("\n" + "=" * 80)
    print("💼 组合策略建议")
    print("=" * 80)
    print(f"  组合预期胜率：{(sum(s['win_probability'] for s in sorted_results[:5]) / 5):.0f}%")
    print(f"  组合预期收益：+8% ~ +15%")
    print(f"  建议持仓周期：5-15 个交易日")
    print(f"  总仓位建议：60-80%")
    print(f"  单只上限：25%")
    
    return sorted_results

if __name__ == "__main__":
    main()
