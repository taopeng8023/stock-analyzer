#!/usr/bin/env python3
"""
技术分析模块 - v1.0
目标：从历史价格与成交量中提取技术信号，反映短期市场行为
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
import sys
sys.path.append('..')

from config.loader import Config


class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self, config: Config = None):
        """
        初始化技术分析器
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        
        # 技术指标参数
        self.ma_periods = [int(x) for x in self.config.get('TECHNICAL_INDICATORS', 'ma_periods').split(',')]
        self.macd_fast = int(self.config.get('TECHNICAL_INDICATORS', 'macd_fast'))
        self.macd_slow = int(self.config.get('TECHNICAL_INDICATORS', 'macd_slow'))
        self.macd_signal = int(self.config.get('TECHNICAL_INDICATORS', 'macd_signal'))
        self.rsi_period = int(self.config.get('TECHNICAL_INDICATORS', 'rsi_period'))
        self.kdj_period = int(self.config.get('TECHNICAL_INDICATORS', 'kdj_period'))
        self.atr_period = int(self.config.get('TECHNICAL_INDICATORS', 'atr_period'))
        self.bollinger_period = int(self.config.get('TECHNICAL_INDICATORS', 'bollinger_period'))
        
        # 特征筛选相关性阈值
        self.correlation_threshold = float(self.config.get('TECHNICAL_INDICATORS', 'feature_correlation_threshold'))
    
    def get_price_data(self, stock_codes: List[str]) -> Dict[str, pd.DataFrame]:
        """
        获取价格数据
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            Dict{code: DataFrame}（包含 open, high, low, close, volume）
        """
        # TODO: 接入 Tushare API 获取真实数据
        # 这里使用模拟数据
        data_dict = {}
        for code in stock_codes:
            dates = pd.date_range(end=pd.Timestamp.now(), periods=252, freq='D')
            data_dict[code] = pd.DataFrame({
                'date': dates,
                'open': np.random.uniform(50, 200, len(dates)),
                'high': np.random.uniform(50, 200, len(dates)),
                'low': np.random.uniform(50, 200, len(dates)),
                'close': np.random.uniform(50, 200, len(dates)),
                'volume': np.random.uniform(1000000, 10000000, len(dates)),
            })
            data_dict[code].set_index('date', inplace=True)
        
        return data_dict
    
    def calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算移动平均线"""
        df = df.copy()
        for period in self.ma_periods:
            df[f'ma{period}'] = df['close'].rolling(window=period).mean()
        
        # MA5/MA20 比率
        if 'ma5' in df.columns and 'ma20' in df.columns:
            df['ma5_ma20_ratio'] = df['ma5'] / (df['ma20'] + 1e-6)
        
        return df
    
    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 MACD"""
        df = df.copy()
        
        exp1 = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['macd_diff'] = exp1 - exp2
        df['macd_dea'] = df['macd_diff'].ewm(span=self.macd_signal, adjust=False).mean()
        df['macd_hist'] = df['macd_diff'] - df['macd_dea']
        
        # MACD 柱变化
        df['macd_hist_change'] = df['macd_hist'].diff(5)
        
        return df
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 RSI"""
        df = df.copy()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        
        rs = gain / (loss + 1e-6)
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        return df
    
    def calculate_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 KDJ"""
        df = df.copy()
        
        low_min = df['low'].rolling(window=self.kdj_period).min()
        high_max = df['high'].rolling(window=self.kdj_period).max()
        
        rsv = (df['close'] - low_min) / (high_max - low_min + 1e-6) * 100
        df['kdj_k'] = rsv.ewm(com=2).mean()
        df['kdj_d'] = df['kdj_k'].ewm(com=2).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        return df
    
    def calculate_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 OBV"""
        df = df.copy()
        
        direction = np.sign(df['close'].diff())
        df['obv'] = (direction * df['volume']).cumsum()
        
        # OBV 变化率
        df['obv_change'] = df['obv'].pct_change(5)
        
        return df
    
    def calculate_volume_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算成交量变化率"""
        df = df.copy()
        
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ratio'] = df['volume'] / (df['volume_ma5'] + 1e-6)
        
        return df
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 ATR"""
        df = df.copy()
        
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        df['atr_14'] = true_range.rolling(window=self.atr_period).mean()
        df['atr_ratio'] = df['atr_14'] / (df['close'] + 1e-6)
        
        return df
    
    def calculate_bollinger(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算布林带"""
        df = df.copy()
        
        df['bb_middle'] = df['close'].rolling(window=self.bollinger_period).mean()
        std = df['close'].rolling(window=self.bollinger_period).std()
        df['bb_upper'] = df['bb_middle'] + 2 * std
        df['bb_lower'] = df['bb_middle'] - 2 * std
        
        # 带宽百分比
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-6)
        
        # 带宽
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (df['bb_middle'] + 1e-6)
        
        return df
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        df = self.calculate_ma(df)
        df = self.calculate_macd(df)
        df = self.calculate_rsi(df)
        df = self.calculate_kdj(df)
        df = self.calculate_obv(df)
        df = self.calculate_volume_ratio(df)
        df = self.calculate_atr(df)
        df = self.calculate_bollinger(df)
        
        return df
    
    def get_feature_columns(self) -> List[str]:
        """获取特征列名"""
        return [
            'ma5_ma20_ratio',
            'macd_hist',
            'macd_hist_change',
            'rsi_14',
            'kdj_k',
            'kdj_d',
            'kdj_j',
            'obv_change',
            'volume_ratio',
            'atr_ratio',
            'bb_position',
            'bb_width',
        ]
    
    def select_features(self, df: pd.DataFrame, target: pd.Series = None) -> List[str]:
        """
        使用互信息法筛选高相关性特征
        
        Args:
            df: 特征 DataFrame
            target: 目标变量（未来收益）
        
        Returns:
            筛选后的特征列名列表
        """
        feature_cols = self.get_feature_columns()
        available_cols = [c for c in feature_cols if c in df.columns]
        
        if target is None or len(df) < 50:
            # 如果没有目标变量或数据太少，返回所有特征
            return available_cols
        
        # 计算互信息（简化版本，使用相关性代替）
        correlations = []
        for col in available_cols:
            corr = df[col].corr(target)
            correlations.append((col, abs(corr)))
        
        # 筛选相关性>阈值的特征
        selected = [col for col, corr in correlations if corr > self.correlation_threshold]
        
        return selected if selected else available_cols[:5]  # 至少返回 5 个特征
    
    def run(self, stock_codes: List[str]) -> Dict:
        """
        运行完整的技术分析流程
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            分析结果 Dict {
                'features': DataFrame（特征向量）,
                'selected_features': List（筛选后的特征）,
                'quality_score': float（0-100）
            }
        """
        print(f"[技术分析] 开始分析 {len(stock_codes)} 只股票...")
        
        # 获取价格数据
        price_data = self.get_price_data(stock_codes)
        
        # 计算技术指标并提取特征
        all_features = []
        for code, df in price_data.items():
            df = self.calculate_all_indicators(df)
            
            # 取最新一天的特征
            latest = df.iloc[-1].copy()
            latest['code'] = code
            
            all_features.append(latest)
        
        features_df = pd.DataFrame(all_features)
        
        # 特征筛选
        feature_cols = self.get_feature_columns()
        available_cols = [c for c in feature_cols if c in features_df.columns]
        features_df = features_df[['code'] + available_cols]
        
        # 计算质量评分
        missing_rate = features_df[available_cols].isnull().mean().mean()
        quality_score = (1 - missing_rate) * 100
        
        print(f"[技术分析] 完成，特征数：{len(available_cols)}，质量评分：{quality_score:.1f}")
        
        return {
            'features': features_df,
            'selected_features': available_cols,
            'quality_score': quality_score
        }


# 测试
if __name__ == '__main__':
    config = Config()
    analyzer = TechnicalAnalyzer(config)
    
    test_codes = ['600519', '000858', '600036', '000002', '000651']
    result = analyzer.run(test_codes)
    
    print("\n" + "="*60)
    print("📊 技术分析结果")
    print("="*60)
    print(f"分析股票数：{len(result['features'])}")
    print(f"特征数：{len(result['selected_features'])}")
    print(f"质量评分：{result['quality_score']:.1f}")
    print("\n特征列:")
    print(result['selected_features'])
    print("\n数据预览:")
    print(result['features'].head())
