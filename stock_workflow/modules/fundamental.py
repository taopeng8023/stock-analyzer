#!/usr/bin/env python3
"""
基本面分析模块 - v1.0
目标：提取关键财务指标，评估企业内在价值
"""

import pandas as pd
import numpy as np
from typing import List, Dict
import sys
sys.path.append('..')

from config.loader import Config


class FundamentalAnalyzer:
    """基本面分析器"""
    
    def __init__(self, config: Config = None):
        """
        初始化基本面分析器
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        
        # 核心财务指标
        self.core_indicators = [
            'pe_ttm',           # 市盈率（TTM）
            'pb',               # 市净率
            'roe',              # 净资产收益率
            'revenue_growth',   # 营业收入同比增长率
            'debt_to_assets',   # 资产负债率
            'eps',              # 每股收益
        ]
    
    def get_fundamental_data(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取基本面数据
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            DataFrame（code, pe_ttm, pb, roe, revenue_growth, debt_to_assets, eps）
        """
        # TODO: 接入 Tushare API 获取真实数据
        # 这里使用模拟数据
        data = []
        for code in stock_codes:
            data.append({
                'code': code,
                'pe_ttm': np.random.uniform(10, 50),
                'pb': np.random.uniform(1, 10),
                'roe': np.random.uniform(5, 30),
                'revenue_growth': np.random.uniform(-20, 50),
                'debt_to_assets': np.random.uniform(20, 80),
                'eps': np.random.uniform(0.5, 5),
            })
        
        return pd.DataFrame(data)
    
    def handle_outliers(self, df: pd.DataFrame, columns: List[str] = None) -> pd.DataFrame:
        """
        处理异常值（分位数法）
        
        Args:
            df: 数据 DataFrame
            columns: 需要处理的列
        
        Returns:
            处理后的 DataFrame
        """
        if columns is None:
            columns = self.core_indicators
        
        df = df.copy()
        
        for col in columns:
            if col not in df.columns:
                continue
            
            # 计算 1% 和 99% 分位数
            low = df[col].quantile(0.01)
            high = df[col].quantile(0.99)
            
            # 截断异常值
            df[col] = df[col].clip(low, high)
        
        return df
    
    def standardize(self, df: pd.DataFrame, by_industry: bool = False) -> pd.DataFrame:
        """
        标准化处理（Z-score）
        
        Args:
            df: 数据 DataFrame
            by_industry: 是否按行业分组标准化
        
        Returns:
            标准化后的 DataFrame
        """
        df = df.copy()
        
        for col in self.core_indicators:
            if col not in df.columns:
                continue
            
            if by_industry and 'industry' in df.columns:
                # 按行业分组标准化
                df[f'{col}_zscore'] = df.groupby('industry')[col].transform(
                    lambda x: (x - x.mean()) / (x.std() + 1e-6)
                )
            else:
                # 全局标准化
                mean = df[col].mean()
                std = df[col].std()
                df[f'{col}_zscore'] = (df[col] - mean) / (std + 1e-6)
        
        return df
    
    def calculate_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算衍生特征
        
        Args:
            df: 数据 DataFrame
        
        Returns:
            包含衍生特征的 DataFrame
        """
        df = df.copy()
        
        # 估值综合评分（PE 和 PB 的负向指标，越低越好）
        if 'pe_ttm_zscore' in df.columns and 'pb_zscore' in df.columns:
            df['valuation_score'] = -(df['pe_ttm_zscore'] + df['pb_zscore']) / 2
        
        # 盈利能力评分（ROE 和 EPS 的正向指标，越高越好）
        if 'roe_zscore' in df.columns and 'eps_zscore' in df.columns:
            df['profitability_score'] = (df['roe_zscore'] + df['eps_zscore']) / 2
        
        # 成长性评分
        if 'revenue_growth_zscore' in df.columns:
            df['growth_score'] = df['revenue_growth_zscore']
        
        # 财务健康评分（负债率负向指标）
        if 'debt_to_assets_zscore' in df.columns:
            df['health_score'] = -df['debt_to_assets_zscore']
        
        # 综合基本面评分
        score_cols = ['valuation_score', 'profitability_score', 'growth_score', 'health_score']
        available_scores = [c for c in score_cols if c in df.columns]
        if available_scores:
            df['fundamental_score'] = df[available_scores].mean(axis=1)
        
        return df
    
    def run(self, stock_codes: List[str]) -> Dict:
        """
        运行完整的基本面分析流程
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            分析结果 Dict {
                'data': DataFrame（原始数据）,
                'features': DataFrame（特征向量）,
                'quality_score': float（0-100）
            }
        """
        print(f"[基本面分析] 开始分析 {len(stock_codes)} 只股票...")
        
        # 获取原始数据
        data = self.get_fundamental_data(stock_codes)
        print(f"[基本面分析] 获取原始数据完成")
        
        # 处理异常值
        data = self.handle_outliers(data)
        print(f"[基本面分析] 异常值处理完成")
        
        # 标准化
        data = self.standardize(data)
        print(f"[基本面分析] 标准化完成")
        
        # 计算衍生特征
        data = self.calculate_derived_features(data)
        print(f"[基本面分析] 衍生特征计算完成")
        
        # 构建特征向量
        feature_cols = [c for c in data.columns if c.endswith('_zscore') or c.endswith('_score')]
        features = data[['code'] + feature_cols]
        
        # 计算质量评分
        missing_rate = data[self.core_indicators].isnull().mean().mean()
        quality_score = (1 - missing_rate) * 100
        
        print(f"[基本面分析] 完成，质量评分：{quality_score:.1f}")
        
        return {
            'data': data,
            'features': features,
            'quality_score': quality_score
        }


# 测试
if __name__ == '__main__':
    config = Config()
    analyzer = FundamentalAnalyzer(config)
    
    test_codes = ['600519', '000858', '600036', '000002', '000651']
    result = analyzer.run(test_codes)
    
    print("\n" + "="*60)
    print("📊 基本面分析结果")
    print("="*60)
    print(f"分析股票数：{len(result['features'])}")
    print(f"质量评分：{result['quality_score']:.1f}")
    print("\n特征列:")
    print(result['features'].columns.tolist())
    print("\n数据预览:")
    print(result['features'].head())
