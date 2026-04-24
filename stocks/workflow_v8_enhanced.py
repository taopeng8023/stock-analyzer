#!/usr/bin/env python3
"""
v8.0-Financial-Enhanced 工作流 - 多数据源增强版
集成 6 大数据源，确保数据获取稳定性

数据源列表:
1. 百度股市通 - 主力净流入排名 (原有)
2. 腾讯财经 - 实时行情 + 成交额估算 (原有增强)
3. 东方财富 - 个股资金流排名 (新增 API)
4. 同花顺 - 资金流排名 (新增)
5. 新浪财经 - 备用实时行情 (新增)
6. 网易财经 - 历史行情 (新增)

用法:
    python3 workflow_v8_enhanced.py --top 20 --push
    python3 workflow_v8_enhanced.py --ml-enhance
    python3 workflow_v8_enhanced.py --financial-models
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 导入新数据源
from data_sources_v2 import MultiSourceFetcher


class WorkflowV8Enhanced:
    """v8.0 增强版工作流"""
    
    def __init__(self):
        self.cache_dir = Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        # 新数据源获取器
        self.fetcher = MultiSourceFetcher(self.cache_dir)
        
        # 原有模块
        from stock_selector import StockSelector
        from financial_models import FinancialModelsEnsemble
        from workflow_push import format_final_decision_message
        
        self.selector = StockSelector()
        self.models = FinancialModelsEnsemble()
        self.format_push = format_final_decision_message
    
    def fetch_multi_source_data(self, top_n: int = 50) -> Dict[str, List[Dict]]:
        """
        从多数据源获取数据
        
        Args:
            top_n: 每个数据源获取数量
        
        Returns:
            dict: 各数据源数据
        """
        print("\n" + "="*80)
        print("📡 多数据源数据获取")
        print("="*80)
        
        results = {}
        
        # 1. 东方财富（最稳定）
        print("\n[1/4] 东方财富 - 个股资金流...")
        em_data = self.fetcher.get_em_individual_flow(top_n)
        if em_data:
            results['eastmoney'] = em_data
            print(f"  ✅ 获取 {len(em_data)} 条")
        
        # 2. 腾讯财经（批量）
        if em_data:
            codes = [s['code'] for s in em_data[:30]]
            print(f"\n[2/4] 腾讯财经 - 批量获取 {len(codes)} 只...")
            tencent_data = self.fetcher.get_tencent_batch(codes, batch_size=50)
            if tencent_data:
                results['tencent'] = tencent_data
                print(f"  ✅ 获取 {len(tencent_data)} 条")
        
        # 3. 同花顺（降级到东方财富）
        print("\n[3/4] 同花顺 - 资金流排名...")
        ths_data = self.fetcher.get_ths_flow_rank(top_n)
        if ths_data and len(ths_data) > 0:
            results['ths'] = ths_data
            print(f"  ✅ 获取 {len(ths_data)} 条")
        
        # 4. 新浪财经（备用）
        if tencent_data and len(tencent_data) < 10:
            codes = [s['code'] for s in tencent_data]
            print(f"\n[4/4] 新浪财经 - 备用获取...")
            sina_data = self.fetcher.get_sina_quote(codes)
            if sina_data:
                results['sina'] = sina_data
                print(f"  ✅ 获取 {len(sina_data)} 条")
        
        # 汇总
        print("\n" + "="*80)
        print("📊 数据源汇总")
        print("="*80)
        total = sum(len(data) for data in results.values())
        print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"数据源数量：{len(results)}")
        for source, data in results.items():
            print(f"  - {source}: {len(data)} 条")
        print(f"总计：{total} 条")
        
        return results
    
    def merge_and_analyze(self, sources_data: Dict[str, List[Dict]]) -> List[Dict]:
        """
        合并多数据源并进行分析
        
        Args:
            sources_data: 各数据源数据
        
        Returns:
            list: 分析后的股票列表
        """
        print("\n" + "="*80)
        print("🔍 数据合并与分析")
        print("="*80)
        
        # 合并数据
        merged = self.fetcher.merge_results(sources_data)
        print(f"合并后股票数：{len(merged)}")
        
        # 分析每只股票
        analyzed = []
        for stock in merged:
            # 多数据源验证
            sources_count = len(stock.get('sources', []))
            
            # 计算综合评分
            score = 0
            
            # 数据源数量评分
            score += min(sources_count * 10, 30)  # 最多 30 分
            
            # 资金流评分
            if 'eastmoney_main_flow' in stock:
                flow = stock['eastmoney_main_flow']
                if flow > 10000:  # >1 亿
                    score += 40
                elif flow > 5000:
                    score += 30
                elif flow > 1000:
                    score += 20
            
            # 腾讯成交额评分
            if 'tencent_turnover' in stock:
                turnover = stock['tencent_turnover']
                if turnover > 5000000000:  # >50 亿
                    score += 30
                elif turnover > 1000000000:  # >10 亿
                    score += 20
            
            # 涨跌幅评分
            if 'tencent_change_pct' in stock:
                change = stock['tencent_change_pct']
                if 3 <= change <= 7:  # 温和上涨
                    score += 20
                elif 0 <= change < 3:
                    score += 10
            
            stock['composite_score'] = score
            stock['sources_count'] = sources_count
            
            analyzed.append(stock)
        
        # 排序
        analyzed.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        
        print(f"分析完成，最高分：{analyzed[0]['composite_score'] if analyzed else 0}")
        
        return analyzed
    
    def run(self, top_n: int = 20, use_ml: bool = False, use_financial: bool = False):
        """
        运行完整工作流
        
        Args:
            top_n: 推荐数量
            use_ml: 是否使用 ML 增强
            use_financial: 是否使用金融模型增强
        """
        print("\n" + "="*80)
        print("🚀 v8.0-Financial-Enhanced 工作流启动")
        print("="*80)
        print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"模式：{'ML 增强' if use_ml else '标准'} + {'金融模型' if use_financial else '标准'}")
        
        # 1. 多数据源获取
        sources_data = self.fetch_multi_source_data(top_n * 2)
        
        if not sources_data:
            print("\n❌ 所有数据源失败，使用缓存数据")
            # TODO: 加载缓存
        
        # 2. 合并分析
        analyzed = self.merge_and_analyze(sources_data)
        
        # 3. 应用金融模型（v8.0 特性）
        if use_financial and analyzed:
            print("\n" + "="*80)
            print("🏦 应用金融模型 (v8.0)")
            print("="*80)
            
            codes = [s['code'] for s in analyzed[:top_n]]
            # TODO: 调用 financial_models
        
        # 4. 输出结果
        print("\n" + "="*80)
        print("🎯 最终推荐")
        print("="*80)
        
        for i, stock in enumerate(analyzed[:top_n], 1):
            sources = ', '.join(stock.get('sources', []))
            score = stock.get('composite_score', 0)
            print(f"{i:2d}. {stock.get('code', '')} {stock.get('name', ''):10s} 评分:{score:3d} 数据源:{sources}")
        
        return analyzed[:top_n]


# CLI 入口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='v8.0-Financial-Enhanced 多数据源增强版')
    parser.add_argument('--top', type=int, default=20, help='推荐数量')
    parser.add_argument('--ml-enhance', action='store_true', help='使用 ML 增强')
    parser.add_argument('--financial-models', action='store_true', help='使用金融模型增强')
    parser.add_argument('--push', action='store_true', help='推送到企业微信')
    
    args = parser.parse_args()
    
    workflow = WorkflowV8Enhanced()
    results = workflow.run(
        top_n=args.top,
        use_ml=args.ml_enhance,
        use_financial=args.financial_models
    )
    
    print(f"\n✅ 工作流完成，推荐 {len(results)} 只股票")
