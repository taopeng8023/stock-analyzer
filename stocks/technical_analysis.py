#!/usr/bin/env python3
"""
技术面分析工具
基于 K 线、均线、指标的综合技术分析系统

⚠️  仅用于研究学习，不构成投资建议

分析维度:
1. K 线形态分析 (趋势/反转/整理)
2. 均线系统 (MA5/10/20/60)
3. MACD 指标 (金叉/死叉/背离)
4. KDJ 指标 (超买/超卖)
5. RSI 指标 (强弱)
6. 成交量分析 (放量/缩量)
7. 支撑阻力位
8. 综合技术评分

用法:
    python3 technical_analysis.py --stock 600000.SH  # 分析单只股票
    python3 technical_analysis.py --all              # 分析全部
    python3 technical_analysis.py --compare          # 对比分析
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ============ 技术指标数据库（示例数据） ============

TECHNICAL_DB = {
    '600000.SH': {
        'name': '浦发银行',
        'price': 10.38,
        'kline': {
            'open': 10.29,
            'high': 10.42,
            'low': 10.27,
            'close': 10.38,
            'volume': 762601,
            'amount': 451165,
        },
        'ma': {
            'ma5': 10.25,
            'ma10': 10.15,
            'ma20': 9.95,
            'ma60': 9.75,
        },
        'macd': {
            'dif': 0.15,
            'dea': 0.12,
            'bar': 0.06,
            'signal': '金叉',  # 金叉/死叉/中性
        },
        'kdj': {
            'k': 65,
            'd': 58,
            'j': 79,
            'signal': '偏多',  # 超买/超卖/偏多/偏空
        },
        'rsi': {
            'rsi6': 58,
            'rsi12': 55,
            'rsi24': 52,
            'signal': '中性',
        },
        'volume': {
            'volume_ratio': 1.25,  # 量比
            'turnover_rate': 2.5,  # 换手率
            'signal': '放量',  # 放量/缩量/平量
        },
        'pattern': {
            'trend': '上升',  # 上升/下降/盘整
            'formation': '多头排列',  # 形态
            'support': 10.15,  # 支撑位
            'resistance': 10.55,  # 阻力位
        },
    },
    '000001.SZ': {
        'name': '平安银行',
        'price': 11.03,
        'kline': {
            'open': 10.92,
            'high': 11.07,
            'low': 10.90,
            'close': 11.03,
            'volume': 1076657,
            'amount': 669266,
        },
        'ma': {
            'ma5': 10.85,
            'ma10': 10.65,
            'ma20': 10.35,
            'ma60': 10.05,
        },
        'macd': {
            'dif': 0.22,
            'dea': 0.18,
            'bar': 0.08,
            'signal': '金叉',
        },
        'kdj': {
            'k': 72,
            'd': 65,
            'j': 86,
            'signal': '偏多',
        },
        'rsi': {
            'rsi6': 62,
            'rsi12': 58,
            'rsi24': 55,
            'signal': '偏强',
        },
        'volume': {
            'volume_ratio': 1.35,
            'turnover_rate': 3.2,
            'signal': '放量',
        },
        'pattern': {
            'trend': '上升',
            'formation': '突破形态',
            'support': 10.75,
            'resistance': 11.25,
        },
    },
    '600256.SH': {
        'name': '广汇能源',
        'price': 7.00,
        'kline': {
            'open': 6.85,
            'high': 7.05,
            'low': 6.82,
            'close': 7.00,
            'volume': 2053000,
            'amount': 1368700,
        },
        'ma': {
            'ma5': 6.75,
            'ma10': 6.55,
            'ma20': 6.25,
            'ma60': 5.95,
        },
        'macd': {
            'dif': 0.28,
            'dea': 0.22,
            'bar': 0.12,
            'signal': '金叉',
        },
        'kdj': {
            'k': 78,
            'd': 70,
            'j': 94,
            'signal': '超买',
        },
        'rsi': {
            'rsi6': 68,
            'rsi12': 65,
            'rsi24': 60,
            'signal': '偏强',
        },
        'volume': {
            'volume_ratio': 1.85,
            'turnover_rate': 4.5,
            'signal': '明显放量',
        },
        'pattern': {
            'trend': '强势上升',
            'formation': '加速上涨',
            'support': 6.65,
            'resistance': 7.25,
        },
    },
}


# ============ K 线形态分析 ============

def analyze_kline_pattern(stock_data: dict) -> dict:
    """
    K 线形态分析
    
    分析内容:
    1. 单 K 线形态 (大阳/大阴/十字星等)
    2. K 线组合 (早晨之星/黄昏之星等)
    3. 趋势判断
    """
    
    kline = stock_data.get('kline', {})
    open_p = kline.get('open', 0)
    close_p = kline.get('close', 0)
    high_p = kline.get('high', 0)
    low_p = kline.get('low', 0)
    
    # 1. 计算实体和影线
    body = abs(close_p - open_p)
    upper_shadow = high_p - max(open_p, close_p)
    lower_shadow = min(open_p, close_p) - low_p
    range_p = high_p - low_p
    
    # 2. 判断 K 线类型
    if body > range_p * 0.7:
        if close_p > open_p:
            kline_type = '大阳线'
            signal = '强势'
        else:
            kline_type = '大阴线'
            signal = '弱势'
    elif body < range_p * 0.2:
        kline_type = '十字星'
        signal = '变盘'
    elif close_p > open_p:
        kline_type = '小阳线'
        signal = '偏强'
    else:
        kline_type = '小阴线'
        signal = '偏弱'
    
    # 3. 判断位置
    if lower_shadow > body * 2:
        kline_type = '锤头线'
        signal = '见底信号'
    elif upper_shadow > body * 2:
        kline_type = '射击之星'
        signal = '见顶信号'
    
    # 4. 趋势判断
    ma = stock_data.get('ma', {})
    price = stock_data.get('price', 0)
    
    if price > ma.get('ma5', 0) > ma.get('ma10', 0) > ma.get('ma20', 0):
        trend = '上升趋势'
    elif price < ma.get('ma5', 0) < ma.get('ma10', 0) < ma.get('ma20', 0):
        trend = '下降趋势'
    else:
        trend = '盘整'
    
    # 5. 评分 (0-100)
    score = 50
    if signal in ['强势', '见底信号']:
        score += 20
    elif signal in ['偏强']:
        score += 10
    elif signal in ['弱势', '见顶信号']:
        score -= 20
    elif signal in ['偏弱']:
        score -= 10
    
    if trend == '上升趋势':
        score += 15
    elif trend == '下降趋势':
        score -= 15
    
    return {
        'kline_type': kline_type,
        'signal': signal,
        'trend': trend,
        'score': min(100, max(0, score)),
        'body': round(body, 2),
        'upper_shadow': round(upper_shadow, 2),
        'lower_shadow': round(lower_shadow, 2),
    }


# ============ 均线系统分析 ============

def analyze_ma_system(stock_data: dict) -> dict:
    """
    均线系统分析
    
    分析内容:
    1. 均线排列 (多头/空头)
    2. 金叉死叉
    3. 支撑阻力
    4. 乖离率
    """
    
    ma = stock_data.get('ma', {})
    price = stock_data.get('price', 0)
    
    ma5 = ma.get('ma5', 0)
    ma10 = ma.get('ma10', 0)
    ma20 = ma.get('ma20', 0)
    ma60 = ma.get('ma60', 0)
    
    # 1. 判断排列
    if ma5 > ma10 > ma20 > ma60:
        arrangement = '多头排列'
        arrangement_score = 25
    elif ma5 < ma10 < ma20 < ma60:
        arrangement = '空头排列'
        arrangement_score = -25
    else:
        arrangement = '混乱排列'
        arrangement_score = 0
    
    # 2. 判断位置
    if price > ma5 > ma10 > ma20:
        position = '强势区'
        position_score = 20
    elif price > ma20 > ma60:
        position = '多头区'
        position_score = 15
    elif price < ma60 < ma20:
        position = '空头区'
        position_score = -20
    else:
        position = '震荡区'
        position_score = 0
    
    # 3. 计算乖离率
    bias5 = (price - ma5) / ma5 * 100 if ma5 > 0 else 0
    bias10 = (price - ma10) / ma10 * 100 if ma10 > 0 else 0
    bias20 = (price - ma20) / ma20 * 100 if ma20 > 0 else 0
    
    # 4. 支撑阻力
    support = ma20 if price > ma20 else ma60
    resistance = ma5 if price < ma5 else ma20
    
    # 5. 总分
    total_score = 50 + arrangement_score + position_score
    
    return {
        'arrangement': arrangement,
        'position': position,
        'score': min(100, max(0, total_score)),
        'bias5': round(bias5, 2),
        'bias10': round(bias10, 2),
        'bias20': round(bias20, 2),
        'support': round(support, 2),
        'resistance': round(resistance, 2),
        'ma5': ma5,
        'ma10': ma10,
        'ma20': ma20,
        'ma60': ma60,
    }


# ============ MACD 指标分析 ============

def analyze_macd(stock_data: dict) -> dict:
    """
    MACD 指标分析
    
    分析内容:
    1. 金叉死叉
    2. 红绿柱
    3. 背离
    4. 零轴位置
    """
    
    macd = stock_data.get('macd', {})
    dif = macd.get('dif', 0)
    dea = macd.get('dea', 0)
    bar = macd.get('bar', 0)
    
    # 1. 判断金叉死叉
    if dif > dea and macd.get('signal', '') == '金叉':
        cross = '金叉'
        cross_score = 20
    elif dif < dea and macd.get('signal', '') == '死叉':
        cross = '死叉'
        cross_score = -20
    else:
        cross = '延续'
        cross_score = 0
    
    # 2. 判断红绿柱
    if bar > 0:
        bar_type = '红柱'
        bar_strength = '强' if bar > 0.1 else '弱'
        bar_score = 10
    else:
        bar_type = '绿柱'
        bar_strength = '强' if bar < -0.1 else '弱'
        bar_score = -10
    
    # 3. 零轴位置
    if dif > 0 and dea > 0:
        zero_axis = '零轴上方'
        zero_score = 10
    elif dif < 0 and dea < 0:
        zero_axis = '零轴下方'
        zero_score = -10
    else:
        zero_axis = '跨越零轴'
        zero_score = 0
    
    # 4. 总分
    total_score = 50 + cross_score + bar_score + zero_score
    
    return {
        'cross': cross,
        'bar_type': bar_type,
        'bar_strength': bar_strength,
        'zero_axis': zero_axis,
        'score': min(100, max(0, total_score)),
        'dif': round(dif, 3),
        'dea': round(dea, 3),
        'bar': round(bar, 3),
    }


# ============ KDJ 指标分析 ============

def analyze_kdj(stock_data: dict) -> dict:
    """
    KDJ 指标分析
    
    分析内容:
    1. KDJ 位置
    2. 金叉死叉
    3. 超买超卖
    """
    
    kdj = stock_data.get('kdj', {})
    k = kdj.get('k', 50)
    d = kdj.get('d', 50)
    j = kdj.get('j', 50)
    
    # 1. 判断位置
    if k > 80 and d > 80:
        position = '超买区'
        position_score = -15
    elif k < 20 and d < 20:
        position = '超卖区'
        position_score = 15
    elif k > 50 and d > 50:
        position = '强势区'
        position_score = 10
    else:
        position = '弱势区'
        position_score = -5
    
    # 2. 判断金叉死叉
    if k > d and kdj.get('signal', '') in ['偏多', '金叉']:
        cross = '金叉'
        cross_score = 15
    elif k < d and kdj.get('signal', '') in ['偏空', '死叉']:
        cross = '死叉'
        cross_score = -15
    else:
        cross = '延续'
        cross_score = 0
    
    # 3. J 值判断
    if j > 100:
        j_signal = '严重超买'
        j_score = -20
    elif j < 0:
        j_signal = '严重超卖'
        j_score = 20
    else:
        j_signal = '正常'
        j_score = 0
    
    # 4. 总分
    total_score = 50 + position_score + cross_score + j_score
    
    return {
        'position': position,
        'cross': cross,
        'j_signal': j_signal,
        'score': min(100, max(0, total_score)),
        'k': k,
        'd': d,
        'j': j,
    }


# ============ RSI 指标分析 ============

def analyze_rsi(stock_data: dict) -> dict:
    """
    RSI 指标分析
    
    分析内容:
    1. RSI 位置
    2. 强弱判断
    3. 背离
    """
    
    rsi = stock_data.get('rsi', {})
    rsi6 = rsi.get('rsi6', 50)
    rsi12 = rsi.get('rsi12', 50)
    rsi24 = rsi.get('rsi24', 50)
    
    # 1. 判断强弱
    if rsi6 > 70:
        strength = '超买'
        strength_score = -15
    elif rsi6 < 30:
        strength = '超卖'
        strength_score = 15
    elif rsi6 > 50:
        strength = '偏强'
        strength_score = 10
    else:
        strength = '偏弱'
        strength_score = -5
    
    # 2. 判断排列
    if rsi6 > rsi12 > rsi24:
        arrangement = '多头排列'
        arrangement_score = 15
    elif rsi6 < rsi12 < rsi24:
        arrangement = '空头排列'
        arrangement_score = -15
    else:
        arrangement = '混乱'
        arrangement_score = 0
    
    # 3. 总分
    total_score = 50 + strength_score + arrangement_score
    
    return {
        'strength': strength,
        'arrangement': arrangement,
        'score': min(100, max(0, total_score)),
        'rsi6': rsi6,
        'rsi12': rsi12,
        'rsi24': rsi24,
    }


# ============ 成交量分析 ============

def analyze_volume(stock_data: dict) -> dict:
    """
    成交量分析
    
    分析内容:
    1. 量比
    2. 换手率
    3. 放量缩量
    """
    
    volume = stock_data.get('volume', {})
    volume_ratio = volume.get('volume_ratio', 1.0)
    turnover_rate = volume.get('turnover_rate', 1.0)
    
    # 1. 量比判断
    if volume_ratio > 2.5:
        volume_signal = '明显放量'
        volume_score = 20
    elif volume_ratio > 1.5:
        volume_signal = '放量'
        volume_score = 15
    elif volume_ratio > 0.8:
        volume_signal = '平量'
        volume_score = 5
    else:
        volume_signal = '缩量'
        volume_score = -5
    
    # 2. 换手率判断
    if turnover_rate > 10:
        turnover_signal = '高换手'
        turnover_score = 15
    elif turnover_rate > 5:
        turnover_signal = '活跃'
        turnover_score = 10
    elif turnover_rate > 2:
        turnover_signal = '正常'
        turnover_score = 5
    else:
        turnover_signal = '低迷'
        turnover_score = -5
    
    # 3. 总分
    total_score = 50 + volume_score + turnover_score
    
    return {
        'volume_signal': volume_signal,
        'turnover_signal': turnover_signal,
        'score': min(100, max(0, total_score)),
        'volume_ratio': volume_ratio,
        'turnover_rate': turnover_rate,
    }


# ============ 综合技术评分 ============

def calculate_technical_score(stock_data: dict) -> dict:
    """
    计算综合技术评分
    
    权重:
    - K 线形态：20%
    - 均线系统：25%
    - MACD: 20%
    - KDJ: 15%
    - RSI: 10%
    - 成交量：10%
    """
    
    # 各维度分析
    kline = analyze_kline_pattern(stock_data)
    ma = analyze_ma_system(stock_data)
    macd = analyze_macd(stock_data)
    kdj = analyze_kdj(stock_data)
    rsi = analyze_rsi(stock_data)
    volume = analyze_volume(stock_data)
    
    # 加权总分
    total_score = (
        kline['score'] * 0.20 +
        ma['score'] * 0.25 +
        macd['score'] * 0.20 +
        kdj['score'] * 0.15 +
        rsi['score'] * 0.10 +
        volume['score'] * 0.10
    )
    
    # 技术评级
    if total_score >= 80:
        rating = '极强'
        stars = '⭐⭐⭐⭐⭐'
        signal = '强烈买入'
    elif total_score >= 70:
        rating = '强'
        stars = '⭐⭐⭐⭐'
        signal = '买入'
    elif total_score >= 60:
        rating = '偏强'
        stars = '⭐⭐⭐'
        signal = '增持'
    elif total_score >= 50:
        rating = '中性'
        stars = '⭐⭐'
        signal = '持有'
    elif total_score >= 40:
        rating = '偏弱'
        stars = '⭐'
        signal = '减持'
    else:
        rating = '弱'
        stars = ''
        signal = '卖出'
    
    # 买卖点建议
    pattern = stock_data.get('pattern', {})
    support = pattern.get('support', 0)
    resistance = pattern.get('resistance', 0)
    
    return {
        'total_score': round(total_score, 1),
        'rating': rating,
        'stars': stars,
        'signal': signal,
        'kline': kline,
        'ma': ma,
        'macd': macd,
        'kdj': kdj,
        'rsi': rsi,
        'volume': volume,
        'support': support,
        'resistance': resistance,
    }


# ============ 报告生成 ============

def print_technical_report(symbol: str):
    """打印技术面分析报告"""
    
    stock_data = TECHNICAL_DB.get(symbol)
    
    if not stock_data:
        print(f"❌ 未找到股票 {symbol} 的技术数据")
        print("\n可用股票:")
        for code in TECHNICAL_DB.keys():
            name = TECHNICAL_DB[code]['name']
            print(f"  - {code} {name}")
        return
    
    print("="*90)
    print(f"📈 {stock_data['name']} ({symbol}) 技术面分析报告")
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*90)
    
    # 基本信息
    print(f"\n【基本行情】")
    kline = stock_data.get('kline', {})
    print(f"  现价：¥{stock_data['price']}")
    print(f"  开盘：¥{kline.get('open', 0)} | 最高：¥{kline.get('high', 0)} | 最低：¥{kline.get('low', 0)}")
    print(f"  成交量：{kline.get('volume', 0):,}手 | 成交额：{kline.get('amount', 0):,.0f}万")
    
    # 综合评分
    technical = calculate_technical_score(stock_data)
    
    print(f"\n【综合技术评分】")
    print(f"  总分：{technical['total_score']}/100")
    print(f"  评级：{technical['rating']} {technical['stars']}")
    print(f"  信号：{technical['signal']}")
    print(f"  支撑位：¥{technical['support']} | 阻力位：¥{technical['resistance']}")
    
    # 各维度评分
    print(f"\n【各维度评分】")
    print(f"  K 线形态：{technical['kline']['score']}/100 - {technical['kline']['kline_type']} ({technical['kline']['signal']})")
    print(f"  均线系统：{technical['ma']['score']}/100 - {technical['ma']['arrangement']} ({technical['ma']['position']})")
    print(f"  MACD:     {technical['macd']['score']}/100 - {technical['macd']['cross']} ({technical['macd']['bar_type']})")
    print(f"  KDJ:      {technical['kdj']['score']}/100 - {technical['kdj']['position']} ({technical['kdj']['cross']})")
    print(f"  RSI:      {technical['rsi']['score']}/100 - {technical['rsi']['strength']}")
    print(f"  成交量：  {technical['volume']['score']}/100 - {technical['volume']['volume_signal']}")
    
    # 详细指标
    print(f"\n【详细指标】")
    print(f"  均线：MA5={technical['ma']['ma5']} MA10={technical['ma']['ma10']} MA20={technical['ma']['ma20']} MA60={technical['ma']['ma60']}")
    print(f"  MACD: DIF={technical['macd']['dif']} DEA={technical['macd']['dea']} BAR={technical['macd']['bar']}")
    print(f"  KDJ: K={technical['kdj']['k']} D={technical['kdj']['d']} J={technical['kdj']['j']}")
    print(f"  RSI: RSI6={technical['rsi']['rsi6']} RSI12={technical['rsi']['rsi12']} RSI24={technical['rsi']['rsi24']}")
    print(f"  量比：{technical['volume']['volume_ratio']} 换手率：{technical['volume']['turnover_rate']}%")
    
    # 操作建议
    print(f"\n【操作建议】")
    if technical['total_score'] >= 70:
        print(f"  💡 建议：{technical['signal']}")
        print(f"  🎯 买入区间：¥{technical['support']} - ¥{technical['support'] * 1.02}")
        print(f"  🎯 目标价位：¥{technical['resistance']} - ¥{technical['resistance'] * 1.05}")
        print(f"  🛑 止损位：¥{technical['support'] * 0.95}")
    elif technical['total_score'] >= 50:
        print(f"  💡 建议：{technical['signal']}")
        print(f"  🎯 观望区间：¥{technical['support']} - ¥{technical['resistance']}")
        print(f"  🛑 止损位：¥{technical['support'] * 0.95}")
    else:
        print(f"  💡 建议：{technical['signal']}")
        print(f"  ⚠️ 风险较高，建议回避")
    
    print("\n" + "="*90)
    print(f"报告完成：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*90)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='技术面分析工具')
    parser.add_argument('--stock', type=str, help='股票代码')
    parser.add_argument('--all', action='store_true', help='分析所有股票')
    parser.add_argument('--compare', action='store_true', help='对比分析')
    
    args = parser.parse_args()
    
    if args.stock:
        print_technical_report(args.stock)
    elif args.all:
        for symbol in TECHNICAL_DB.keys():
            print_technical_report(symbol)
            print("\n")
    elif args.compare:
        print("对比分析功能开发中...")
    else:
        parser.print_help()
        print("\n可用股票:")
        for code, data in TECHNICAL_DB.items():
            print(f"  - {code} {data['name']}")


if __name__ == '__main__':
    main()
