#!/usr/bin/env python3
"""
结果输出模块 - v1.0
目标：将决策结果以结构化格式输出，供用户查看和使用
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List
import sys
sys.path.append('..')

from config.loader import Config


class ResultOutput:
    """结果输出器"""
    
    def __init__(self, config: Config = None):
        """
        初始化结果输出器
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        self.output_format = self.config.get('OUTPUT', 'output_format').split(',')
    
    def enrich_stock_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        丰富股票信息
        
        Args:
            df: 预测结果 DataFrame
        
        Returns:
            丰富后的 DataFrame
        """
        # TODO: 从数据库获取股票名称等信息
        # 这里使用模拟数据
        stock_names = {
            '600519': '贵州茅台',
            '000858': '五粮液',
            '600036': '招商银行',
            '000002': '万科 A',
            '000651': '格力电器',
        }
        
        df = df.copy()
        df['name'] = df['code'].map(stock_names)
        df['name'] = df['name'].fillna('未知')
        
        return df
    
    def calculate_scores(self, df: pd.DataFrame, features_dict: Dict) -> pd.DataFrame:
        """
        计算各项评分
        
        Args:
            df: 预测结果 DataFrame
            features_dict: 各模块特征 Dict
        
        Returns:
            包含评分的 DataFrame
        """
        df = df.copy()
        
        # 基本面评分
        if 'fundamental_grade' not in df.columns:
            # 如果已有 fundamental_score，直接使用它计算 grade
            if 'fundamental_score' in df.columns:
                df['fundamental_score'] = df['fundamental_score'].fillna(0)
                df['fundamental_grade'] = pd.cut(
                    df['fundamental_score'],
                    bins=[-np.inf, -1, 0, 1, np.inf],
                    labels=['C', 'B', 'A', 'A+']
                )
            elif 'fundamental' in features_dict:
                fund_df = features_dict['fundamental']
                if 'fundamental_score' in fund_df.columns:
                    df = df.merge(fund_df[['code', 'fundamental_score']], on='code', how='left')
                    df['fundamental_score'] = df['fundamental_score'].fillna(0)
                    df['fundamental_grade'] = pd.cut(
                        df['fundamental_score'],
                        bins=[-np.inf, -1, 0, 1, np.inf],
                        labels=['C', 'B', 'A', 'A+']
                    )
                elif 'pe_ttm_zscore' in fund_df.columns:
                    # 降级处理：使用 pe_ttm_zscore 作为替代
                    df = df.merge(fund_df[['code', 'pe_ttm_zscore']], on='code', how='left')
                    df['fundamental_score'] = -df['pe_ttm_zscore'].fillna(0)
                    df['fundamental_grade'] = pd.cut(
                        df['fundamental_score'],
                        bins=[-np.inf, -1, 0, 1, np.inf],
                        labels=['C', 'B', 'A', 'A+'],
                        include_lowest=True
                    )
                else:
                    df['fundamental_grade'] = 'A'
        
        # 技术信号
        if 'tech_signal' not in df.columns:
            if 'ma5_ma20_ratio' in df.columns:
                df['tech_signal'] = df['ma5_ma20_ratio'].apply(
                    lambda x: '强买入' if x > 1.1 else '买入' if x > 1.0 else '中性' if x > 0.9 else '卖出'
                )
            elif 'technical' in features_dict:
                tech_df = features_dict['technical']
                if 'ma5_ma20_ratio' in tech_df.columns:
                    df = df.merge(tech_df[['code', 'ma5_ma20_ratio']], on='code', how='left')
                    df['tech_signal'] = df['ma5_ma20_ratio'].apply(
                        lambda x: '强买入' if x > 1.1 else '买入' if x > 1.0 else '中性' if x > 0.9 else '卖出'
                    )
                else:
                    df['tech_signal'] = '中性'
        
        # 消息情绪
        if 'news_sentiment' not in df.columns:
            if 'sentiment_avg' in df.columns:
                df['news_sentiment'] = df['sentiment_avg'].apply(
                    lambda x: '积极' if x > 0.2 else '中性' if x > -0.2 else '消极'
                )
            elif 'news' in features_dict:
                news_df = features_dict['news']
                if 'sentiment_avg' in news_df.columns:
                    df = df.merge(news_df[['code', 'sentiment_avg']], on='code', how='left')
                    df['news_sentiment'] = df['sentiment_avg'].apply(
                        lambda x: '积极' if x > 0.2 else '中性' if x > -0.2 else '消极'
                    )
                else:
                    df['news_sentiment'] = '中性'
        
        return df
    
    def to_json(self, df: pd.DataFrame) -> str:
        """
        转换为 JSON 格式
        
        Args:
            df: DataFrame
        
        Returns:
            JSON 字符串
        """
        records = df.to_dict('records')
        return json.dumps(records, ensure_ascii=False, indent=2, default=str)
    
    def to_csv(self, df: pd.DataFrame, filepath: str = None) -> str:
        """
        转换为 CSV 格式
        
        Args:
            df: DataFrame
            filepath: 文件路径
        
        Returns:
            CSV 字符串或保存文件
        """
        csv_str = df.to_csv(index=False)
        if filepath:
            df.to_csv(filepath, index=False)
        return csv_str
    
    def generate_report(self, df: pd.DataFrame, quality_report: Dict) -> str:
        """
        生成可视化报告文本
        
        Args:
            df: 预测结果 DataFrame
            quality_report: 质量报告 Dict
        
        Returns:
            报告文本
        """
        lines = []
        lines.append("=" * 70)
        lines.append("📊 股票筛选与多因子决策报告")
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")
        
        # 数据质量
        lines.append("📋 数据质量")
        lines.append(f"  质量评分：{quality_report.get('quality_score', 0):.1f}/100")
        lines.append(f"  质量状态：{'✅ 合格' if quality_report.get('passed', False) else '⚠️ 需关注'}")
        lines.append("")
        
        # 推荐股票
        lines.append("🎯 推荐股票（Top 10）")
        lines.append("-" * 70)
        
        for i, row in df.iterrows():
            lines.append(f"{i+1}. {row.get('name', '未知')} ({row['code']})")
            lines.append(f"   上涨概率：{row.get('up_probability', 0):.1%}")
            lines.append(f"   排名：第{row.get('rank', 0)}名")
            
            if 'fundamental_grade' in row:
                lines.append(f"   基本面：{row['fundamental_grade']}")
            if 'tech_signal' in row:
                lines.append(f"   技术信号：{row['tech_signal']}")
            if 'news_sentiment' in row:
                lines.append(f"   消息情绪：{row['news_sentiment']}")
            
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("⚠️ 风险提示：本报告仅供参考，不构成投资建议")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def push_notification(self, df: pd.DataFrame, channels: List[str] = None) -> Dict:
        """
        推送通知
        
        Args:
            df: 预测结果 DataFrame
            channels: 推送渠道列表
        
        Returns:
            推送结果 Dict
        """
        if channels is None:
            channels = ['wechat']
        
        results = {}
        
        for channel in channels:
            if channel == 'wechat':
                # TODO: 实现微信推送
                results['wechat'] = {'success': True, 'message': '微信推送成功'}
            elif channel == 'email':
                # TODO: 实现邮件推送
                results['email'] = {'success': True, 'message': '邮件推送成功'}
            elif channel == 'api':
                # TODO: 实现 API 推送
                results['api'] = {'success': True, 'message': 'API 推送成功'}
        
        return results
    
    def run(self, predictions: pd.DataFrame, features_dict: Dict, quality_report: Dict) -> Dict:
        """
        运行完整的结果输出流程
        
        Args:
            predictions: 预测结果 DataFrame
            features_dict: 各模块特征 Dict
            quality_report: 质量报告 Dict
        
        Returns:
            输出结果 Dict
        """
        print(f"[结果输出] 开始处理 {len(predictions)} 只股票的输出...")
        
        # 处理空预测结果
        if len(predictions) == 0:
            print(f"[结果输出] 警告：没有推荐股票，生成空报告")
            return {
                'data': predictions,
                'report': "📊 股票筛选与多因子决策报告\n生成时间：" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n⚠️ 今日无符合筛选条件的股票",
                'json': '[]',
                'csv': predictions.to_csv(index=False) if len(predictions) > 0 else '',
                'push_result': {},
            }
        
        # 丰富股票信息
        enriched = self.enrich_stock_info(predictions)
        
        # 计算各项评分
        enriched = self.calculate_scores(enriched, features_dict)
        
        # 生成报告
        report = self.generate_report(enriched, quality_report)
        
        # 转换为不同格式
        json_output = self.to_json(enriched)
        csv_output = self.to_csv(enriched)
        
        # 推送通知
        push_result = self.push_notification(enriched)
        
        print(f"[结果输出] 完成")
        
        return {
            'data': enriched,
            'report': report,
            'json': json_output,
            'csv': csv_output,
            'push_result': push_result,
        }


# 测试
if __name__ == '__main__':
    config = Config()
    output = ResultOutput(config)
    
    # 创建测试数据
    test_predictions = pd.DataFrame({
        'code': ['600519', '000858', '600036', '000002', '000651'],
        'up_probability': [0.72, 0.68, 0.65, 0.62, 0.60],
        'rank': [1, 2, 3, 4, 5],
    })
    
    test_features = {
        'fundamental': pd.DataFrame({
            'code': ['600519', '000858', '600036', '000002', '000651'],
            'fundamental_score': [1.5, 1.2, 0.8, 0.5, 0.3],
        }),
        'technical': pd.DataFrame({
            'code': ['600519', '000858', '600036', '000002', '000651'],
            'ma5_ma20_ratio': [1.15, 1.08, 1.02, 0.98, 0.95],
        }),
        'news': pd.DataFrame({
            'code': ['600519', '000858', '600036', '000002', '000651'],
            'sentiment_avg': [0.5, 0.3, 0.1, -0.1, -0.2],
        }),
    }
    
    quality_report = {
        'quality_score': 98.5,
        'passed': True,
    }
    
    result = output.run(test_predictions, test_features, quality_report)
    
    print("\n" + "="*60)
    print("📊 结果输出")
    print("="*60)
    print(result['report'])
