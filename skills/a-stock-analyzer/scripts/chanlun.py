#!/usr/bin/env python3
"""
缠论技术分析模块
包含：分型、笔、线段、中枢、背驰、买卖点识别
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class FractalType(Enum):
    TOP = "顶分型"
    BOTTOM = "底分型"


class TrendType(Enum):
    UP = "上涨"
    DOWN = "下跌"
    CONSOLIDATION = "盘整"


class BuySellPoint(Enum):
    BUY_1 = "一买"
    BUY_2 = "二买"
    BUY_3 = "三买"
    SELL_1 = "一卖"
    SELL_2 = "二卖"
    SELL_3 = "三卖"


@dataclass
class Fractal:
    """分型"""
    index: int
    price: float
    fractal_type: FractalType
    high: float
    low: float
    date: str


@dataclass
class Bi:
    """笔"""
    start_idx: int
    end_idx: int
    start_price: float
    end_price: float
    direction: int  # 1: 向上，-1: 向下
    high: float
    low: float
    start_date: str
    end_date: str


@dataclass
class Duan:
    """线段"""
    start_idx: int
    end_idx: int
    start_price: float
    end_price: float
    direction: int
    bis: List[Bi]


@dataclass
class Zhongshu:
    """中枢"""
    start_idx: int
    end_idx: int
    high: float  # 中枢上沿 (ZG)
    low: float   # 中枢下沿 (ZD)
    start_price: float
    end_price: float
    direction: int
    level: int = 1  # 中枢级别


@dataclass
class Beichi:
    """背驰"""
    price_low: float
    price_high: float
    macd_low: float
    macd_high: float
    beichi_type: str  # "顶背驰" or "底背驰"
    strength: float  # 背驰强度 0-1


def find_fractals(df: pd.DataFrame) -> List[Fractal]:
    """
    识别分型 (顶分型和底分型)
    顶分型：中间 K 线高点最高，低点也最高
    底分型：中间 K 线低点最低，高点也最低
    """
    fractals = []
    
    if len(df) < 3:
        return fractals
    
    for i in range(1, len(df) - 1):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]
        next_k = df.iloc[i + 1]
        
        # 顶分型判断
        if (curr['最高'] > prev['最高'] and 
            curr['最高'] > next_k['最高'] and
            curr['最低'] > prev['最低'] and 
            curr['最低'] > next_k['最低']):
            fractals.append(Fractal(
                index=i,
                price=curr['最高'],
                fractal_type=FractalType.TOP,
                high=curr['最高'],
                low=curr['最低'],
                date=str(curr.get('日期', i))
            ))
        
        # 底分型判断
        elif (curr['最低'] < prev['最低'] and 
              curr['最低'] < next_k['最低'] and
              curr['最高'] < prev['最高'] and 
              curr['最高'] < next_k['最高']):
            fractals.append(Fractal(
                index=i,
                price=curr['最低'],
                fractal_type=FractalType.BOTTOM,
                high=curr['最高'],
                low=curr['最低'],
                date=str(curr.get('日期', i))
            ))
    
    return fractals


def filter_fractals(fractals: List[Fractal], min_distance: int = 4) -> List[Fractal]:
    """
    过滤分型，确保相邻分型之间有足够的 K 线距离
    处理包含关系
    """
    if not fractals:
        return []
    
    filtered = [fractals[0]]
    
    for i in range(1, len(fractals)):
        curr = fractals[i]
        prev = filtered[-1]
        
        # 确保距离足够
        if curr.index - prev.index < min_distance:
            # 同类型分型，保留极值
            if curr.fractal_type == prev.fractal_type:
                if curr.fractal_type == FractalType.TOP and curr.price > prev.price:
                    filtered[-1] = curr
                elif curr.fractal_type == FractalType.BOTTOM and curr.price < prev.price:
                    filtered[-1] = curr
            else:
                # 不同类型但距离太近，跳过
                continue
        else:
            filtered.append(curr)
    
    return filtered


def form_bis(fractals: List[Fractal], df: pd.DataFrame) -> List[Bi]:
    """
    由分型形成笔
    笔的条件：
    1. 顶底分型交替出现
    2. 顶分型高点 > 底分型低点 (向上笔)
    3. 至少 5 根 K 线 (包含处理后的)
    """
    if len(fractals) < 2:
        return []
    
    bis = []
    
    for i in range(len(fractals) - 1):
        curr = fractals[i]
        next_f = fractals[i + 1]
        
        # 必须是交替的分型
        if curr.fractal_type == next_f.fractal_type:
            continue
        
        # 检查 K 线数量
        if next_f.index - curr.index < 4:
            continue
        
        # 确定方向
        if curr.fractal_type == FractalType.BOTTOM:
            # 向上笔
            direction = 1
            start_price = curr.price
            end_price = next_f.price
            high = next_f.high
            low = curr.low
            
            # 验证：顶分型高点必须高于底分型
            if end_price <= start_price:
                continue
        else:
            # 向下笔
            direction = -1
            start_price = curr.price
            end_price = next_f.price
            high = curr.high
            low = next_f.low
            
            # 验证：底分型低点必须低于顶分型
            if end_price >= start_price:
                continue
        
        bis.append(Bi(
            start_idx=curr.index,
            end_idx=next_f.index,
            start_price=start_price,
            end_price=end_price,
            direction=direction,
            high=high,
            low=low,
            start_date=curr.date,
            end_date=next_f.date
        ))
    
    return bis


def form_duan(bis: List[Bi]) -> List[Duan]:
    """
    由笔形成线段
    线段至少由 3 笔组成，且方向一致
    """
    if len(bis) < 3:
        return []
    
    duans = []
    current_bis = [bis[0]]
    
    for i in range(1, len(bis)):
        curr_bi = bis[i]
        prev_bi = bis[i - 1]
        
        # 检查是否破坏线段
        if len(current_bis) >= 3:
            # 检查是否有反向突破
            if curr_bi.direction == current_bis[0].direction:
                # 同向，继续
                current_bis.append(curr_bi)
            else:
                # 反向，检查是否破坏
                if curr_bi.direction == 1:  # 当前向上
                    # 检查是否突破前高
                    if curr_bi.end_price > max(b.end_price for b in current_bis[::2]):
                        # 线段延续
                        current_bis.append(curr_bi)
                    else:
                        # 线段结束
                        if len(current_bis) >= 3:
                            duans.append(create_duan(current_bis))
                        current_bis = [prev_bi, curr_bi]
                else:  # 当前向下
                    if curr_bi.end_price < min(b.end_price for b in current_bis[::2]):
                        current_bis.append(curr_bi)
                    else:
                        if len(current_bis) >= 3:
                            duans.append(create_duan(current_bis))
                        current_bis = [prev_bi, curr_bi]
        else:
            current_bis.append(curr_bi)
    
    # 添加最后一个线段
    if len(current_bis) >= 3:
        duans.append(create_duan(current_bis))
    
    return duans


def create_duan(bis: List[Bi]) -> Duan:
    """创建线段"""
    direction = bis[0].direction
    return Duan(
        start_idx=bis[0].start_idx,
        end_idx=bis[-1].end_idx,
        start_price=bis[0].start_price,
        end_price=bis[-1].end_price,
        direction=direction,
        bis=bis.copy()
    )


def find_zhongshu(bis: List[Bi]) -> List[Zhongshu]:
    """
    识别中枢
    中枢：至少 3 笔重叠的价格区间
    """
    if len(bis) < 3:
        return []
    
    zhongshus = []
    i = 0
    
    while i < len(bis) - 2:
        # 取连续 3 笔
        b1, b2, b3 = bis[i], bis[i + 1], bis[i + 2]
        
        # 计算重叠区间
        high_points = [b1.high, b2.high, b3.high]
        low_points = [b1.low, b2.low, b3.low]
        
        zg = min(high_points)  # 中枢上沿
        zd = max(low_points)   # 中枢下沿
        
        # 检查是否有重叠
        if zg > zd:
            # 找到中枢的延伸
            j = i + 3
            while j < len(bis):
                bj = bis[j]
                # 检查是否仍在中枢范围内
                if bj.low < zg and bj.high > zd:
                    j += 1
                else:
                    break
            
            # 创建中枢
            zhongshus.append(Zhongshu(
                start_idx=bis[i].start_idx,
                end_idx=bis[j-1].end_idx,
                high=zg,
                low=zd,
                start_price=bis[i].start_price,
                end_price=bis[j-1].end_price,
                direction=bis[i].direction,
                level=1
            ))
            
            i = j
        else:
            i += 1
    
    return zhongshus


def calculate_macd_for_beichi(df: pd.DataFrame, bis: List[Bi]) -> Dict[int, float]:
    """计算每笔对应的 MACD 面积"""
    macd_areas = {}
    
    if 'MACD' not in df.columns:
        # 计算 MACD
        exp1 = df['收盘'].ewm(span=12, adjust=False).mean()
        exp2 = df['收盘'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']
    
    for bi in bis:
        start = max(0, bi.start_idx - 2)
        end = min(len(df), bi.end_idx + 2)
        segment = df.iloc[start:end]
        
        # 计算 MACD 柱面积
        area = abs(segment['Histogram'].sum())
        macd_areas[bi.start_idx] = area
    
    return macd_areas


def find_beichi(bis: List[Bi], df: pd.DataFrame) -> List[Beichi]:
    """
    识别背驰
    底背驰：价格创新低，但 MACD 不创新低
    顶背驰：价格创新高，但 MACD 不创新高
    """
    beichis = []
    macd_areas = calculate_macd_for_beichi(df, bis)
    
    # 寻找同向笔进行比较
    for i in range(2, len(bis), 2):
        b1 = bis[i - 2]
        b2 = bis[i]
        
        if b1.direction != b2.direction:
            continue
        
        area1 = macd_areas.get(b1.start_idx, 0)
        area2 = macd_areas.get(b2.start_idx, 0)
        
        if b1.direction == -1:  # 向下笔
            # 底背驰判断
            if b2.end_price < b1.end_price and area2 < area1:
                strength = 1 - (area2 / area1) if area1 > 0 else 0
                beichis.append(Beichi(
                    price_low=b2.end_price,
                    price_high=b1.end_price,
                    macd_low=area2,
                    macd_high=area1,
                    beichi_type="底背驰",
                    strength=strength
                ))
        else:  # 向上笔
            # 顶背驰判断
            if b2.end_price > b1.end_price and area2 < area1:
                strength = 1 - (area2 / area1) if area1 > 0 else 0
                beichis.append(Beichi(
                    price_low=b1.end_price,
                    price_high=b2.end_price,
                    macd_low=area2,
                    macd_high=area1,
                    beichi_type="顶背驰",
                    strength=strength
                ))
    
    return beichis


def find_buy_sell_points(bis: List[Bi], zhongshus: List[Zhongshu], 
                          beichis: List[Beichi]) -> List[Dict]:
    """
    识别三类买卖点
    一买：底背驰后的第一个底分型
    二买：一买后的第一个不破新低的高点回调
    三买：突破中枢后回踩不破中枢高点
    一卖：顶背驰后的第一个顶分型
    二卖：一卖后的第一个不创新高的高点回调
    三卖：跌破中枢后反弹不过中枢低点
    """
    points = []
    
    if len(bis) < 3:
        return points
    
    # 一买/一卖 (基于背驰)
    for beichi in beichis:
        if beichi.beichi_type == "底背驰":
            points.append({
                'type': BuySellPoint.BUY_1.value,
                'price': beichi.price_low,
                'confidence': beichi.strength,
                'description': f"底背驰形成，MACD 背离强度 {beichi.strength:.2f}"
            })
        else:
            points.append({
                'type': BuySellPoint.SELL_1.value,
                'price': beichi.price_high,
                'confidence': beichi.strength,
                'description': f"顶背驰形成，MACD 背离强度 {beichi.strength:.2f}"
            })
    
    # 二买/二卖 (基于笔的回调)
    for i in range(2, len(bis)):
        if bis[i].direction == 1 and bis[i-2].direction == -1:
            # 可能的二买
            if bis[i].end_price > bis[i-2].end_price and bis[i-1].end_price > bis[i-2].end_price:
                if len(points) > 0 and points[-1]['type'] == BuySellPoint.BUY_1.value:
                    points.append({
                        'type': BuySellPoint.BUY_2.value,
                        'price': bis[i-1].low,
                        'confidence': 0.6,
                        'description': "一买后的回调确认"
                    })
    
    # 三买/三卖 (基于中枢突破)
    for zhongshu in zhongshus:
        # 寻找突破中枢的笔
        for i, bi in enumerate(bis):
            if bi.direction == 1 and bi.end_price > zhongshu.high:
                # 向上突破中枢
                # 检查回踩
                if i + 1 < len(bis) and bis[i+1].direction == -1:
                    if bis[i+1].low > zhongshu.high:
                        points.append({
                            'type': BuySellPoint.BUY_3.value,
                            'price': bis[i+1].low,
                            'confidence': 0.7,
                            'description': f"突破中枢后回踩确认，中枢区间 [{zhongshu.low:.2f}, {zhongshu.high:.2f}]"
                        })
            elif bi.direction == -1 and bi.end_price < zhongshu.low:
                # 向下跌破中枢
                if i + 1 < len(bis) and bis[i+1].direction == 1:
                    if bis[i+1].high < zhongshu.low:
                        points.append({
                            'type': BuySellPoint.SELL_3.value,
                            'price': bis[i+1].high,
                            'confidence': 0.7,
                            'description': f"跌破中枢后反弹确认，中枢区间 [{zhongshu.low:.2f}, {zhongshu.high:.2f}]"
                        })
    
    return points


def analyze_trend(bis: List[Bi]) -> Tuple[str, str]:
    """分析当前趋势"""
    if len(bis) < 2:
        return "未知", "数据不足"
    
    recent_bis = bis[-3:] if len(bis) >= 3 else bis
    
    # 判断趋势
    highs = [b.high for b in recent_bis[::2]]
    lows = [b.low for b in recent_bis[::2]]
    
    if len(highs) >= 2 and len(lows) >= 2:
        if highs[-1] > highs[0] and lows[-1] > lows[0]:
            trend = "上涨"
            desc = "高点抬高，低点抬高"
        elif highs[-1] < highs[0] and lows[-1] < lows[0]:
            trend = "下跌"
            desc = "高点降低，低点降低"
        else:
            trend = "盘整"
            desc = "高低点交错，无明确方向"
    else:
        trend = "盘整"
        desc = "笔数不足，趋势不明"
    
    return trend, desc


def generate_chanlun_report(df: pd.DataFrame, include_candlestick: bool = False) -> Dict:
    """生成缠论分析报告"""
    result = {
        'fractals': [],
        'bis': [],
        'duans': [],
        'zhongshus': [],
        'beichis': [],
        'buy_sell_points': [],
        'trend': '',
        'trend_desc': '',
        'current_position': '',
        'recommendation': '',
        'candlestick_patterns': []
    }
    
    # 蜡烛图分析
    if include_candlestick:
        try:
            from candlestick import identify_all_patterns
            patterns = identify_all_patterns(df, lookback=20)
            result['candlestick_patterns'] = [
                {
                    'type': p.pattern_type.value,
                    'date': p.date,
                    'price': p.price,
                    'signal': '看涨' if p.signal == 1 else '看跌' if p.signal == -1 else '中性',
                    'strength': p.strength,
                    'description': p.description
                }
                for p in patterns[-5:]
            ]
        except Exception as e:
            result['candlestick_error'] = str(e)
    
    # 1. 识别分型
    fractals = find_fractals(df)
    fractals = filter_fractals(fractals)
    result['fractals'] = [
        {
            'type': f.fractal_type.value,
            'price': f.price,
            'high': f.high,
            'low': f.low,
            'index': f.index,
            'date': f.date
        }
        for f in fractals[-10:]  # 只显示最近 10 个
    ]
    
    # 2. 形成笔
    bis = form_bis(fractals, df)
    result['bis'] = [
        {
            'direction': '↑' if b.direction == 1 else '↓',
            'start_price': round(b.start_price, 2),
            'end_price': round(b.end_price, 2),
            'high': round(b.high, 2),
            'low': round(b.low, 2),
            'start_date': b.start_date,
            'end_date': b.end_date
        }
        for b in bis[-10:]
    ]
    
    # 3. 形成线段
    duans = form_duan(bis)
    result['duans'] = [
        {
            'direction': '↑' if d.direction == 1 else '↓',
            'start_price': round(d.start_price, 2),
            'end_price': round(d.end_price, 2),
            'bi_count': len(d.bis)
        }
        for d in duans[-5:]
    ]
    
    # 4. 识别中枢
    zhongshus = find_zhongshu(bis)
    result['zhongshus'] = [
        {
            'high': round(z.high, 2),
            'low': round(z.low, 2),
            'start_price': round(z.start_price, 2),
            'end_price': round(z.end_price, 2),
            'level': z.level
        }
        for z in zhongshus[-5:]
    ]
    
    # 5. 识别背驰
    beichis = find_beichi(bis, df)
    result['beichis'] = [
        {
            'type': b.beichi_type,
            'price_low': round(b.price_low, 2),
            'price_high': round(b.price_high, 2),
            'strength': round(b.strength, 2)
        }
        for b in beichis[-5:]
    ]
    
    # 6. 识别买卖点
    points = find_buy_sell_points(bis, zhongshus, beichis)
    result['buy_sell_points'] = points
    
    # 7. 趋势分析
    trend, trend_desc = analyze_trend(bis)
    result['trend'] = trend
    result['trend_desc'] = trend_desc
    
    # 8. 当前位置判断
    if len(bis) > 0:
        last_bi = bis[-1]
        current_price = df.iloc[-1]['收盘']
        
        if last_bi.direction == 1:
            result['current_position'] = f"向上笔中，当前价格 {current_price:.2f}"
        else:
            result['current_position'] = f"向下笔中，当前价格 {current_price:.2f}"
        
        # 结合中枢判断
        if zhongshus:
            last_zs = zhongshus[-1]
            if current_price > last_zs.high:
                result['current_position'] += " (中枢上方)"
            elif current_price < last_zs.low:
                result['current_position'] += " (中枢下方)"
            else:
                result['current_position'] += " (中枢内)"
    
    # 9. 综合建议
    if points:
        latest_point = points[-1]
        if '买' in latest_point['type']:
            result['recommendation'] = f"缠论信号：{latest_point['type']} - {latest_point['description']}"
        else:
            result['recommendation'] = f"缠论信号：{latest_point['type']} - {latest_point['description']}"
    else:
        if trend == "上涨":
            result['recommendation'] = "趋势向上，持股待涨"
        elif trend == "下跌":
            result['recommendation'] = "趋势向下，谨慎观望"
        else:
            result['recommendation'] = "盘整走势，等待方向选择"
    
    return result


def print_chanlun_report(report: Dict):
    """打印缠论分析报告"""
    print("\n" + "="*70)
    print("缠论技术分析报告")
    print("="*70)
    
    print(f"\n【趋势判断】{report['trend']} - {report['trend_desc']}")
    print(f"【当前位置】{report['current_position']}")
    
    print("\n【笔分析】")
    if report['bis']:
        for i, bi in enumerate(report['bis'][-5:], 1):
            print(f"  {i}. {bi['direction']} {bi['start_price']} → {bi['end_price']} "
                  f"(高:{bi['high']}, 低:{bi['low']})")
    else:
        print("  数据不足，无法形成笔")
    
    print("\n【中枢】")
    if report['zhongshus']:
        for i, zs in enumerate(report['zhongshus'][-3:], 1):
            print(f"  {i}. 区间 [{zs['low']}, {zs['high']}] "
                  f"级别:{zs['level']}")
    else:
        print("  未识别到明显中枢")
    
    print("\n【背驰】")
    if report['beichis']:
        for bc in report['beichis'][-3:]:
            print(f"  • {bc['type']}: 价格 {bc['price_low']}-{bc['price_high']} "
                  f"强度:{bc['strength']}")
    else:
        print("  未识别到背驰")
    
    print("\n【买卖点】")
    if report['buy_sell_points']:
        for pt in report['buy_sell_points'][-5:]:
            print(f"  ⭐ {pt['type']}: {pt['description']} (置信度:{pt['confidence']:.1f})")
    else:
        print("  暂无明确买卖点")
    
    print(f"\n【缠论建议】{report['recommendation']}")
    print("="*70 + "\n")
