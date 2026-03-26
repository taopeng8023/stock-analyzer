#!/usr/bin/env python3
"""
深度基本面分析模型
基于财务指标、行业对比、估值分析的综合评估系统

⚠️  仅用于研究学习，不构成投资建议

分析维度:
1. 估值分析 (PE/PB/PS/PEG)
2. 盈利能力 (ROE/ROA/毛利率/净利率)
3. 成长能力 (营收增长/利润增长/现金流增长)
4. 偿债能力 (负债率/流动比率/速动比率)
5. 运营能力 (周转率/收现率)
6. 现金流分析 (经营现金流/自由现金流)
7. 行业对比 (相对估值/行业地位)
8. 股东分析 (机构持股/高管增持)

用法:
    python3 fundamental_analysis.py --stock 600000.SH  # 分析单只股票
    python3 fundamental_analysis.py --compare          # 行业对比
    python3 fundamental_analysis.py --all              # 全部分析
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ============ 基本面数据库（示例数据） ============

FUNDAMENTAL_DB = {
    '600000.SH': {  # 浦发银行
        'name': '浦发银行',
        'sector': '银行',
        'industry': '股份制银行',
        'market_cap': 2150,  # 亿
        'pe_ttm': 5.2,
        'pb': 0.55,
        'ps': 1.8,
        'peg': 0.65,
        'roe': 11.2,
        'roa': 0.95,
        'gross_margin': 35.5,
        'net_margin': 28.2,
        'revenue_growth': 8.5,
        'profit_growth': 10.2,
        'cash_flow_growth': 12.5,
        'debt_ratio': 85.2,  # 银行特殊
        'current_ratio': 1.05,
        'quick_ratio': 0.98,
        'asset_turnover': 0.035,
        'inventory_turnover': None,  # 银行不适用
        'receivables_turnover': None,
        'operating_cash_flow': 1250,  # 亿
        'free_cash_flow': 980,  # 亿
        'dividend_yield': 4.5,
        'institutional_holding': 65.2,
        'insider_trading': '增持',
        'analyst_rating': 4.2,  # 5 分制
        'target_price': 12.5,
    },
    '000001.SZ': {  # 平安银行
        'name': '平安银行',
        'sector': '银行',
        'industry': '股份制银行',
        'market_cap': 2080,
        'pe_ttm': 5.5,
        'pb': 0.58,
        'ps': 1.9,
        'peg': 0.55,
        'roe': 11.8,
        'roa': 0.98,
        'gross_margin': 36.2,
        'net_margin': 29.5,
        'revenue_growth': 9.2,
        'profit_growth': 12.5,
        'cash_flow_growth': 15.2,
        'debt_ratio': 84.8,
        'current_ratio': 1.08,
        'quick_ratio': 1.02,
        'asset_turnover': 0.038,
        'inventory_turnover': None,
        'receivables_turnover': None,
        'operating_cash_flow': 1380,
        'free_cash_flow': 1050,
        'dividend_yield': 4.2,
        'institutional_holding': 68.5,
        'insider_trading': '增持',
        'analyst_rating': 4.5,
        'target_price': 13.2,
    },
    '000100.SZ': {  # TCL 科技
        'name': 'TCL 科技',
        'sector': '科技',
        'industry': '显示面板',
        'market_cap': 650,
        'pe_ttm': 18,
        'pb': 1.8,
        'ps': 1.2,
        'peg': 0.72,
        'roe': 12.5,
        'roa': 5.8,
        'gross_margin': 18.5,
        'net_margin': 8.2,
        'revenue_growth': 22.5,
        'profit_growth': 28.5,
        'cash_flow_growth': 25.2,
        'debt_ratio': 52.5,
        'current_ratio': 1.35,
        'quick_ratio': 1.05,
        'asset_turnover': 0.72,
        'inventory_turnover': 6.5,
        'receivables_turnover': 8.2,
        'operating_cash_flow': 280,
        'free_cash_flow': 150,
        'dividend_yield': 1.2,
        'institutional_holding': 45.8,
        'insider_trading': '中性',
        'analyst_rating': 4.0,
        'target_price': 5.2,
    },
    '600256.SH': {  # 广汇能源
        'name': '广汇能源',
        'sector': '能源',
        'industry': '石油天然气',
        'market_cap': 580,
        'pe_ttm': 8,
        'pb': 1.2,
        'ps': 1.5,
        'peg': 0.25,
        'roe': 15.2,
        'roa': 8.5,
        'gross_margin': 32.5,
        'net_margin': 18.5,
        'revenue_growth': 28.5,
        'profit_growth': 35.2,
        'cash_flow_growth': 42.5,
        'debt_ratio': 45.2,
        'current_ratio': 1.55,
        'quick_ratio': 1.25,
        'asset_turnover': 0.48,
        'inventory_turnover': 12.5,
        'receivables_turnover': 15.2,
        'operating_cash_flow': 320,
        'free_cash_flow': 220,
        'dividend_yield': 6.5,
        'institutional_holding': 52.5,
        'insider_trading': '增持',
        'analyst_rating': 4.3,
        'target_price': 8.5,
    },
}

# 行业平均数据
INDUSTRY_AVERAGE = {
    '银行': {
        'pe': 6.5, 'pb': 0.65, 'roe': 10.5, 'debt_ratio': 86,
        'revenue_growth': 7, 'profit_growth': 8, 'dividend_yield': 4.0
    },
    '科技': {
        'pe': 28, 'pb': 3.5, 'roe': 11, 'debt_ratio': 45,
        'revenue_growth': 20, 'profit_growth': 25, 'dividend_yield': 1.0
    },
    '能源': {
        'pe': 10, 'pb': 1.3, 'roe': 13, 'debt_ratio': 48,
        'revenue_growth': 18, 'profit_growth': 22, 'dividend_yield': 4.5
    },
    '农业': {
        'pe': 30, 'pb': 2.0, 'roe': 8, 'debt_ratio': 42,
        'revenue_growth': 12, 'profit_growth': 15, 'dividend_yield': 1.5
    },
    '医药': {
        'pe': 25, 'pb': 3.0, 'roe': 12, 'debt_ratio': 35,
        'revenue_growth': 18, 'profit_growth': 20, 'dividend_yield': 1.8
    },
}


# ============ 估值分析模型 ============

def analyze_valuation(stock_data: dict) -> dict:
    """
    估值分析
    
    分析指标:
    1. PE (市盈率) - 相对行业
    2. PB (市净率) - 相对行业
    3. PS (市销率) - 相对行业
    4. PEG (市盈率相对盈利增长比率)
    5. 股息率
    """
    
    sector = stock_data.get('sector', '一般')
    industry_avg = INDUSTRY_AVERAGE.get(sector, INDUSTRY_AVERAGE['科技'])
    
    # 1. PE 分析 (25 分)
    pe = stock_data.get('pe_ttm', 20)
    industry_pe = industry_avg['pe']
    pe_ratio = pe / industry_pe if industry_pe > 0 else 1
    
    if pe_ratio < 0.5:
        pe_score = 25  # 显著低估
    elif pe_ratio < 0.8:
        pe_score = 20  # 低估
    elif pe_ratio < 1.2:
        pe_score = 15  # 合理
    elif pe_ratio < 1.5:
        pe_score = 10  # 高估
    else:
        pe_score = 5   # 显著高估
    
    # 2. PB 分析 (20 分)
    pb = stock_data.get('pb', 1.5)
    industry_pb = industry_avg['pb']
    pb_ratio = pb / industry_pb if industry_pb > 0 else 1
    
    if pb_ratio < 0.5:
        pb_score = 20
    elif pb_ratio < 0.8:
        pb_score = 16
    elif pb_ratio < 1.2:
        pb_score = 12
    elif pb_ratio < 1.5:
        pb_score = 8
    else:
        pb_score = 4
    
    # 3. PEG 分析 (25 分)
    peg = stock_data.get('peg', 1.0)
    if peg < 0.5:
        peg_score = 25  # 极具投资价值
    elif peg < 0.8:
        peg_score = 20  # 有投资价值
    elif peg < 1.2:
        peg_score = 15  # 合理
    elif peg < 1.5:
        peg_score = 10  # 偏高
    else:
        peg_score = 5   # 过高
    
    # 4. PS 分析 (15 分)
    ps = stock_data.get('ps', 2.0)
    if ps < 1:
        ps_score = 15
    elif ps < 2:
        ps_score = 12
    elif ps < 3:
        ps_score = 9
    elif ps < 5:
        ps_score = 6
    else:
        ps_score = 3
    
    # 5. 股息率分析 (15 分)
    dividend = stock_data.get('dividend_yield', 1.0)
    industry_dividend = industry_avg['dividend_yield']
    
    if dividend > industry_dividend * 1.5:
        dividend_score = 15
    elif dividend > industry_dividend:
        dividend_score = 12
    elif dividend > industry_dividend * 0.8:
        dividend_score = 9
    elif dividend > industry_dividend * 0.5:
        dividend_score = 6
    else:
        dividend_score = 3
    
    # 总分
    total_score = pe_score + pb_score + peg_score + ps_score + dividend_score
    
    # 估值评级
    if total_score >= 90:
        rating = '极度低估'
        level = '⭐⭐⭐⭐⭐'
    elif total_score >= 75:
        rating = '低估'
        level = '⭐⭐⭐⭐'
    elif total_score >= 60:
        rating = '合理'
        level = '⭐⭐⭐'
    elif total_score >= 45:
        rating = '高估'
        level = '⭐⭐'
    else:
        rating = '严重高估'
        level = '⭐'
    
    return {
        'total_score': total_score,
        'rating': rating,
        'level': level,
        'pe_score': pe_score,
        'pb_score': pb_score,
        'peg_score': peg_score,
        'ps_score': ps_score,
        'dividend_score': dividend_score,
        'pe': pe,
        'pb': pb,
        'peg': peg,
        'ps': ps,
        'dividend_yield': dividend,
        'pe_vs_industry': f"{pe_ratio:.2f}x",
        'pb_vs_industry': f"{pb_ratio:.2f}x",
    }


# ============ 盈利能力分析模型 ============

def analyze_profitability(stock_data: dict) -> dict:
    """
    盈利能力分析
    
    分析指标:
    1. ROE (净资产收益率)
    2. ROA (总资产收益率)
    3. 毛利率
    4. 净利率
    5. 盈利质量
    """
    
    sector = stock_data.get('sector', '一般')
    industry_avg = INDUSTRY_AVERAGE.get(sector, INDUSTRY_AVERAGE['科技'])
    
    # 1. ROE 分析 (30 分)
    roe = stock_data.get('roe', 10)
    industry_roe = industry_avg['roe']
    
    if roe > 20:
        roe_score = 30
    elif roe > 15:
        roe_score = 25
    elif roe > industry_roe * 1.2:
        roe_score = 20
    elif roe > industry_roe:
        roe_score = 15
    elif roe > industry_roe * 0.8:
        roe_score = 10
    else:
        roe_score = 5
    
    # 2. ROA 分析 (20 分)
    roa = stock_data.get('roa', 5)
    if roa > 10:
        roa_score = 20
    elif roa > 7:
        roa_score = 16
    elif roa > 5:
        roa_score = 12
    elif roa > 3:
        roa_score = 8
    else:
        roa_score = 4
    
    # 3. 毛利率分析 (20 分)
    gross_margin = stock_data.get('gross_margin', 20)
    if gross_margin > 50:
        gross_score = 20
    elif gross_margin > 30:
        gross_score = 16
    elif gross_margin > 20:
        gross_score = 12
    elif gross_margin > 10:
        gross_score = 8
    else:
        gross_score = 4
    
    # 4. 净利率分析 (20 分)
    net_margin = stock_data.get('net_margin', 10)
    if net_margin > 25:
        net_score = 20
    elif net_margin > 15:
        net_score = 16
    elif net_margin > 10:
        net_score = 12
    elif net_margin > 5:
        net_score = 8
    else:
        net_score = 4
    
    # 5. 盈利稳定性 (10 分)
    # 简化：假设连续增长为稳定
    profit_growth = stock_data.get('profit_growth', 10)
    if profit_growth > 20:
        stability_score = 10
    elif profit_growth > 10:
        stability_score = 8
    elif profit_growth > 0:
        stability_score = 6
    else:
        stability_score = 3
    
    # 总分
    total_score = roe_score + roa_score + gross_score + net_score + stability_score
    
    # 盈利能力评级
    if total_score >= 90:
        rating = '极强'
        level = '⭐⭐⭐⭐⭐'
    elif total_score >= 75:
        rating = '强'
        level = '⭐⭐⭐⭐'
    elif total_score >= 60:
        rating = '中等'
        level = '⭐⭐⭐'
    elif total_score >= 45:
        rating = '较弱'
        level = '⭐⭐'
    else:
        rating = '弱'
        level = '⭐'
    
    return {
        'total_score': total_score,
        'rating': rating,
        'level': level,
        'roe_score': roe_score,
        'roa_score': roa_score,
        'gross_score': gross_score,
        'net_score': net_score,
        'stability_score': stability_score,
        'roe': roe,
        'roa': roa,
        'gross_margin': gross_margin,
        'net_margin': net_margin,
        'profit_growth': profit_growth,
    }


# ============ 成长能力分析模型 ============

def analyze_growth(stock_data: dict) -> dict:
    """
    成长能力分析
    
    分析指标:
    1. 营收增长率
    2. 利润增长率
    3. 现金流增长率
    4. 成长稳定性
    5. 成长可持续性
    """
    
    sector = stock_data.get('sector', '一般')
    industry_avg = INDUSTRY_AVERAGE.get(sector, INDUSTRY_AVERAGE['科技'])
    
    # 1. 营收增长 (25 分)
    revenue_growth = stock_data.get('revenue_growth', 10)
    industry_growth = industry_avg['revenue_growth']
    
    if revenue_growth > 50:
        revenue_score = 25
    elif revenue_growth > 30:
        revenue_score = 22
    elif revenue_growth > industry_growth * 1.5:
        revenue_score = 18
    elif revenue_growth > industry_growth:
        revenue_score = 14
    elif revenue_growth > 0:
        revenue_score = 10
    else:
        revenue_score = 5
    
    # 2. 利润增长 (25 分)
    profit_growth = stock_data.get('profit_growth', 10)
    industry_profit_growth = industry_avg['profit_growth']
    
    if profit_growth > 50:
        profit_score = 25
    elif profit_growth > 30:
        profit_score = 22
    elif profit_growth > industry_profit_growth * 1.5:
        profit_score = 18
    elif profit_growth > industry_profit_growth:
        profit_score = 14
    elif profit_growth > 0:
        profit_score = 10
    else:
        profit_score = 5
    
    # 3. 现金流增长 (20 分)
    cash_flow_growth = stock_data.get('cash_flow_growth', 10)
    if cash_flow_growth > 40:
        cash_score = 20
    elif cash_flow_growth > 25:
        cash_score = 16
    elif cash_flow_growth > 15:
        cash_score = 12
    elif cash_flow_growth > 0:
        cash_score = 8
    else:
        cash_score = 4
    
    # 4. 成长稳定性 (15 分)
    # 简化：营收和利润增长都为正且匹配
    if revenue_growth > 0 and profit_growth > 0:
        if abs(revenue_growth - profit_growth) < 10:
            stability_score = 15
        else:
            stability_score = 10
    else:
        stability_score = 5
    
    # 5. 成长可持续性 (15 分)
    # 简化：基于现金流增长和利润增长匹配度
    if cash_flow_growth > 0 and profit_growth > 0:
        if cash_flow_growth >= profit_growth * 0.8:
            sustainability_score = 15
        else:
            sustainability_score = 10
    else:
        sustainability_score = 5
    
    # 总分
    total_score = revenue_score + profit_score + cash_score + stability_score + sustainability_score
    
    # 成长能力评级
    if total_score >= 90:
        rating = '极高成长'
        level = '⭐⭐⭐⭐⭐'
    elif total_score >= 75:
        rating = '高成长'
        level = '⭐⭐⭐⭐'
    elif total_score >= 60:
        rating = '中等成长'
        level = '⭐⭐⭐'
    elif total_score >= 45:
        rating = '低成长'
        level = '⭐⭐'
    else:
        rating = '负成长'
        level = '⭐'
    
    return {
        'total_score': total_score,
        'rating': rating,
        'level': level,
        'revenue_score': revenue_score,
        'profit_score': profit_score,
        'cash_score': cash_score,
        'stability_score': stability_score,
        'sustainability_score': sustainability_score,
        'revenue_growth': revenue_growth,
        'profit_growth': profit_growth,
        'cash_flow_growth': cash_flow_growth,
    }


# ============ 偿债能力分析模型 ============

def analyze_solvency(stock_data: dict) -> dict:
    """
    偿债能力分析
    
    分析指标:
    1. 资产负债率
    2. 流动比率
    3. 速动比率
    4. 利息保障倍数
    """
    
    sector = stock_data.get('sector', '一般')
    
    # 银行特殊处理
    if sector == '银行':
        debt_ratio = stock_data.get('debt_ratio', 85)
        # 银行负债率高是正常的
        if debt_ratio < 88:
            debt_score = 25
        elif debt_ratio < 90:
            debt_score = 20
        elif debt_ratio < 92:
            debt_score = 15
        else:
            debt_score = 10
        
        current_ratio = stock_data.get('current_ratio', 1.0)
        if current_ratio > 1.1:
            liquidity_score = 25
        elif current_ratio > 1.0:
            liquidity_score = 20
        elif current_ratio > 0.9:
            liquidity_score = 15
        else:
            liquidity_score = 10
    else:
        # 非银行企业
        debt_ratio = stock_data.get('debt_ratio', 50)
        if debt_ratio < 30:
            debt_score = 25
        elif debt_ratio < 50:
            debt_score = 20
        elif debt_ratio < 60:
            debt_score = 15
        elif debt_ratio < 70:
            debt_score = 10
        else:
            debt_score = 5
        
        current_ratio = stock_data.get('current_ratio', 1.5)
        quick_ratio = stock_data.get('quick_ratio', 1.2)
        
        if current_ratio > 2 and quick_ratio > 1.5:
            liquidity_score = 25
        elif current_ratio > 1.5 and quick_ratio > 1:
            liquidity_score = 20
        elif current_ratio > 1.2 and quick_ratio > 0.8:
            liquidity_score = 15
        elif current_ratio > 1:
            liquidity_score = 10
        else:
            liquidity_score = 5
    
    # 总分
    total_score = debt_score + liquidity_score
    
    # 偿债能力评级
    if total_score >= 45:
        rating = '极强'
        level = '⭐⭐⭐⭐⭐'
    elif total_score >= 35:
        rating = '强'
        level = '⭐⭐⭐⭐'
    elif total_score >= 25:
        rating = '中等'
        level = '⭐⭐⭐'
    elif total_score >= 15:
        rating = '较弱'
        level = '⭐⭐'
    else:
        rating = '弱'
        level = '⭐'
    
    return {
        'total_score': total_score,
        'rating': rating,
        'level': level,
        'debt_score': debt_score,
        'liquidity_score': liquidity_score,
        'debt_ratio': debt_ratio,
        'current_ratio': current_ratio,
        'quick_ratio': stock_data.get('quick_ratio', 0),
    }


# ============ 现金流分析模型 ============

def analyze_cash_flow(stock_data: dict) -> dict:
    """
    现金流分析
    
    分析指标:
    1. 经营现金流
    2. 自由现金流
    3. 现金流/利润比
    4. 现金流增长率
    """
    
    operating_cf = stock_data.get('operating_cash_flow', 0)  # 亿
    free_cf = stock_data.get('free_cash_flow', 0)  # 亿
    profit_growth = stock_data.get('profit_growth', 10)
    cash_flow_growth = stock_data.get('cash_flow_growth', 10)
    
    # 1. 经营现金流 (30 分)
    if operating_cf > 1000:
        operating_score = 30
    elif operating_cf > 500:
        operating_score = 25
    elif operating_cf > 200:
        operating_score = 20
    elif operating_cf > 100:
        operating_score = 15
    elif operating_cf > 0:
        operating_score = 10
    else:
        operating_score = 5
    
    # 2. 自由现金流 (30 分)
    if free_cf > 800:
        free_score = 30
    elif free_cf > 400:
        free_score = 25
    elif free_cf > 150:
        free_score = 20
    elif free_cf > 50:
        free_score = 15
    elif free_cf > 0:
        free_score = 10
    else:
        free_score = 5
    
    # 3. 现金流质量 (20 分)
    # 现金流增长与利润增长匹配
    if cash_flow_growth > profit_growth:
        quality_score = 20
    elif cash_flow_growth > profit_growth * 0.8:
        quality_score = 16
    elif cash_flow_growth > 0:
        quality_score = 12
    else:
        quality_score = 6
    
    # 4. 现金流稳定性 (20 分)
    if operating_cf > 0 and free_cf > 0:
        if cash_flow_growth > 20:
            stability_score = 20
        elif cash_flow_growth > 10:
            stability_score = 16
        elif cash_flow_growth > 0:
            stability_score = 12
        else:
            stability_score = 8
    else:
        stability_score = 4
    
    # 总分
    total_score = operating_score + free_score + quality_score + stability_score
    
    # 现金流评级
    if total_score >= 90:
        rating = '极强'
        level = '⭐⭐⭐⭐⭐'
    elif total_score >= 75:
        rating = '强'
        level = '⭐⭐⭐⭐'
    elif total_score >= 60:
        rating = '中等'
        level = '⭐⭐⭐'
    elif total_score >= 45:
        rating = '较弱'
        level = '⭐⭐'
    else:
        rating = '弱'
        level = '⭐'
    
    return {
        'total_score': total_score,
        'rating': rating,
        'level': level,
        'operating_score': operating_score,
        'free_score': free_score,
        'quality_score': quality_score,
        'stability_score': stability_score,
        'operating_cash_flow': operating_cf,
        'free_cash_flow': free_cf,
        'cash_flow_growth': cash_flow_growth,
    }


# ============ 杜邦分析 ============

def dupont_analysis(stock_data: dict) -> dict:
    """
    杜邦分析法
    
    ROE = 净利率 × 总资产周转率 × 权益乘数
    
    分析 ROE 的驱动因素
    """
    
    roe = stock_data.get('roe', 10)
    net_margin = stock_data.get('net_margin', 10)
    asset_turnover = stock_data.get('asset_turnover', 0.5)
    
    # 计算权益乘数
    debt_ratio = stock_data.get('debt_ratio', 50)
    equity_ratio = 1 - debt_ratio / 100
    equity_multiplier = 1 / equity_ratio if equity_ratio > 0 else 1
    
    # 计算 ROE 分解
    calculated_roe = net_margin * asset_turnover * equity_multiplier
    
    # 分析主导因素
    if net_margin > 20:
        driver = '高净利率驱动'
    elif asset_turnover > 1:
        driver = '高周转驱动'
    elif equity_multiplier > 2:
        driver = '高杠杆驱动'
    else:
        driver = '均衡发展'
    
    return {
        'roe': roe,
        'calculated_roe': round(calculated_roe, 2),
        'net_margin': net_margin,
        'asset_turnover': asset_turnover,
        'equity_multiplier': round(equity_multiplier, 2),
        'driver': driver,
    }


# ============ 估值分析扩展 ============

def analyze_valuation_extended(stock_data: dict) -> dict:
    """
    扩展估值分析
    
    添加:
    - EV/EBITDA
    - PEG
    - 相对估值
    """
    
    # 基础估值
    base = analyze_valuation(stock_data)
    
    # 添加 PEG 详细分析
    peg = stock_data.get('peg', 1.0)
    profit_growth = stock_data.get('profit_growth', 10)
    
    if peg < 0.5:
        peg_evaluation = '极度低估'
    elif peg < 0.8:
        peg_evaluation = '低估'
    elif peg < 1.2:
        peg_evaluation = '合理'
    elif peg < 1.5:
        peg_evaluation = '高估'
    else:
        peg_evaluation = '严重高估'
    
    base['peg_evaluation'] = peg_evaluation
    base['profit_growth'] = profit_growth
    
    return base


# ============ 行业对比分析 ============

def analyze_industry_comparison(stock_data: dict) -> dict:
    """
    行业对比分析
    
    对比行业内各项指标
    """
    
    sector = stock_data.get('sector', '一般')
    industry_avg = INDUSTRY_AVERAGE.get(sector, INDUSTRY_AVERAGE['科技'])
    
    comparison = {}
    
    # PE 对比
    pe = stock_data.get('pe_ttm', 20)
    industry_pe = industry_avg.get('pe', 20)
    comparison['pe_vs_industry'] = pe / industry_pe if industry_pe > 0 else 1
    
    # PB 对比
    pb = stock_data.get('pb', 1.5)
    industry_pb = industry_avg.get('pb', 1.5)
    comparison['pb_vs_industry'] = pb / industry_pb if industry_pb > 0 else 1
    
    # ROE 对比
    roe = stock_data.get('roe', 10)
    industry_roe = industry_avg.get('roe', 10)
    comparison['roe_vs_industry'] = roe / industry_roe if industry_roe > 0 else 1
    
    # 增长对比
    growth = stock_data.get('profit_growth', 10)
    industry_growth = industry_avg.get('profit_growth', 10)
    comparison['growth_vs_industry'] = growth / industry_growth if industry_growth > 0 else 1
    
    # 综合评分
    score = 0
    if comparison['pe_vs_industry'] < 0.8:
        score += 25
    elif comparison['pe_vs_industry'] < 1.2:
        score += 15
    
    if comparison['pb_vs_industry'] < 0.8:
        score += 20
    elif comparison['pb_vs_industry'] < 1.2:
        score += 10
    
    if comparison['roe_vs_industry'] > 1.2:
        score += 30
    elif comparison['roe_vs_industry'] > 1:
        score += 20
    
    if comparison['growth_vs_industry'] > 1.2:
        score += 25
    elif comparison['growth_vs_industry'] > 1:
        score += 15
    
    return {
        'comparison': comparison,
        'score': min(100, score),
        'sector': sector,
        'industry_avg': industry_avg,
    }


# ============ 综合基本面评分 ============

def calculate_fundamental_score(stock_data: dict) -> dict:
    """
    计算综合基本面评分
    
    权重:
    - 估值分析：25%
    - 盈利能力：25%
    - 成长能力：20%
    - 偿债能力：15%
    - 现金流：15%
    - 杜邦分析：额外参考
    - 行业对比：额外参考
    """
    
    # 各维度分析
    valuation = analyze_valuation(stock_data)
    profitability = analyze_profitability(stock_data)
    growth = analyze_growth(stock_data)
    solvency = analyze_solvency(stock_data)
    cash_flow = analyze_cash_flow(stock_data)
    
    # 加权总分
    total_score = (
        valuation['total_score'] * 0.25 +
        profitability['total_score'] * 0.25 +
        growth['total_score'] * 0.20 +
        solvency['total_score'] * 0.15 +
        cash_flow['total_score'] * 0.15
    )
    
    # 综合评级
    if total_score >= 90:
        rating = 'AAA'
        level = '极优'
        stars = '⭐⭐⭐⭐⭐'
    elif total_score >= 80:
        rating = 'AA'
        level = '优秀'
        stars = '⭐⭐⭐⭐'
    elif total_score >= 70:
        rating = 'A'
        level = '良好'
        stars = '⭐⭐⭐'
    elif total_score >= 60:
        rating = 'BBB'
        level = '中等'
        stars = '⭐⭐'
    elif total_score >= 50:
        rating = 'BB'
        level = '一般'
        stars = '⭐'
    else:
        rating = 'B'
        level = '较差'
        stars = ''
    
    # 投资建议
    if total_score >= 80:
        suggestion = '强烈推荐'
        action = '积极买入'
    elif total_score >= 70:
        suggestion = '推荐'
        action = '逢低买入'
    elif total_score >= 60:
        suggestion = '谨慎推荐'
        action = '适度配置'
    elif total_score >= 50:
        suggestion = '观望'
        action = '持有观望'
    else:
        suggestion = '谨慎'
        action = '谨慎回避'
    
    return {
        'total_score': round(total_score, 1),
        'rating': rating,
        'level': level,
        'stars': stars,
        'suggestion': suggestion,
        'action': action,
        'valuation': valuation,
        'profitability': profitability,
        'growth': growth,
        'solvency': solvency,
        'cash_flow': cash_flow,
    }


# ============ 报告生成 ============

def print_fundamental_report(symbol: str):
    """打印基本面分析报告"""
    
    stock_data = FUNDAMENTAL_DB.get(symbol)
    
    if not stock_data:
        print(f"❌ 未找到股票 {symbol} 的数据")
        print("\n可用股票:")
        for code in FUNDAMENTAL_DB.keys():
            name = FUNDAMENTAL_DB[code]['name']
            print(f"  - {code} {name}")
        return
    
    print("="*90)
    print(f"📊 {stock_data['name']} ({symbol}) 基本面分析报告")
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*90)
    
    # 基本信息
    print(f"\n【基本信息】")
    print(f"  行业：{stock_data['sector']} - {stock_data['industry']}")
    print(f"  市值：{stock_data['market_cap']}亿")
    print(f"  分析师评级：{stock_data['analyst_rating']}/5.0")
    print(f"  目标价：¥{stock_data['target_price']}")
    
    # 综合评分
    fundamental = calculate_fundamental_score(stock_data)
    
    # 杜邦分析
    dupont = dupont_analysis(stock_data)
    
    # 行业对比
    industry_comp = analyze_industry_comparison(stock_data)
    
    print(f"\n【综合基本面评分】")
    print(f"  总分：{fundamental['total_score']}/100")
    print(f"  评级：{fundamental['rating']} ({fundamental['level']})")
    print(f"  评级：{fundamental['stars']}")
    print(f"  建议：{fundamental['suggestion']} - {fundamental['action']}")
    
    # 杜邦分析
    print(f"\n【杜邦分析】")
    print(f"  ROE: {dupont['roe']}%")
    print(f"  净利率：{dupont['net_margin']}%")
    print(f"  总资产周转率：{dupont['asset_turnover']}")
    print(f"  权益乘数：{dupont['equity_multiplier']}")
    print(f"  驱动因素：{dupont['driver']}")
    
    # 行业对比
    print(f"\n【行业对比】({industry_comp['sector']})")
    comp = industry_comp['comparison']
    print(f"  PE vs 行业：{comp['pe_vs_industry']:.2f}x {'✅ 低估' if comp['pe_vs_industry'] < 0.8 else '⚠️ 高估' if comp['pe_vs_industry'] > 1.2 else '➡️ 合理'}")
    print(f"  PB vs 行业：{comp['pb_vs_industry']:.2f}x {'✅ 低估' if comp['pb_vs_industry'] < 0.8 else '⚠️ 高估' if comp['pb_vs_industry'] > 1.2 else '➡️ 合理'}")
    print(f"  ROE vs 行业：{comp['roe_vs_industry']:.2f}x {'✅ 优秀' if comp['roe_vs_industry'] > 1.2 else '➡️ 平均' if comp['roe_vs_industry'] > 0.8 else '❌ 落后'}")
    print(f"  增长 vs 行业：{comp['growth_vs_industry']:.2f}x {'✅ 高增长' if comp['growth_vs_industry'] > 1.2 else '➡️ 平均' if comp['growth_vs_industry'] > 0.8 else '❌ 低增长'}")
    print(f"  行业对比评分：{industry_comp['score']}/100")
    
    # 各维度评分
    print(f"\n【各维度评分】")
    print(f"  估值分析：{fundamental['valuation']['total_score']}/100 - {fundamental['valuation']['rating']}")
    print(f"  盈利能力：{fundamental['profitability']['total_score']}/100 - {fundamental['profitability']['rating']}")
    print(f"  成长能力：{fundamental['growth']['total_score']}/100 - {fundamental['growth']['rating']}")
    print(f"  偿债能力：{fundamental['solvency']['total_score']}/50 - {fundamental['solvency']['rating']}")
    print(f"  现金流：  {fundamental['cash_flow']['total_score']}/100 - {fundamental['cash_flow']['rating']}")
    
    # 详细估值
    print(f"\n【估值分析】")
    v = fundamental['valuation']
    print(f"  PE: {v['pe']} (行业{INDUSTRY_AVERAGE.get(stock_data['sector'], {}).get('pe', 'N/A')}x) - {v['pe_vs_industry']}")
    print(f"  PB: {v['pb']} (行业{INDUSTRY_AVERAGE.get(stock_data['sector'], {}).get('pb', 'N/A')}x) - {v['pb_vs_industry']}")
    print(f"  PEG: {v['peg']}")
    print(f"  PS: {v['ps']}")
    print(f"  股息率：{v['dividend_yield']}%")
    
    # 详细盈利
    print(f"\n【盈利能力】")
    p = fundamental['profitability']
    print(f"  ROE: {p['roe']}%")
    print(f"  ROA: {p['roa']}%")
    print(f"  毛利率：{p['gross_margin']}%")
    print(f"  净利率：{p['net_margin']}%")
    print(f"  利润增长：{p['profit_growth']}%")
    
    # 详细成长
    print(f"\n【成长能力】")
    g = fundamental['growth']
    print(f"  营收增长：{g['revenue_growth']}%")
    print(f"  利润增长：{g['profit_growth']}%")
    print(f"  现金流增长：{g['cash_flow_growth']}%")
    
    # 详细偿债
    print(f"\n【偿债能力】")
    s = fundamental['solvency']
    print(f"  资产负债率：{s['debt_ratio']}%")
    print(f"  流动比率：{s['current_ratio']}")
    print(f"  速动比率：{s['quick_ratio']}")
    
    # 详细现金流
    print(f"\n【现金流分析】")
    c = fundamental['cash_flow']
    print(f"  经营现金流：{c['operating_cash_flow']}亿")
    print(f"  自由现金流：{c['free_cash_flow']}亿")
    print(f"  现金流增长：{c['cash_flow_growth']}%")
    
    print("\n" + "="*90)
    print(f"报告完成：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*90)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='深度基本面分析')
    parser.add_argument('--stock', type=str, help='股票代码')
    parser.add_argument('--compare', action='store_true', help='行业对比')
    parser.add_argument('--all', action='store_true', help='分析所有股票')
    
    args = parser.parse_args()
    
    if args.stock:
        print_fundamental_report(args.stock)
    elif args.compare:
        print("行业对比功能开发中...")
    elif args.all:
        for symbol in FUNDAMENTAL_DB.keys():
            print_fundamental_report(symbol)
            print("\n")
    else:
        parser.print_help()
        print("\n可用股票:")
        for code, data in FUNDAMENTAL_DB.items():
            print(f"  - {code} {data['name']}")


if __name__ == '__main__':
    main()
