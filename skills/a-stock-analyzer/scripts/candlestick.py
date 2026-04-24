#!/usr/bin/env python3
"""
蜡烛图形态识别模块
识别经典 K 线形态，与缠论分析结合使用
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class CandleType(Enum):
    """蜡烛类型"""
    BIG_YANG = "大阳线"
    BIG_YIN = "大阴线"
    SMALL_YANG = "小阳线"
    SMALL_YIN = "小阴线"
    DOJI = "十字星"
    HAMMER = "锤头线"
    HANGING_MAN = "上吊线"
    INVERTED_HAMMER = "倒锤头线"
    SHOOTING_STAR = "射击之星"


class PatternType(Enum):
    """形态类型"""
    # 单根
    DOJI = "十字星"
    HAMMER = "锤头线"
    HANGING_MAN = "上吊线"
    SHOOTING_STAR = "射击之星"
    INVERTED_HAMMER = "倒锤头线"
    
    # 双根
    BULLISH_ENGULFING = "看涨吞没"
    BEARISH_ENGULFING = "看跌吞没"
    BULLISH_HARAMI = "看涨孕线"
    BEARISH_HARAMI = "看跌孕线"
    DARK_CLOUD_COVER = "乌云盖顶"
    PIERCING_LINE = "刺透形态"
    
    # 三根
    MORNING_STAR = "早晨之星"
    EVENING_STAR = "黄昏之星"
    THREE_WHITE_SOLDIERS = "红三兵"
    THREE_BLACK_CROWS = "三只乌鸦"


@dataclass
class CandlePattern:
    """蜡烛形态"""
    pattern_type: PatternType
    index: int
    date: str
    price: float
    signal: int  # 1: 看涨，-1: 看跌
    strength: float  # 0-1，信号强度
    description: str


def is_yang(open_price: float, close: float) -> bool:
    """是否阳线"""
    return close > open_price


def is_yin(open_price: float, close: float) -> bool:
    """是否阴线"""
    return close < open_price


def body_size(open_price: float, close: float) -> float:
    """实体大小"""
    return abs(close - open_price)


def upper_shadow(high: float, open_price: float, close: float) -> float:
    """上影线长度"""
    return high - max(open_price, close)


def lower_shadow(low: float, open_price: float, close: float) -> float:
    """下影线长度"""
    return min(open_price, close) - low


def avg_body(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """计算平均实体大小"""
    bodies = abs(df['收盘'] - df['开盘'])
    return bodies.rolling(window=period, min_periods=5).mean()


def identify_single_candle(df: pd.DataFrame, index: int) -> Optional[CandlePattern]:
    """识别单根蜡烛形态"""
    if index >= len(df):
        return None
    
    row = df.iloc[index]
    open_p = row['开盘']
    close = row['收盘']
    high = row['最高']
    low = row['最低']
    
    body = body_size(open_p, close)
    upper = upper_shadow(high, open_p, close)
    lower = lower_shadow(low, open_p, close)
    
    # 获取平均实体用于比较
    avg_body_val = avg_body(df, 20).iloc[index] if index >= 20 else body * 1.5
    if pd.isna(avg_body_val):
        avg_body_val = body * 1.5
    
    yang = is_yang(open_p, close)
    
    # 十字星 (实体非常小)
    if body < avg_body_val * 0.1:
        return CandlePattern(
            pattern_type=PatternType.DOJI,
            index=index,
            date=str(row.get('日期', index)),
            price=close,
            signal=0,
            strength=0.5,
            description="十字星 - 市场犹豫，变盘信号"
        )
    
    # 锤头线 (下跌趋势中，长下影)
    if (lower > body * 2 and 
        upper < body * 0.5 and 
        index > 5 and 
        df.iloc[index-5:index]['收盘'].mean() > close):
        return CandlePattern(
            pattern_type=PatternType.HAMMER,
            index=index,
            date=str(row.get('日期', index)),
            price=close,
            signal=1,
            strength=0.7,
            description="锤头线 - 下跌动能衰竭，看涨信号"
        )
    
    # 上吊线 (上涨趋势中，长下影)
    if (lower > body * 2 and 
        upper < body * 0.5 and 
        index > 5 and 
        df.iloc[index-5:index]['收盘'].mean() < close):
        return CandlePattern(
            pattern_type=PatternType.HANGING_MAN,
            index=index,
            date=str(row.get('日期', index)),
            price=close,
            signal=-1,
            strength=0.7,
            description="上吊线 - 上涨动能衰竭，看跌信号"
        )
    
    # 射击之星 (上涨趋势中，长上影)
    if (upper > body * 2 and 
        lower < body * 0.5 and 
        index > 5 and 
        df.iloc[index-5:index]['收盘'].mean() < close):
        return CandlePattern(
            pattern_type=PatternType.SHOOTING_STAR,
            index=index,
            date=str(row.get('日期', index)),
            price=close,
            signal=-1,
            strength=0.7,
            description="射击之星 - 上涨受阻，看跌信号"
        )
    
    # 倒锤头线 (下跌趋势中，长上影)
    if (upper > body * 2 and 
        lower < body * 0.5 and 
        index > 5 and 
        df.iloc[index-5:index]['收盘'].mean() > close):
        return CandlePattern(
            pattern_type=PatternType.INVERTED_HAMMER,
            index=index,
            date=str(row.get('日期', index)),
            price=close,
            signal=1,
            strength=0.6,
            description="倒锤头线 - 下跌动能减弱，看涨信号"
        )
    
    return None


def identify_two_candle_pattern(df: pd.DataFrame, index: int) -> Optional[CandlePattern]:
    """识别双根蜡烛形态"""
    if index < 1 or index >= len(df):
        return None
    
    # 当前 K 线
    curr = df.iloc[index]
    prev = df.iloc[index - 1]
    
    curr_open = curr['开盘']
    curr_close = curr['收盘']
    curr_high = curr['最高']
    curr_low = curr['最低']
    
    prev_open = prev['开盘']
    prev_close = prev['收盘']
    prev_high = prev['最高']
    prev_low = prev['最低']
    
    curr_body = body_size(curr_open, curr_close)
    prev_body = body_size(prev_open, prev_close)
    
    curr_yang = is_yang(curr_open, curr_close)
    prev_yang = is_yang(prev_open, prev_close)
    
    # 看涨吞没
    if (curr_yang and not prev_yang and 
        curr_body > prev_body * 1.5 and
        curr_open < prev_close and 
        curr_close > prev_open):
        return CandlePattern(
            pattern_type=PatternType.BULLISH_ENGULFING,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=1,
            strength=0.8,
            description="看涨吞没 - 强烈反转信号"
        )
    
    # 看跌吞没
    if (not curr_yang and prev_yang and 
        curr_body > prev_body * 1.5 and
        curr_open > prev_close and 
        curr_close < prev_open):
        return CandlePattern(
            pattern_type=PatternType.BEARISH_ENGULFING,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=-1,
            strength=0.8,
            description="看跌吞没 - 强烈反转信号"
        )
    
    # 看涨孕线
    if (curr_yang and not prev_yang and
        curr_open > prev_open and 
        curr_close < prev_open and
        curr_body < prev_body * 0.5):
        return CandlePattern(
            pattern_type=PatternType.BULLISH_HARAMI,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=1,
            strength=0.6,
            description="看涨孕线 - 温和反转信号"
        )
    
    # 看跌孕线
    if (not curr_yang and prev_yang and
        curr_open < prev_open and 
        curr_close > prev_open and
        curr_body < prev_body * 0.5):
        return CandlePattern(
            pattern_type=PatternType.BEARISH_HARAMI,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=-1,
            strength=0.6,
            description="看跌孕线 - 温和反转信号"
        )
    
    # 乌云盖顶
    if (not curr_yang and prev_yang and
        curr_open > prev_high and
        curr_close < prev_open + prev_body * 0.5):
        return CandlePattern(
            pattern_type=PatternType.DARK_CLOUD_COVER,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=-1,
            strength=0.75,
            description="乌云盖顶 - 强烈看跌信号"
        )
    
    # 刺透形态
    if (curr_yang and not prev_yang and
        curr_open < prev_low and
        curr_close > prev_open - prev_body * 0.5):
        return CandlePattern(
            pattern_type=PatternType.PIERCING_LINE,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=1,
            strength=0.75,
            description="刺透形态 - 强烈看涨信号"
        )
    
    return None


def identify_three_candle_pattern(df: pd.DataFrame, index: int) -> Optional[CandlePattern]:
    """识别三根蜡烛形态"""
    if index < 2 or index >= len(df):
        return None
    
    # 当前 K 线
    curr = df.iloc[index]
    mid = df.iloc[index - 1]
    prev = df.iloc[index - 2]
    
    curr_open = curr['开盘']
    curr_close = curr['收盘']
    mid_open = mid['开盘']
    mid_close = mid['收盘']
    prev_open = prev['开盘']
    prev_close = prev['收盘']
    
    curr_yang = is_yang(curr_open, curr_close)
    mid_yang = is_yang(mid_open, mid_close)
    prev_yang = is_yang(prev_open, prev_close)
    
    curr_body = body_size(curr_open, curr_close)
    mid_body = body_size(mid_open, mid_close)
    prev_body = body_size(prev_open, prev_close)
    
    avg_body_val = avg_body(df, 20).iloc[index] if index >= 20 else curr_body
    if pd.isna(avg_body_val):
        avg_body_val = curr_body
    
    # 早晨之星
    if (not prev_yang and  # 第一根阴线
        body_size(mid_open, mid_close) < avg_body_val * 0.3 and  # 第二根小 K/十字
        curr_yang and  # 第三根阳线
        curr_close > prev_open + prev_body * 0.5):  # 深入第一根实体
        return CandlePattern(
            pattern_type=PatternType.MORNING_STAR,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=1,
            strength=0.85,
            description="早晨之星 - 强烈底部反转"
        )
    
    # 黄昏之星
    if (prev_yang and  # 第一根阳线
        body_size(mid_open, mid_close) < avg_body_val * 0.3 and  # 第二根小 K/十字
        not curr_yang and  # 第三根阴线
        curr_close < prev_open - prev_body * 0.5):  # 深入第一根实体
        return CandlePattern(
            pattern_type=PatternType.EVENING_STAR,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=-1,
            strength=0.85,
            description="黄昏之星 - 强烈顶部反转"
        )
    
    # 红三兵
    if (curr_yang and mid_yang and prev_yang and
        curr_close > mid_close and 
        mid_close > prev_close and
        curr_body > avg_body_val * 0.8 and
        mid_body > avg_body_val * 0.8 and
        prev_body > avg_body_val * 0.8):
        return CandlePattern(
            pattern_type=PatternType.THREE_WHITE_SOLDIERS,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=1,
            strength=0.8,
            description="红三兵 - 强烈看涨"
        )
    
    # 三只乌鸦
    if (not curr_yang and not mid_yang and not prev_yang and
        curr_close < mid_close and 
        mid_close < prev_close and
        curr_body > avg_body_val * 0.8 and
        mid_body > avg_body_val * 0.8 and
        prev_body > avg_body_val * 0.8):
        return CandlePattern(
            pattern_type=PatternType.THREE_BLACK_CROWS,
            index=index,
            date=str(curr.get('日期', index)),
            price=curr_close,
            signal=-1,
            strength=0.8,
            description="三只乌鸦 - 强烈看跌"
        )
    
    return None


def identify_all_patterns(df: pd.DataFrame, lookback: int = 20) -> List[CandlePattern]:
    """识别所有蜡烛形态"""
    patterns = []
    
    start_idx = max(0, len(df) - lookback)
    
    for i in range(start_idx, len(df)):
        # 单根形态
        single = identify_single_candle(df, i)
        if single:
            patterns.append(single)
        
        # 双根形态
        double = identify_two_candle_pattern(df, i)
        if double:
            patterns.append(double)
        
        # 三根形态
        triple = identify_three_candle_pattern(df, i)
        if triple:
            patterns.append(triple)
    
    return patterns


def get_latest_pattern(df: pd.DataFrame) -> Optional[CandlePattern]:
    """获取最新的蜡烛形态"""
    patterns = identify_all_patterns(df, lookback=5)
    if patterns:
        return max(patterns, key=lambda p: p.index)
    return None


def print_patterns(patterns: List[CandlePattern]):
    """打印蜡烛形态"""
    if not patterns:
        print("未识别到蜡烛形态")
        return
    
    print("\n" + "="*70)
    print("蜡烛图形态识别")
    print("="*70)
    
    # 按信号强度排序
    sorted_patterns = sorted(patterns, key=lambda p: p.strength, reverse=True)
    
    for i, p in enumerate(sorted_patterns[:10], 1):
        signal_icon = "📈" if p.signal == 1 else "📉" if p.signal == -1 else "➖"
        print(f"{i}. {signal_icon} {p.pattern_type.value}")
        print(f"   日期：{p.date}  价格：{p.price:.2f}")
        print(f"   强度：{p.strength:.2f}")
        print(f"   {p.description}")
        print()
    
    print("="*70)


def combine_with_chanlun(chanlun_report: Dict, patterns: List[CandlePattern]) -> Dict:
    """将蜡烛形态与缠论分析结合"""
    result = {
        'chanlun': chanlun_report,
        'candle_patterns': [
            {
                'type': p.pattern_type.value,
                'date': p.date,
                'price': p.price,
                'signal': '看涨' if p.signal == 1 else '看跌' if p.signal == -1 else '中性',
                'strength': p.strength,
                'description': p.description
            }
            for p in patterns[-5:]  # 最近 5 个
        ],
        'combined_signal': None,
        'combined_description': ''
    }
    
    # 结合判断
    if not patterns:
        result['combined_signal'] = chanlun_report.get('recommendation', '观望')
        result['combined_description'] = '无蜡烛形态信号，以缠论分析为准'
        return result
    
    # 获取最强蜡烛信号
    latest_pattern = max(patterns, key=lambda p: p.strength)
    
    # 获取缠论趋势
    chanlun_trend = chanlun_report.get('trend', '盘整')
    chanlun_rec = chanlun_report.get('recommendation', '观望')
    
    # 结合判断
    if latest_pattern.signal == 1:  # 蜡烛看涨
        if chanlun_trend == '上涨' or '买' in chanlun_rec:
            result['combined_signal'] = '强烈买入'
            result['combined_description'] = f'缠论{chanlun_rec} + 蜡烛{latest_pattern.pattern_type.value}，双重确认'
        else:
            result['combined_signal'] = '谨慎买入'
            result['combined_description'] = f'蜡烛{latest_pattern.pattern_type.value}看涨，但缠论趋势不明'
    
    elif latest_pattern.signal == -1:  # 蜡烛看跌
        if chanlun_trend == '下跌' or '卖' in chanlun_rec:
            result['combined_signal'] = '强烈卖出'
            result['combined_description'] = f'缠论{chanlun_rec} + 蜡烛{latest_pattern.pattern_type.value}，双重确认'
        else:
            result['combined_signal'] = '谨慎卖出'
            result['combined_description'] = f'蜡烛{latest_pattern.pattern_type.value}看跌，但缠论趋势不明'
    
    else:  # 蜡烛中性
        result['combined_signal'] = chanlun_rec
        result['combined_description'] = f'蜡烛十字星观望，以缠论{chanlun_rec}为主'
    
    return result
