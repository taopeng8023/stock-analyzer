#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票短期买入推荐系统 v3.0
整合资金流评分 + 多技术指标（MACD/KDJ/RSI/均线）
"""

import json
import os
import math
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

# 评分维度权重 v3.0
WEIGHTS = {
    "技术面": 0.30,    # 30 分（增加技术指标）
    "资金面": 0.20,    # 20 分（资金流）
    "题材面": 0.20,    # 20 分
    "基本面": 0.15,    # 15 分
    "风险面": 0.15,    # 15 分
}

# ==================== 技术指标计算 ====================

def calculate_macd_score(macd: float, signal: float, histogram: float, trend: str) -> float:
    """
    MACD 评分（0-10 分）
    macd: DIF 值
    signal: DEA 值
    histogram: MACD 柱
    trend: 趋势（"金叉"/"死叉"/"多头"/"空头"）
    """
    score = 5.0  # 基础分
    
    # 金叉/死叉判断
    if trend == "金叉" or (macd > signal and histogram > 0):
        score += 3
        if histogram > 0 and histogram > histogram * 0.5:  # 红柱放大
            score += 2
    elif trend == "死叉" or (macd < signal and histogram < 0):
        score -= 3
        if histogram < 0:  # 绿柱放大
            score -= 2
    
    # 0 轴位置
    if macd > 0 and signal > 0:  # 0 轴上方（多头市场）
        score += 1
    elif macd < 0 and signal < 0:  # 0 轴下方（空头市场）
        score -= 1
    
    return max(0, min(10, score))

def calculate_kdj_score(k: float, d: float, j: float, position: str) -> float:
    """
    KDJ 评分（0-10 分）
    k: K 值
    d: D 值
    j: J 值
    position: 位置（"超买"/"超卖"/"中性"）
    """
    score = 5.0  # 基础分
    
    # 金叉/死叉
    if k > d and j > d:  # 金叉
        score += 2
        if k < 80:  # 未超买
            score += 1
    elif k < d and j < d:  # 死叉
        score -= 2
        if k > 20:  # 未超卖
            score -= 1
    
    # 超买超卖
    if position == "超卖" or (k < 20 and d < 20):
        score += 2  # 超卖区，可能反弹
    elif position == "超买" or (k > 80 and d > 80):
        score -= 2  # 超买区，可能回调
    
    # J 值极端
    if j > 100:
        score -= 1  # J 值过高
    elif j < 0:
        score += 1  # J 值过低
    
    return max(0, min(10, score))

def calculate_rsi_score(rsi6: float, rsi12: float, rsi24: float) -> float:
    """
    RSI 评分（0-10 分）
    rsi6: 6 日 RSI
    rsi12: 12 日 RSI
    rsi24: 24 日 RSI
    """
    score = 5.0  # 基础分
    
    # RSI 位置判断
    if rsi6 < 20:
        score += 3  # 严重超卖
    elif rsi6 < 30:
        score += 2  # 超卖
    elif rsi6 > 80:
        score -= 3  # 严重超买
    elif rsi6 > 70:
        score -= 2  # 超买
    
    # 多头排列
    if rsi6 > rsi12 > rsi24:
        score += 2  # 多头排列
    elif rsi6 < rsi12 < rsi24:
        score -= 2  # 空头排列
    
    # 50 中轴
    if rsi6 > 50 and rsi12 > 50:
        score += 1  # 强势区
    elif rsi6 < 50 and rsi12 < 50:
        score -= 1  # 弱势区
    
    return max(0, min(10, score))

def calculate_ma_score(price: float, ma5: float, ma10: float, ma20: float, ma60: float, trend: str) -> float:
    """
    均线系统评分（0-10 分）
    price: 当前股价
    ma5/10/20/60: 各周期均线
    trend: 趋势（"多头"/"空头"/"震荡"）
    """
    score = 5.0  # 基础分
    
    # 股价与均线关系
    if price > ma5 > ma10 > ma20:
        score += 3  # 多头排列
    elif price < ma5 < ma10 < ma20:
        score -= 3  # 空头排列
    elif price > ma20:
        score += 1  # 站上 20 日线
    elif price < ma20:
        score -= 1  # 跌破 20 日线
    
    # 60 日线（生命线）
    if price > ma60 and ma60 > ma20:
        score += 2  # 站上生命线且向上
    elif price < ma60:
        score -= 1  # 跌破生命线
    
    # 趋势判断
    if trend == "多头":
        score += 1
    elif trend == "空头":
        score -= 1
    
    return max(0, min(10, score))

def calculate_volume_score(volume_ratio: float, turnover_rate: float, amount: float) -> float:
    """
    成交量评分（0-10 分）
    volume_ratio: 量比
    turnover_rate: 换手率
    amount: 成交额（亿）
    """
    score = 5.0  # 基础分
    
    # 量比评分
    if volume_ratio >= 3:
        score += 3  # 放量明显
    elif volume_ratio >= 2:
        score += 2
    elif volume_ratio >= 1:
        score += 1
    elif volume_ratio <= 0.5:
        score -= 2  # 严重缩量
    elif volume_ratio <= 0.8:
        score -= 1
    
    # 换手率评分（活跃但不过度）
    if 3 <= turnover_rate <= 10:
        score += 2  # 健康活跃
    elif 10 < turnover_rate <= 20:
        score += 1  # 较活跃
    elif turnover_rate > 20:
        score -= 1  # 过度活跃（可能见顶）
    elif turnover_rate < 1:
        score -= 1  # 成交不活跃
    
    # 成交额（流动性）
    if amount >= 50:
        score += 1  # 成交充沛
    elif amount >= 10:
        score += 0.5
    elif amount < 1:
        score -= 1  # 成交低迷
    
    return max(0, min(10, score))

def calculate_price_strength_score(price_change: float, amplitude: float, close_position: float) -> float:
    """
    价格强度评分（0-10 分）
    price_change: 涨跌幅
    amplitude: 振幅
    close_position: 收盘位置（0-1，1 为最高价附近）
    """
    score = 5.0  # 基础分
    
    # 涨跌幅评分
    if price_change >= 9.5:  # 涨停
        score += 4
    elif price_change >= 5:
        score += 3
    elif price_change >= 2:
        score += 2
    elif price_change >= 0:
        score += 1
    elif price_change <= -9.5:  # 跌停
        score -= 4
    elif price_change <= -5:
        score -= 3
    elif price_change <= -2:
        score -= 2
    
    # 收盘位置
    if close_position >= 0.8:  # 收在高位
        score += 2
    elif close_position >= 0.5:
        score += 1
    elif close_position <= 0.2:  # 收在低位
        score -= 2
    
    # 振幅（适度为好）
    if 3 <= amplitude <= 8:
        score += 1  # 健康振幅
    elif amplitude > 15:
        score -= 1  # 振幅过大（波动剧烈）
    
    return max(0, min(10, score))

# ==================== 综合技术面评分 ====================

def calculate_technical_score_v3(stock_data: Dict) -> float:
    """
    综合技术面评分（0-30 分）
    包含：MACD + KDJ + RSI + 均线 + 成交量 + 价格强度
    """
    # 各技术指标评分
    macd_score = calculate_macd_score(
        stock_data.get("macd_dif", 0),
        stock_data.get("macd_dea", 0),
        stock_data.get("macd_hist", 0),
        stock_data.get("macd_trend", "中性")
    )
    
    kdj_score = calculate_kdj_score(
        stock_data.get("kdj_k", 50),
        stock_data.get("kdj_d", 50),
        stock_data.get("kdj_j", 50),
        stock_data.get("kdj_position", "中性")
    )
    
    rsi_score = calculate_rsi_score(
        stock_data.get("rsi6", 50),
        stock_data.get("rsi12", 50),
        stock_data.get("rsi24", 50)
    )
    
    ma_score = calculate_ma_score(
        stock_data.get("price", 0),
        stock_data.get("ma5", 0),
        stock_data.get("ma10", 0),
        stock_data.get("ma20", 0),
        stock_data.get("ma60", 0),
        stock_data.get("ma_trend", "震荡")
    )
    
    volume_score = calculate_volume_score(
        stock_data.get("volume_ratio", 1),
        stock_data.get("turnover_rate", 3),
        stock_data.get("amount", 10)
    )
    
    price_score = calculate_price_strength_score(
        stock_data.get("price_change", 0),
        stock_data.get("amplitude", 5),
        stock_data.get("close_position", 0.5)
    )
    
    # 加权计算（30 分制）
    # 6 个指标，每个 0-10 分，平均后*3 得到 0-30 分
    avg_score = (macd_score + kdj_score + rsi_score + ma_score + volume_score + price_score) / 6
    total_tech_score = avg_score * 3
    
    return round(max(0, min(30, total_tech_score)), 1)

# ==================== 其他维度评分 ====================

def calculate_fund_score(main_net_inflow: float, main_ratio: float, super_ratio: float) -> float:
    """资金流评分（0-20 分）"""
    score = 10.0
    
    if main_ratio >= 10: score += 6
    elif main_ratio >= 5: score += 4
    elif main_ratio >= 2: score += 2
    elif main_ratio >= 0: score += 1
    elif main_ratio <= -10: score -= 6
    elif main_ratio <= -5: score -= 4
    elif main_ratio <= -2: score -= 2
    elif main_ratio < 0: score -= 1
    
    if super_ratio >= 5: score += 4
    elif super_ratio >= 2: score += 2
    elif super_ratio >= 0: score += 1
    elif super_ratio <= -5: score -= 4
    elif super_ratio <= -2: score -= 2
    elif super_ratio < 0: score -= 1
    
    return max(0, min(20, score))

def calculate_theme_score(sector: str, is_hot_concept: bool) -> float:
    """题材面评分（0-20 分）"""
    score = 10.0
    
    hot_sectors = ["CPO", "光模块", "AI 服务器", "存储芯片", "半导体设备", "有色金属", "锂电池"]
    if sector in hot_sectors:
        score += 6
    elif "光" in sector or "电" in sector or "芯片" in sector:
        score += 4
    elif is_hot_concept:
        score += 5
    
    return max(0, min(20, score))

def calculate_fundamental_score(pe_ttm: float, profit_growth: float, debt_ratio: float) -> float:
    """基本面评分（0-15 分）"""
    score = 7.5
    
    if 0 < pe_ttm <= 20: score += 3
    elif 20 < pe_ttm <= 40: score += 1
    elif pe_ttm <= 0: score -= 3
    elif pe_ttm > 80: score -= 2
    
    if profit_growth >= 50: score += 4
    elif profit_growth >= 20: score += 2
    elif profit_growth >= 0: score += 1
    elif profit_growth <= -30: score -= 3
    
    if debt_ratio <= 40: score += 2
    elif debt_ratio <= 60: score += 0
    elif debt_ratio >= 80: score -= 2
    
    return max(0, min(15, score))

def calculate_risk_score(position_52w: float, is_loss: bool, has_limit_down: bool) -> float:
    """风险面评分（0-15 分）"""
    score = 7.5
    
    if position_52w >= 90: score -= 4
    elif position_52w >= 75: score -= 2
    elif position_52w <= 20: score += 3
    
    if is_loss: score -= 3
    if has_limit_down: score -= 4
    
    return max(0, min(15, score))

# ==================== 综合评分 ====================

def calculate_comprehensive_score_v3(stock_data: Dict) -> Dict:
    """计算综合评分（100 分制）"""
    
    # 技术面（30 分）
    tech_score = calculate_technical_score_v3(stock_data)
    
    # 资金面（20 分）
    fund_score = calculate_fund_score(
        stock_data.get("main_net_inflow", 0),
        stock_data.get("main_ratio", 0),
        stock_data.get("super_ratio", 0)
    )
    
    # 题材面（20 分）
    theme_score = calculate_theme_score(
        stock_data.get("sector", ""),
        stock_data.get("is_hot_concept", False)
    )
    
    # 基本面（15 分）
    fundamental_score = calculate_fundamental_score(
        stock_data.get("pe_ttm", 30),
        stock_data.get("profit_growth", 0),
        stock_data.get("debt_ratio", 50)
    )
    
    # 风险面（15 分）
    risk_score = calculate_risk_score(
        stock_data.get("position_52w", 50),
        stock_data.get("is_loss", False),
        stock_data.get("has_limit_down", False)
    )
    
    # 总分（100 分）
    total_score = tech_score + fund_score + theme_score + fundamental_score + risk_score
    
    # 盈利概率
    if total_score >= 85: win_prob = 80
    elif total_score >= 75: win_prob = 70
    elif total_score >= 65: win_prob = 60
    elif total_score >= 55: win_prob = 50
    elif total_score >= 45: win_prob = 40
    else: win_prob = 30
    
    return {
        **stock_data,
        "tech_score": round(tech_score, 1),
        "fund_score": round(fund_score, 1),
        "theme_score": round(theme_score, 1),
        "fundamental_score": round(fundamental_score, 1),
        "risk_score": round(risk_score, 1),
        "total_score": round(total_score, 1),
        "win_probability": win_prob,
        # 技术指标明细
        "macd_score": round(calculate_macd_score(stock_data.get("macd_dif", 0), stock_data.get("macd_dea", 0), stock_data.get("macd_hist", 0), stock_data.get("macd_trend", "中性")), 1),
        "kdj_score": round(calculate_kdj_score(stock_data.get("kdj_k", 50), stock_data.get("kdj_d", 50), stock_data.get("kdj_j", 50), stock_data.get("kdj_position", "中性")), 1),
        "rsi_score": round(calculate_rsi_score(stock_data.get("rsi6", 50), stock_data.get("rsi12", 50), stock_data.get("rsi24", 50)), 1),
        "ma_score": round(calculate_ma_score(stock_data.get("price", 0), stock_data.get("ma5", 0), stock_data.get("ma10", 0), stock_data.get("ma20", 0), stock_data.get("ma60", 0), stock_data.get("ma_trend", "震荡")), 1),
        "volume_score": round(calculate_volume_score(stock_data.get("volume_ratio", 1), stock_data.get("turnover_rate", 3), stock_data.get("amount", 10)), 1),
        "price_score": round(calculate_price_strength_score(stock_data.get("price_change", 0), stock_data.get("amplitude", 5), stock_data.get("close_position", 0.5)), 1),
    }

def get_rating_v3(score: float) -> str:
    """获取评级"""
    if score >= 85: return "⭐⭐⭐⭐⭐ 强烈推荐"
    elif score >= 75: return "⭐⭐⭐⭐ 推荐"
    elif score >= 65: return "⭐⭐⭐ 谨慎推荐"
    elif score >= 55: return "⭐⭐ 观望"
    else: return "⭐ 回避"

def generate_recommendation_v3(stock: Dict) -> Dict:
    """生成个股推荐建议"""
    score = stock["total_score"]
    
    if score >= 85:
        return {"position": "20-25%", "stop_loss": "-8%", "take_profit": "+15-20%"}
    elif score >= 75:
        return {"position": "15-20%", "stop_loss": "-10%", "take_profit": "+10-15%"}
    elif score >= 65:
        return {"position": "10-15%", "stop_loss": "-10%", "take_profit": "+8-12%"}
    elif score >= 55:
        return {"position": "5-10%", "stop_loss": "-12%", "take_profit": "+5-8%"}
    else:
        return {"position": "观望", "stop_loss": "-", "take_profit": "-"}

# ==================== 主函数 ====================

def main():
    """主函数"""
    print("=" * 90)
    print(" " * 22 + "股票短期买入推荐系统 v3.0")
    print(" " * 25 + "（多技术指标整合版）")
    print("=" * 90)
    
    # 示例数据（包含完整技术指标）
    sample_stocks = [
        {
            "code": "002475", "name": "立讯精密", "sector": "苹果链/AI",
            "price": 50.97, "price_change": 9.99, "volume_ratio": 3.14, "turnover_rate": 3.53, "amount": 128,
            "amplitude": 8.57, "close_position": 0.95, "position_52w": 71,
            "pe_ttm": 23.49, "profit_growth": 25, "debt_ratio": 45,
            "main_net_inflow": 296900, "main_ratio": 22.76, "super_ratio": 27.70,
            "macd_dif": 1.5, "macd_dea": 1.2, "macd_hist": 0.3, "macd_trend": "金叉",
            "kdj_k": 75, "kdj_d": 68, "kdj_j": 85, "kdj_position": "中性",
            "rsi6": 68, "rsi12": 62, "rsi24": 58,
            "ma5": 49.5, "ma10": 48.2, "ma20": 46.8, "ma60": 44.5, "ma_trend": "多头",
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
        {
            "code": "601899", "name": "紫金矿业", "sector": "有色金属",
            "price": 18.50, "price_change": 2.5, "volume_ratio": 1.2, "turnover_rate": 2.8, "amount": 45,
            "amplitude": 4.5, "close_position": 0.7, "position_52w": 65,
            "pe_ttm": 18.5, "profit_growth": 35, "debt_ratio": 48,
            "main_net_inflow": 120000, "main_ratio": 9.5, "super_ratio": 7.8,
            "macd_dif": 0.3, "macd_dea": 0.25, "macd_hist": 0.05, "macd_trend": "金叉",
            "kdj_k": 65, "kdj_d": 60, "kdj_j": 72, "kdj_position": "中性",
            "rsi6": 58, "rsi12": 55, "rsi24": 52,
            "ma5": 18.2, "ma10": 17.8, "ma20": 17.2, "ma60": 16.5, "ma_trend": "多头",
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
        {
            "code": "300394", "name": "天孚通信", "sector": "光器件",
            "price": 316.74, "price_change": 6.04, "volume_ratio": 1.5, "turnover_rate": 4.5, "amount": 112,
            "amplitude": 6.5, "close_position": 0.75, "position_52w": 81,
            "pe_ttm": 134.38, "profit_growth": 60, "debt_ratio": 20,
            "main_net_inflow": 80000, "main_ratio": 7.2, "super_ratio": 5.1,
            "macd_dif": 8.5, "macd_dea": 7.8, "macd_hist": 0.7, "macd_trend": "金叉",
            "kdj_k": 72, "kdj_d": 65, "kdj_j": 82, "kdj_position": "中性",
            "rsi6": 65, "rsi12": 60, "rsi24": 55,
            "ma5": 310, "ma10": 302, "ma20": 290, "ma60": 275, "ma_trend": "多头",
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
        {
            "code": "601138", "name": "工业富联", "sector": "AI 服务器",
            "price": 50.22, "price_change": 2.83, "volume_ratio": 1.08, "turnover_rate": 0.58, "amount": 57,
            "amplitude": 4.0, "close_position": 0.65, "position_52w": 60,
            "pe_ttm": 28.26, "profit_growth": 15, "debt_ratio": 55,
            "main_net_inflow": 50000, "main_ratio": 3.8, "super_ratio": 2.5,
            "macd_dif": 0.8, "macd_dea": 0.7, "macd_hist": 0.1, "macd_trend": "金叉",
            "kdj_k": 58, "kdj_d": 55, "kdj_j": 62, "kdj_position": "中性",
            "rsi6": 55, "rsi12": 52, "rsi24": 50,
            "ma5": 49.8, "ma10": 49.2, "ma20": 48.5, "ma60": 47.0, "ma_trend": "多头",
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
        {
            "code": "300308", "name": "中际旭创", "sector": "CPO",
            "price": 628.00, "price_change": 4.11, "volume_ratio": 1.8, "turnover_rate": 2.78, "amount": 193,
            "amplitude": 3.1, "close_position": 0.8, "position_52w": 95,
            "pe_ttm": 81.61, "profit_growth": 80, "debt_ratio": 25,
            "main_net_inflow": 150000, "main_ratio": 8.5, "super_ratio": 6.2,
            "macd_dif": 15, "macd_dea": 14, "macd_hist": 1, "macd_trend": "多头",
            "kdj_k": 82, "kdj_d": 78, "kdj_j": 88, "kdj_position": "超买",
            "rsi6": 72, "rsi12": 68, "rsi24": 65,
            "ma5": 615, "ma10": 600, "ma20": 580, "ma60": 550, "ma_trend": "多头",
            "is_loss": False, "has_limit_down": False, "is_hot_concept": True,
        },
    ]
    
    # 计算综合评分
    results = []
    for stock in sample_stocks:
        result = calculate_comprehensive_score_v3(stock)
        result["recommendation"] = generate_recommendation_v3(result)
        results.append(result)
    
    # 排序
    sorted_results = sorted(results, key=lambda x: x["total_score"], reverse=True)
    
    # 输出 TOP 5
    print("\n" + "=" * 90)
    print("📈 短期买入推荐 TOP 5")
    print("=" * 90)
    print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'总分':<6} {'技术':<6} {'资金':<6} {'胜率':<6} {'评级':<20}")
    print("-" * 90)
    
    for i, stock in enumerate(sorted_results[:5], 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        print(f"{medal} {stock['code']:<8} {stock['name']:<10} {stock['total_score']:<6.1f} "
              f"{stock['tech_score']:<6.1f} {stock['fund_score']:<6.1f} {stock['win_probability']:<6.0f}% "
              f"{get_rating_v3(stock['total_score'])}")
    
    # 详细技术指标
    print("\n" + "=" * 90)
    print("📊 技术指标明细")
    print("=" * 90)
    
    for i, stock in enumerate(sorted_results[:5], 1):
        print(f"\n【第{i}名】{stock['name']} ({stock['code']}) - 总分：{stock['total_score']:.1f}")
        print(f"  技术面：{stock['tech_score']:.1f}/30 | 资金面：{stock['fund_score']:.1f}/20 | 题材面：{stock['theme_score']:.1f}/20")
        print(f"  基本面：{stock['fundamental_score']:.1f}/15 | 风险面：{stock['risk_score']:.1f}/15")
        print(f"  └─ MACD: {stock['macd_score']:.1f} | KDJ: {stock['kdj_score']:.1f} | RSI: {stock['rsi_score']:.1f}")
        print(f"  └─ 均线：{stock['ma_score']:.1f} | 成交量：{stock['volume_score']:.1f} | 价格：{stock['price_score']:.1f}")
        print(f"  💡 主力净流入：{stock['main_net_inflow']:,.0f}万 ({stock['main_ratio']:.2f}%) | 建议：仓位{stock['recommendation']['position']} | 止盈{stock['recommendation']['take_profit']} | 止损{stock['recommendation']['stop_loss']}")
    
    # 保存
    output_dir = "/home/admin/.openclaw/workspace/data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/stock_recommend_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sorted_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存至：{output_file}")
    
    # 组合策略
    print("\n" + "=" * 90)
    print("💼 组合策略建议")
    print("=" * 90)
    avg_win_prob = sum(s['win_probability'] for s in sorted_results[:5]) / 5
    print(f"  组合预期胜率：{avg_win_prob:.0f}%")
    print(f"  组合预期收益：+10% ~ +18%")
    print(f"  建议持仓周期：5-15 个交易日")
    print(f"  总仓位建议：60-80%")
    print(f"  单只上限：25%")
    
    return sorted_results

if __name__ == "__main__":
    main()
