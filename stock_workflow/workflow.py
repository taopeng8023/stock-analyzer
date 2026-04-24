#!/usr/bin/env python3
"""
股票筛选与多因子决策工作流 - 主调度模块
版本：1.1
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import json
import sys

# 添加模块路径
sys.path.append(str(Path(__file__).parent))

from config.loader import Config
from modules.stock_filter import StockFilter
from modules.fundamental import FundamentalAnalyzer
from modules.technical import TechnicalAnalyzer
from modules.news_sentiment import NewsSentimentAnalyzer
from modules.data_quality import DataQualityMonitor
from modules.decision_fusion import DecisionFusion
from modules.output import ResultOutput
from modules.real_data_fetcher import RealDataFetcher


class StockWorkflow:
    """股票筛选与多因子决策工作流"""
    
    def __init__(self, config: Config = None):
        """
        初始化工作流
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        self.start_time = None
        self.logs = []
        
        # 初始化各模块
        self.stock_filter = StockFilter(self.config)
        self.fundamental = FundamentalAnalyzer(self.config)
        self.technical = TechnicalAnalyzer(self.config)
        self.news = NewsSentimentAnalyzer(self.config)
        self.quality = DataQualityMonitor(self.config)
        self.decision = DecisionFusion(self.config)
        self.output = ResultOutput(self.config)
        self.data_fetcher = RealDataFetcher(self.config)
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        self.logs.append(log_msg)
        print(log_msg)
    
    def run(self, stock_list: pd.DataFrame = None, volume_data: pd.DataFrame = None, 
            turnover_data: pd.DataFrame = None, price_data: dict = None,
            is_training: bool = False, use_real_data: bool = False) -> dict:
        """
        运行完整工作流
        
        Args:
            stock_list: 股票列表 DataFrame
            volume_data: 成交量数据 DataFrame
            turnover_data: 成交额数据 DataFrame
            price_data: 价格数据 Dict（训练时需要）
            is_training: 是否训练模式
            use_real_data: 是否使用真实数据
        
        Returns:
            工作流结果 Dict
        """
        self.start_time = datetime.now()
        self.log("="*60)
        self.log("🚀 股票筛选与多因子决策工作流 启动")
        self.log("="*60)
        
        results = {
            'status': 'success',
            'start_time': self.start_time.isoformat(),
            'end_time': None,
            'duration': None,
            'modules': {},
            'final_result': None,
        }
        
        try:
            # ==================== 阶段 1: 股票筛选 ====================
            self.log("\n" + "="*60)
            self.log("📋 阶段 1: 股票筛选")
            self.log("="*60)
            
            if use_real_data and (stock_list is None or volume_data is None):
                # 获取真实数据
                self.log("[数据获取] 正在获取真实股票数据...")
                stock_list = self.data_fetcher.fetch_stock_list()
                self.log(f"[数据获取] 获取到 {len(stock_list)} 只股票")
                
                # 生成模拟成交量数据（真实 API 需要额外实现）
                import random
                volume_data = pd.DataFrame({
                    'code': stock_list['code'].tolist()[:50],  # 只取前 50 只
                    'vol_t': [random.randint(5000, 20000) for _ in range(min(50, len(stock_list)))],
                    'vol_t1': [random.randint(3000, 15000) for _ in range(min(50, len(stock_list)))],
                    'vol_t2': [random.randint(3000, 15000) for _ in range(min(50, len(stock_list)))],
                    'vol_t3': [random.randint(3000, 15000) for _ in range(min(50, len(stock_list)))],
                    'vol_t4': [random.randint(3000, 15000) for _ in range(min(50, len(stock_list)))],
                })
                self.log(f"[数据获取] 生成成交量数据：{len(volume_data)} 只")
            
            # 降级处理：如果 volume_data 仍为 None，使用模拟数据
            if volume_data is None:
                self.log("[数据获取] 使用模拟成交量数据")
                volume_data = pd.DataFrame({
                    'code': ['600519', '000858', '600036', '000002', '000651'],
                    'vol_t': [10000, 8000, 15000, 5000, 12000],
                    'vol_t1': [5000, 5000, 6000, 5000, 5000],
                    'vol_t2': [5000, 5000, 6000, 5000, 5000],
                    'vol_t3': [5000, 5000, 6000, 5000, 5000],
                    'vol_t4': [5000, 5000, 6000, 5000, 5000],
                })
            
            if stock_list is None:
                self.log("[数据获取] 使用模拟股票列表")
                stock_list = pd.DataFrame({
                    'code': ['600519', '000858', '600036', '000002', '000651', '300750', '688981'],
                    'name': ['贵州茅台', '五粮液', '招商银行', '万科 A', '格力电器', '宁德时代', '中芯国际'],
                    'status': ['正常交易'] * 7,
                    'list_date': ['2001-08-27'] * 7,
                })
            
            filter_result = self.stock_filter.run(stock_list, volume_data, turnover_data)
            stock_pool = filter_result['stock_pool']
            
            results['modules']['stock_filter'] = {
                'status': 'success',
                'stock_count': len(stock_pool),
                'quality_score': filter_result['quality_score'],
                'stats': filter_result['stats'],
            }
            
            self.log(f"候选股票池：{len(stock_pool)}只")
            self.log(f"筛选质量评分：{filter_result['quality_score']:.1f}")
            
            if len(stock_pool) == 0:
                raise ValueError("股票筛选后无候选股票")
            
            stock_codes = stock_pool['code'].tolist()
            
            # ==================== 阶段 2: 并行特征提取 ====================
            self.log("\n" + "="*60)
            self.log("📊 阶段 2: 特征提取（并行）")
            self.log("="*60)
            
            # 基本面分析
            fundamental_result = self.fundamental.run(stock_codes)
            results['modules']['fundamental'] = {
                'status': 'success',
                'quality_score': fundamental_result['quality_score'],
            }
            self.log(f"基本面分析完成，质量评分：{fundamental_result['quality_score']:.1f}")
            
            # 技术分析
            technical_result = self.technical.run(stock_codes)
            results['modules']['technical'] = {
                'status': 'success',
                'quality_score': technical_result['quality_score'],
            }
            self.log(f"技术分析完成，质量评分：{technical_result['quality_score']:.1f}")
            
            # 市场消息分析
            news_result = self.news.run(stock_codes)
            results['modules']['news'] = {
                'status': 'success',
                'quality_score': news_result['quality_score'],
            }
            self.log(f"市场消息分析完成，质量评分：{news_result['quality_score']:.1f}")
            
            # ==================== 阶段 3: 数据质量监控 ====================
            self.log("\n" + "="*60)
            self.log("🔍 阶段 3: 数据质量监控")
            self.log("="*60)
            
            features_dict = {
                'fundamental': fundamental_result['features'],
                'technical': technical_result['features'],
                'news': news_result['features'],
            }
            
            quality_result = self.quality.run(features_dict)
            results['modules']['data_quality'] = {
                'status': 'success' if quality_result['passed'] else 'warning',
                'quality_score': quality_result['report']['quality_score'],
                'passed': quality_result['passed'],
            }
            
            self.log(f"数据质量评分：{quality_result['report']['quality_score']:.1f}")
            self.log(f"质量状态：{'✅ 合格' if quality_result['passed'] else '⚠️ 需关注'}")
            
            # ==================== 阶段 4: 决策融合 ====================
            self.log("\n" + "="*60)
            self.log("🤖 阶段 4: 决策融合")
            self.log("="*60)
            
            decision_result = self.decision.run(
                features_dict, 
                price_data=price_data,
                is_training=is_training
            )
            
            results['modules']['decision'] = {
                'status': 'success',
                'prediction_count': len(decision_result['predictions']),
                'top_stocks_count': len(decision_result['top_stocks']),
            }
            
            self.log(f"预测完成，推荐 {len(decision_result['top_stocks'])} 只股票")
            
            # ==================== 阶段 5: 结果输出 ====================
            self.log("\n" + "="*60)
            self.log("📤 阶段 5: 结果输出")
            self.log("="*60)
            
            output_result = self.output.run(
                decision_result['top_stocks'],
                features_dict,
                quality_result['report']
            )
            
            results['modules']['output'] = {
                'status': 'success',
                'formats': ['json', 'csv', 'report'],
            }
            
            results['final_result'] = {
                'top_stocks': output_result['data'].to_dict('records'),
                'report': output_result['report'],
            }
            
            self.log("\n" + output_result['report'])
            
        except Exception as e:
            self.log(f"❌ 错误：{str(e)}")
            results['status'] = 'error'
            results['error'] = str(e)
        
        # 记录结束时间
        end_time = datetime.now()
        results['end_time'] = end_time.isoformat()
        results['duration'] = (end_time - self.start_time).total_seconds()
        
        self.log("\n" + "="*60)
        self.log(f"✅ 工作流完成，耗时：{results['duration']:.1f}秒")
        self.log("="*60)
        
        return results
    
    def save_logs(self, filepath: str = None):
        """保存日志"""
        if filepath is None:
            filepath = Path(__file__).parent.parent / 'logs' / f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.logs))
        
        return filepath


# 主程序入口
if __name__ == '__main__':
    print("="*60)
    print("📊 股票筛选与多因子决策工作流 v1.1")
    print("="*60)
    
    # 创建配置
    config = Config()
    
    # 创建工作流
    workflow = StockWorkflow(config)
    
    # 运行工作流（模拟数据）
    results = workflow.run(is_training=False)
    
    # 保存日志
    log_file = workflow.save_logs()
    print(f"\n📁 日志已保存：{log_file}")
    
    # 保存结果
    if results['status'] == 'success' and results['final_result']:
        result_file = Path(__file__).parent.parent / 'data' / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results['final_result'], f, ensure_ascii=False, indent=2)
        
        print(f"📁 结果已保存：{result_file}")
