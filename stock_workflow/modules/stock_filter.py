#!/usr/bin/env python3
"""
股票筛选模块 - v1.0
目标：建立高质量初始股票池，排除无效标的，聚焦短期资金活跃标的
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import sys
sys.path.append('..')

from config.loader import Config


class StockFilter:
    """股票筛选器"""
    
    def __init__(self, config: Config = None):
        """
        初始化股票筛选器
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        self.main_board_prefix = self.config.get('STOCK_FILTER', 'main_board_prefix').split(',')
        self.exclude_prefix = self.config.get('STOCK_FILTER', 'exclude_prefix').split(',')
        self.min_listing_days = int(self.config.get('STOCK_FILTER', 'min_listing_days'))
        self.min_turnover = float(self.config.get('STOCK_FILTER', 'min_turnover')) * 10000  # 转为元
        self.volume_amplify_ratio = float(self.config.get('STOCK_FILTER', 'volume_amplify_ratio'))
        self.volume_ma_period = int(self.config.get('STOCK_FILTER', 'volume_ma_period'))
    
    def filter_main_board(self, stock_list: pd.DataFrame) -> pd.DataFrame:
        """
        筛选主板股票
        
        Args:
            stock_list: 股票列表 DataFrame（包含 code, name, status, list_date）
        
        Returns:
            筛选后的 DataFrame
        """
        filtered = stock_list.copy()
        
        # 保留主板股票（60/00 开头）
        prefix_condition = filtered['code'].str.startswith(tuple(self.main_board_prefix))
        filtered = filtered[prefix_condition]
        
        # 排除创业板、科创板、B 股等
        exclude_condition = ~filtered['code'].str.startswith(tuple(self.exclude_prefix))
        filtered = filtered[exclude_condition]
        
        # 保留正常交易状态
        if 'status' in filtered.columns:
            filtered = filtered[filtered['status'] == '正常交易']
        
        # 排除上市不满指定天数的次新股
        if 'list_date' in filtered.columns:
            cutoff_date = datetime.now() - timedelta(days=self.min_listing_days * 1.5)  # 考虑交易日
            filtered['list_date'] = pd.to_datetime(filtered['list_date'])
            filtered = filtered[filtered['list_date'] < cutoff_date]
        
        return filtered
    
    def filter_st_stocks(self, stock_list: pd.DataFrame) -> pd.DataFrame:
        """
        剔除 ST、*ST、退市整理及停牌股票
        
        Args:
            stock_list: 股票列表 DataFrame
        
        Returns:
            筛选后的 DataFrame
        """
        filtered = stock_list.copy()
        
        # 剔除 ST、*ST 股票
        name_condition = ~filtered['name'].str.contains('ST|退|停牌', na=False)
        filtered = filtered[name_condition]
        
        return filtered
    
    def filter_turnover(self, stock_list: pd.DataFrame, turnover_data: pd.DataFrame) -> pd.DataFrame:
        """
        剔除当日成交额低于门槛的股票
        
        Args:
            stock_list: 股票列表 DataFrame
            turnover_data: 成交额数据 DataFrame（包含 code, turnover）
        
        Returns:
            筛选后的 DataFrame
        """
        filtered = stock_list.copy()
        
        # 合并成交额数据
        merged = filtered.merge(turnover_data, on='code', how='left')
        
        # 剔除成交额低于门槛的股票
        filtered = merged[merged['turnover'] >= self.min_turnover]
        
        return filtered[['code', 'name']]
    
    def filter_volume_amplify(self, stock_list: pd.DataFrame, volume_data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        成交量放大筛选：T 日成交量 > 1.5 × 5 日均量
        
        Args:
            stock_list: 股票列表 DataFrame
            volume_data: 成交量数据 DataFrame（包含 code, vol_t, vol_t1, vol_t2, vol_t3, vol_t4）
        
        Returns:
            (筛选后的 DataFrame, 统计信息 Dict)
        """
        filtered = stock_list.copy()
        
        # 计算 5 日均量
        volume_data['volume_ma5'] = (
            volume_data['vol_t'] + 
            volume_data['vol_t1'] + 
            volume_data['vol_t2'] + 
            volume_data['vol_t3'] + 
            volume_data['vol_t4']
        ) / 5
        
        # 计算成交量放大倍数
        volume_data['volume_ratio'] = volume_data['vol_t'] / (volume_data['volume_ma5'] + 1)
        
        # 筛选成交量放大的股票
        volume_condition = volume_data['volume_ratio'] > self.volume_amplify_ratio
        amplified_stocks = volume_data[volume_condition][['code', 'volume_ratio']]
        
        # 合并筛选结果
        filtered = filtered.merge(amplified_stocks, on='code', how='inner')
        
        # 统计信息
        stats = {
            'total_before': len(stock_list),
            'total_after': len(filtered),
            'filter_rate': 1 - len(filtered) / len(stock_list) if len(stock_list) > 0 else 0,
            'avg_volume_ratio': filtered['volume_ratio'].mean() if len(filtered) > 0 else 0,
            'max_volume_ratio': filtered['volume_ratio'].max() if len(filtered) > 0 else 0,
        }
        
        return filtered[['code', 'name', 'volume_ratio']], stats
    
    def run(self, stock_list: pd.DataFrame, volume_data: pd.DataFrame, turnover_data: pd.DataFrame = None) -> Dict:
        """
        运行完整的股票筛选流程
        
        Args:
            stock_list: 股票列表 DataFrame（code, name, status, list_date）
            volume_data: 成交量数据 DataFrame
            turnover_data: 成交额数据 DataFrame（可选）
        
        Returns:
            筛选结果 Dict {
                'stock_pool': DataFrame（code, name, volume_ratio）,
                'stats': Dict（各阶段统计信息）,
                'quality_score': float（0-100）
            }
        """
        stats = {}
        
        # 阶段 1：主板筛选
        print(f"[股票筛选] 初始股票数：{len(stock_list)}")
        filtered = self.filter_main_board(stock_list)
        stats['main_board'] = {
            'before': len(stock_list),
            'after': len(filtered),
            'filtered': len(stock_list) - len(filtered)
        }
        print(f"[股票筛选] 主板筛选后：{len(filtered)}只")
        
        # 阶段 2：剔除 ST 等异常股票
        filtered = self.filter_st_stocks(filtered)
        stats['st_filter'] = {
            'before': stats['main_board']['after'],
            'after': len(filtered),
            'filtered': stats['main_board']['after'] - len(filtered)
        }
        print(f"[股票筛选] ST 剔除后：{len(filtered)}只")
        
        # 阶段 3：成交额筛选（如果有数据）
        if turnover_data is not None:
            filtered = self.filter_turnover(filtered, turnover_data)
            stats['turnover_filter'] = {
                'before': stats['st_filter']['after'],
                'after': len(filtered),
                'filtered': stats['st_filter']['after'] - len(filtered)
            }
            print(f"[股票筛选] 成交额筛选后：{len(filtered)}只")
        
        # 阶段 4：成交量放大筛选
        filtered, volume_stats = self.filter_volume_amplify(filtered, volume_data)
        stats['volume_filter'] = volume_stats
        print(f"[股票筛选] 成交量放大筛选后：{len(filtered)}只")
        
        # 计算质量评分
        quality_score = self._calculate_quality_score(stats)
        
        return {
            'stock_pool': filtered,
            'stats': stats,
            'quality_score': quality_score
        }
    
    def _calculate_quality_score(self, stats: Dict) -> float:
        """
        计算筛选质量评分
        
        Args:
            stats: 各阶段统计信息
        
        Returns:
            质量评分（0-100）
        """
        score = 100.0
        
        # 成交量放大筛选率过低，扣分
        if 'volume_filter' in stats:
            filter_rate = stats['volume_filter'].get('filter_rate', 0)
            if filter_rate < 0.3:  # 筛选率低于 30%
                score -= (0.3 - filter_rate) * 50
        
        # 平均成交量放大倍数过低，扣分
        if 'volume_filter' in stats:
            avg_ratio = stats['volume_filter'].get('avg_volume_ratio', 0)
            if avg_ratio < 1.8:
                score -= (1.8 - avg_ratio) * 20
        
        return max(0, min(100, score))


# 测试
if __name__ == '__main__':
    # 创建测试数据
    test_stocks = pd.DataFrame({
        'code': ['600519', '000858', '300750', '688981', '600036', '000002'],
        'name': ['贵州茅台', '五粮液', '宁德时代', '中芯国际', '招商银行', '万科 A'],
        'status': ['正常交易'] * 6,
        'list_date': ['2001-08-27'] * 6
    })
    
    test_volume = pd.DataFrame({
        'code': ['600519', '000858', '600036', '000002'],
        'vol_t': [10000, 8000, 15000, 5000],
        'vol_t1': [5000, 5000, 6000, 5000],
        'vol_t2': [5000, 5000, 6000, 5000],
        'vol_t3': [5000, 5000, 6000, 5000],
        'vol_t4': [5000, 5000, 6000, 5000],
    })
    
    # 运行筛选
    config = Config()
    filter = StockFilter(config)
    result = filter.run(test_stocks, test_volume)
    
    print("\n" + "="*60)
    print("📊 股票筛选结果")
    print("="*60)
    print(f"候选股票池：{len(result['stock_pool'])}只")
    print(f"质量评分：{result['quality_score']:.1f}")
    print("\n股票列表:")
    print(result['stock_pool'])
