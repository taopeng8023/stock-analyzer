#!/usr/bin/env python3
"""
数据质量监控模块 - v1.0
目标：确保各模块输入数据的可靠性，及时发现并处理异常
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from sklearn.ensemble import IsolationForest
import sys
sys.path.append('..')

from config.loader import Config


class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self, config: Config = None):
        """
        初始化数据质量监控器
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        self.missing_rate_threshold = float(self.config.get('DATA_QUALITY', 'missing_rate_threshold'))
        self.outlier_quantile_low = float(self.config.get('DATA_QUALITY', 'outlier_quantile_low'))
        self.outlier_quantile_high = float(self.config.get('DATA_QUALITY', 'outlier_quantile_high'))
        self.abnormal_rate_threshold = float(self.config.get('DATA_QUALITY', 'abnormal_rate_threshold'))
        self.quality_score_threshold = float(self.config.get('DATA_QUALITY', 'quality_score_threshold'))
    
    def check_completeness(self, df: pd.DataFrame) -> Dict:
        """
        数据完整性检查
        
        Args:
            df: 数据 DataFrame
        
        Returns:
            检查结果 Dict
        """
        missing_rate = df.isnull().mean().mean()
        missing_cols = df.columns[df.isnull().mean() > self.missing_rate_threshold].tolist()
        
        return {
            'missing_rate': missing_rate,
            'missing_cols': missing_cols,
            'passed': missing_rate <= self.missing_rate_threshold,
        }
    
    def check_validity(self, df: pd.DataFrame, rules: Dict = None) -> Dict:
        """
        数据有效性检查
        
        Args:
            df: 数据 DataFrame
            rules: 验证规则 Dict {col: (min, max)}
        
        Returns:
            检查结果 Dict
        """
        if rules is None:
            rules = {
                'pe_ttm': (0, 1000),
                'pb': (0, 100),
                'roe': (-100, 100),
                'volume_ratio': (0, 100),
                'rsi_14': (0, 100),
            }
        
        invalid_records = []
        for col, (min_val, max_val) in rules.items():
            if col not in df.columns:
                continue
            
            invalid = ((df[col] < min_val) | (df[col] > max_val)).sum()
            if invalid > 0:
                invalid_records.append({
                    'column': col,
                    'invalid_count': invalid,
                    'rule': f'{min_val}-{max_val}',
                })
        
        return {
            'invalid_records': invalid_records,
            'total_invalid': sum(r['invalid_count'] for r in invalid_records),
            'passed': len(invalid_records) == 0,
        }
    
    def detect_outliers(self, df: pd.DataFrame, contamination: float = 0.02) -> pd.DataFrame:
        """
        使用 Isolation Forest 检测异常点
        
        Args:
            df: 数据 DataFrame
            contamination: 异常点比例
        
        Returns:
            剔除异常后的 DataFrame
        """
        # 选择数值列
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if 'code' in numeric_cols:
            numeric_cols.remove('code')
        
        if len(numeric_cols) < 2 or len(df) < 10:
            return df
        
        # Isolation Forest 检测
        iso_forest = IsolationForest(contamination=contamination, random_state=42)
        X = df[numeric_cols].fillna(df[numeric_cols].median())
        
        predictions = iso_forest.fit_predict(X)
        
        # -1 表示异常点，1 表示正常点
        df_clean = df[predictions == 1].copy()
        
        return df_clean
    
    def handle_outliers_quantile(self, df: pd.DataFrame, columns: List[str] = None) -> pd.DataFrame:
        """
        使用分位数法处理异常值
        
        Args:
            df: 数据 DataFrame
            columns: 需要处理的列
        
        Returns:
            处理后的 DataFrame
        """
        df = df.copy()
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
            if 'code' in columns:
                columns.remove('code')
        
        for col in columns:
            if col not in df.columns:
                continue
            
            low = df[col].quantile(self.outlier_quantile_low)
            high = df[col].quantile(self.outlier_quantile_high)
            df[col] = df[col].clip(low, high)
        
        return df
    
    def calculate_quality_score(self, completeness: Dict, validity: Dict, outlier_rate: float) -> float:
        """
        计算数据质量评分
        
        Args:
            completeness: 完整性检查结果
            validity: 有效性检查结果
            outlier_rate: 异常点比例
        
        Returns:
            质量评分（0-100）
        """
        score = 100.0
        
        # 完整性扣分
        if not completeness['passed']:
            score -= completeness['missing_rate'] * 100
        
        # 有效性扣分
        if not validity['passed']:
            score -= validity['total_invalid'] * 2
        
        # 异常点扣分
        score -= outlier_rate * 50
        
        return max(0, min(100, score))
    
    def generate_report(self, completeness: Dict, validity: Dict, outlier_rate: float, quality_score: float) -> Dict:
        """
        生成质量评估报告
        
        Args:
            completeness: 完整性检查结果
            validity: 有效性检查结果
            outlier_rate: 异常点比例
            quality_score: 质量评分
        
        Returns:
            质量报告 Dict
        """
        return {
            'quality_score': quality_score,
            'passed': quality_score >= self.quality_score_threshold,
            'completeness': completeness,
            'validity': validity,
            'outlier_rate': outlier_rate,
            'recommendations': self._generate_recommendations(completeness, validity, outlier_rate),
        }
    
    def _generate_recommendations(self, completeness: Dict, validity: Dict, outlier_rate: float) -> List[str]:
        """生成处理建议"""
        recommendations = []
        
        if not completeness['passed']:
            recommendations.append(f"缺失率过高 ({completeness['missing_rate']:.1%})，建议补充数据")
            if completeness['missing_cols']:
                recommendations.append(f"缺失列：{', '.join(completeness['missing_cols'])}")
        
        if not validity['passed']:
            recommendations.append(f"发现 {validity['total_invalid']} 条无效记录，建议检查数据源")
        
        if outlier_rate > self.abnormal_rate_threshold:
            recommendations.append(f"异常率过高 ({outlier_rate:.1%})，建议重新采集数据")
        
        if not recommendations:
            recommendations.append("数据质量良好，无需特殊处理")
        
        return recommendations
    
    def run(self, features_dict: Dict[str, pd.DataFrame]) -> Dict:
        """
        运行完整的数据质量监控流程
        
        Args:
            features_dict: 各模块特征 Dict {module_name: DataFrame}
        
        Returns:
            监控结果 Dict {
                'report': Dict（质量报告）,
                'cleaned_features': DataFrame（清洗后的特征）,
                'passed': bool（是否合格）
            }
        """
        print(f"[数据质量] 开始监控 {len(features_dict)} 个模块的数据...")
        
        # 合并所有特征
        merged = None
        for module_name, df in features_dict.items():
            if 'code' not in df.columns:
                continue
            
            if merged is None:
                merged = df[['code']].drop_duplicates()
            
            merged = merged.merge(df, on='code', how='left')
        
        if merged is None or len(merged) == 0:
            return {
                'report': {'quality_score': 0, 'passed': False, 'recommendations': ['无有效数据']},
                'cleaned_features': pd.DataFrame(),
                'passed': False,
            }
        
        # 完整性检查
        completeness = self.check_completeness(merged)
        print(f"[数据质量] 完整性检查：缺失率={completeness['missing_rate']:.1%}")
        
        # 有效性检查
        validity = self.check_validity(merged)
        print(f"[数据质量] 有效性检查：无效记录={validity['total_invalid']}条")
        
        # 异常检测
        original_len = len(merged)
        merged_clean = self.detect_outliers(merged)
        outlier_rate = 1 - len(merged_clean) / original_len
        print(f"[数据质量] 异常检测：异常率={outlier_rate:.1%}")
        
        # 计算质量评分
        quality_score = self.calculate_quality_score(completeness, validity, outlier_rate)
        
        # 生成报告
        report = self.generate_report(completeness, validity, outlier_rate, quality_score)
        
        print(f"[数据质量] 完成，质量评分：{quality_score:.1f}，{'合格' if report['passed'] else '不合格'}")
        
        return {
            'report': report,
            'cleaned_features': merged_clean,
            'passed': report['passed'],
        }


# 测试
if __name__ == '__main__':
    config = Config()
    monitor = DataQualityMonitor(config)
    
    # 创建测试数据
    test_data = pd.DataFrame({
        'code': ['600519', '000858', '600036', '000002', '000651'],
        'pe_ttm': [25, 30, 10, 8, np.nan],
        'pb': [5, 4, 1.2, 1.5, 2],
        'roe': [20, 15, 12, 10, 18],
        'rsi_14': [55, 45, 60, 40, 50],
    })
    
    features_dict = {
        'fundamental': test_data,
    }
    
    result = monitor.run(features_dict)
    
    print("\n" + "="*60)
    print("📊 数据质量监控结果")
    print("="*60)
    print(f"质量评分：{result['report']['quality_score']:.1f}")
    print(f"是否合格：{'是' if result['passed'] else '否'}")
    print("\n建议:")
    for rec in result['report']['recommendations']:
        print(f"  - {rec}")
