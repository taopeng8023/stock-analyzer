"""
技术分析模块
计算各种技术指标并给出评分
"""

import pandas as pd
import numpy as np


class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self):
        pass
    
    def calculate_ma(self, df: pd.DataFrame, periods: list = [5, 10, 20, 60]) -> dict:
        """计算移动平均线"""
        result = {}
        for period in periods:
            result[f'ma{period}'] = df['close'].rolling(window=period).mean().iloc[-1]
        return result
    
    def calculate_macd(self, df: pd.DataFrame) -> dict:
        """计算 MACD 指标"""
        close = df['close']
        
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = (dif - dea) * 2
        
        return {
            'dif': dif.iloc[-1],
            'dea': dea.iloc[-1],
            'macd': macd.iloc[-1],
            'golden_cross': dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2],
        }
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算 RSI 指标"""
        close = df['close']
        delta = close.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def calculate_kdj(self, df: pd.DataFrame) -> dict:
        """计算 KDJ 指标"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        lowest_low = low.rolling(window=9).min()
        highest_high = high.rolling(window=9).max()
        
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return {
            'k': k.iloc[-1],
            'd': d.iloc[-1],
            'j': j.iloc[-1],
            'golden_cross': k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2],
        }
    
    def calculate_volume_analysis(self, df: pd.DataFrame) -> dict:
        """成交量分析"""
        volume = df['volume']
        
        ma5_volume = volume.rolling(window=5).mean()
        ma20_volume = volume.rolling(window=20).mean()
        
        volume_ratio = ma5_volume.iloc[-1] / ma20_volume.iloc[-1] if ma20_volume.iloc[-1] > 0 else 1
        
        return {
            'volume_ratio': volume_ratio,
            'volume_trend': '放大' if volume_ratio > 1.2 else ('萎缩' if volume_ratio < 0.8 else '平稳'),
        }
    
    def calculate_bollinger(self, df: pd.DataFrame, period: int = 20) -> dict:
        """计算布林带"""
        close = df['close']
        
        ma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper = ma + 2 * std
        lower = ma - 2 * std
        
        current_price = close.iloc[-1]
        
        return {
            'upper': upper.iloc[-1],
            'middle': ma.iloc[-1],
            'lower': lower.iloc[-1],
            'position': '上轨' if current_price > upper.iloc[-1] else ('下轨' if current_price < lower.iloc[-1] else '中轨'),
            'bandwidth': (upper.iloc[-1] - lower.iloc[-1]) / ma.iloc[-1] * 100,
        }
    
    def calculate_trend_strength(self, df: pd.DataFrame) -> dict:
        """趋势强度分析"""
        close = df['close']
        
        # 计算各周期涨幅
        change_5d = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100 if len(close) >= 5 else 0
        change_10d = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100 if len(close) >= 10 else 0
        change_20d = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100 if len(close) >= 20 else 0
        
        # 判断趋势
        if change_5d > 0 and change_10d > 0 and change_20d > 0:
            trend = '强势上涨'
        elif change_5d > 0 and change_10d > 0:
            trend = '上涨'
        elif change_5d > 0:
            trend = '短期反弹'
        elif change_5d < 0 and change_10d < 0 and change_20d < 0:
            trend = '强势下跌'
        elif change_5d < 0 and change_10d < 0:
            trend = '下跌'
        else:
            trend = '震荡'
        
        return {
            'change_5d': change_5d,
            'change_10d': change_10d,
            'change_20d': change_20d,
            'trend': trend,
        }
    
    def get_technical_score(self, df: pd.DataFrame) -> dict:
        """综合技术评分"""
        if len(df) < 30:
            return {'score': 50, 'signals': ['数据不足']}
        
        score = 50
        signals = []
        
        # MA 分析
        ma = self.calculate_ma(df)
        current_price = df['close'].iloc[-1]
        
        if current_price > ma['ma60']:
            score += 10
            signals.append('✓ 股价在 60 日均线上方')
        else:
            score -= 10
            signals.append('✗ 股价在 60 日均线下方')
        
        if current_price > ma['ma20'] > ma['ma60']:
            score += 5
            signals.append('✓ 均线多头排列')
        
        # MACD 分析
        macd = self.calculate_macd(df)
        if macd['golden_cross']:
            score += 10
            signals.append('✓ MACD 金叉')
        elif macd['dif'] > 0 and macd['dea'] > 0:
            score += 5
            signals.append('✓ MACD 零轴上方')
        else:
            score -= 5
            signals.append('✗ MACD 弱势')
        
        # RSI 分析
        rsi = self.calculate_rsi(df)
        if 40 <= rsi <= 70:
            score += 5
            signals.append(f'✓ RSI 中性 ({rsi:.1f})')
        elif rsi < 30:
            score += 10
            signals.append(f'✓ RSI 超卖 ({rsi:.1f})')
        elif rsi > 80:
            score -= 10
            signals.append(f'✗ RSI 超买 ({rsi:.1f})')
        else:
            signals.append(f'~ RSI ({rsi:.1f})')
        
        # 成交量分析
        volume = self.calculate_volume_analysis(df)
        if volume['volume_ratio'] > 1.5:
            score += 10
            signals.append(f"✓ 成交量放大 ({volume['volume_ratio']:.2f}倍)")
        elif volume['volume_ratio'] > 1.2:
            score += 5
            signals.append(f"✓ 成交量温和放大 ({volume['volume_ratio']:.2f}倍)")
        elif volume['volume_ratio'] < 0.7:
            score -= 5
            signals.append(f"✗ 成交量萎缩 ({volume['volume_ratio']:.2f}倍)")
        
        # 趋势分析
        trend = self.calculate_trend_strength(df)
        if trend['trend'] in ['强势上涨', '上涨']:
            score += 10
            signals.append(f"✓ 趋势：{trend['trend']}")
        elif trend['trend'] in ['下跌', '强势下跌']:
            score -= 10
            signals.append(f"✗ 趋势：{trend['trend']}")
        else:
            signals.append(f"~ 趋势：{trend['trend']}")
        
        # KDJ 分析
        kdj = self.calculate_kdj(df)
        if kdj['golden_cross']:
            score += 5
            signals.append('✓ KDJ 金叉')
        
        # 布林带分析
        boll = self.calculate_bollinger(df)
        if boll['position'] == '下轨':
            score += 5
            signals.append('✓ 股价接近布林下轨')
        elif boll['position'] == '上轨':
            score -= 5
            signals.append('✗ 股价接近布林上轨')
        
        # 限制分数范围
        score = max(0, min(100, score))
        
        return {
            'score': score,
            'signals': signals,
            'indicators': {
                'rsi': rsi,
                'macd': macd,
                'kdj': kdj,
                'volume_ratio': volume['volume_ratio'],
                'trend': trend,
                'bollinger': boll,
            }
        }


# 测试用
if __name__ == "__main__":
    import akshare as ak
    
    analyzer = TechnicalAnalyzer()
    
    # 获取测试数据
    df = ak.stock_zh_a_hist(symbol="603659", period="daily", adjust="qfq")
    if not df.empty:
        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 
                     'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
        
        result = analyzer.get_technical_score(df)
        print(f"技术评分：{result['score']}")
        for signal in result['signals']:
            print(signal)
