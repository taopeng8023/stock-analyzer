#!/usr/bin/env python3
"""
v8.0-Financial-Enhanced 基准版工作流

🏆 十轮回测验证 (1200 次决策) 最优配置
📊 作为股票筛选的基准版，严格数据验证

⚠️ 基准版原则:
1. 数据获取失败 = 筛选失败，严禁使用替代方案
2. 必须使用原版数据源（百度 + 腾讯 + 东方财富）
3. 数据质量不达标 = 不推送
4. 保持基准版的纯粹性和可追溯性

用法:
    python3 workflow_v8_baseline.py --strategy main --top 10 --push
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 导入原版数据源
from local_crawler import StockCrawler
from data_sources import MultiDataSource


class V8BaselineWorkflow:
    """v8.0-Financial-Enhanced 基准版工作流"""
    
    VERSION = 'v8.0-Financial-Enhanced'
    BASELINE_DATE = '2026-03-21'
    
    # 数据质量要求
    MIN_DATA_SOURCES = 2           # 最少数据源数量
    MIN_STOCKS_PER_SOURCE = 10     # 每个数据源最少股票数
    MIN_TOTAL_STOCKS = 20          # 最少总股票数
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        self.crawler = StockCrawler(self.cache_dir)
        self.multi_source = MultiDataSource(self.cache_dir)
        
        self.data_sources_used = []
        self.validation_errors = []
    
    def fetch_main_force_data(self, top_n: int = 20) -> Optional[Dict[str, List]]:
        """
        获取主力净流入数据（基准版）
        
        数据源（必须按顺序）:
        1. 百度股市通 - 主力净流入排名
        2. 腾讯财经 - 成交额估算
        3. 东方财富 - 板块资金流
        
        Returns:
            Dict: 各数据源数据，失败返回 None
        """
        print("\n" + "="*80)
        print(f"💰 {self.VERSION} 基准版 - 主力净流入排行")
        print("="*80)
        print(f"基准日期：{self.BASELINE_DATE}")
        print(f"数据质量要求：最少{self.MIN_DATA_SOURCES}个数据源，每个{self.MIN_STOCKS_PER_SOURCE}条")
        
        results = {}
        self.data_sources_used = []
        self.validation_errors = []
        
        # 1. 百度股市通（核心数据源）
        print("\n[1/3] 百度股市通 - 主力净流入排名...")
        try:
            baidu_data = self.crawler.crawl_baidu_rank('change')
            
            if not baidu_data or len(baidu_data) == 0:
                error_msg = "❌ 百度股市通：获取 0 条数据"
                print(error_msg)
                self.validation_errors.append(error_msg)
            else:
                baidu_data.sort(key=lambda x: x.get('amount_wan', 0), reverse=True)
                results['baidu'] = baidu_data[:top_n]
                self.data_sources_used.append('baidu')
                print(f"  ✅ 获取 {len(results['baidu'])} 条")
                
        except Exception as e:
            error_msg = f"❌ 百度股市通：异常 - {e}"
            print(error_msg)
            self.validation_errors.append(error_msg)
        
        # 2. 腾讯财经（估算）
        print("\n[2/3] 腾讯财经 - 成交额估算...")
        try:
            tencent_data = self.crawler.crawl_tencent()
            
            if not tencent_data or len(tencent_data) < self.MIN_STOCKS_PER_SOURCE:
                error_msg = f"❌ 腾讯财经：获取 {len(tencent_data) if tencent_data else 0} 条，低于要求{self.MIN_STOCKS_PER_SOURCE}条"
                print(error_msg)
                self.validation_errors.append(error_msg)
            else:
                tencent_data.sort(key=lambda x: x.get('amount_wan', 0), reverse=True)
                results['tencent'] = tencent_data[:top_n]
                self.data_sources_used.append('tencent')
                print(f"  ✅ 获取 {len(results['tencent'])} 条")
                
        except Exception as e:
            error_msg = f"❌ 腾讯财经：异常 - {e}"
            print(error_msg)
            self.validation_errors.append(error_msg)
        
        # 3. 东方财富板块
        print("\n[3/3] 东方财富 - 板块资金流...")
        try:
            sector_data = self.crawler.crawl_eastmoney_sector('concept')
            
            if not sector_data or len(sector_data) == 0:
                error_msg = "❌ 东方财富：获取 0 条数据"
                print(error_msg)
                self.validation_errors.append(error_msg)
            else:
                sector_data.sort(key=lambda x: x.get('main_net', 0), reverse=True)
                results['eastmoney'] = sector_data[:top_n]
                self.data_sources_used.append('eastmoney')
                print(f"  ✅ 获取 {len(results['eastmoney'])} 条")
                
        except Exception as e:
            error_msg = f"❌ 东方财富：异常 - {e}"
            print(error_msg)
            self.validation_errors.append(error_msg)
        
        return results
    
    def validate_data_quality(self, results: Dict) -> bool:
        """
        验证数据质量（基准版严格标准）
        
        Args:
            results: 各数据源数据
        
        Returns:
            bool: 是否通过验证
        """
        print("\n" + "="*80)
        print("🔍 数据质量验证（基准版严格标准）")
        print("="*80)
        
        passed = True
        
        # 检查 1: 数据源数量
        source_count = len(results)
        print(f"\n[检查 1] 数据源数量：{source_count}/{self.MIN_DATA_SOURCES}")
        if source_count < self.MIN_DATA_SOURCES:
            print(f"  ❌ 失败：有效数据源 {source_count} 个，低于要求 {self.MIN_DATA_SOURCES} 个")
            passed = False
        else:
            print(f"  ✅ 通过")
        
        # 检查 2: 每个数据源股票数量
        print(f"\n[检查 2] 各数据源股票数量（要求≥{self.MIN_STOCKS_PER_SOURCE}条）:")
        for source, data in results.items():
            count = len(data)
            if count >= self.MIN_STOCKS_PER_SOURCE:
                print(f"  ✅ {source}: {count} 条")
            else:
                print(f"  ❌ {source}: {count} 条 (低于要求)")
                passed = False
        
        # 检查 3: 总股票数
        total_stocks = sum(len(data) for data in results.values())
        print(f"\n[检查 3] 总股票数：{total_stocks}/{self.MIN_TOTAL_STOCKS}")
        if total_stocks < self.MIN_TOTAL_STOCKS:
            print(f"  ❌ 失败：总股票数 {total_stocks}，低于要求 {self.MIN_TOTAL_STOCKS}")
            passed = False
        else:
            print(f"  ✅ 通过")
        
        # 检查 4: 核心数据源（百度）必须有效
        print(f"\n[检查 4] 核心数据源（百度股市通）:")
        if 'baidu' not in results:
            print(f"  ❌ 失败：百度股市通数据缺失")
            passed = False
        else:
            print(f"  ✅ 通过")
        
        return passed
    
    def generate_failure_report(self) -> str:
        """
        生成筛选失败报告
        
        Returns:
            str: 失败报告
        """
        lines = [
            f"🎯 {self.VERSION} 基准版 - 筛选失败报告",
            f"⏰ {datetime.now().strftime('%m-%d %H:%M')}",
            f"📊 仅主板 | 排除创业/科创/北交所",
            f"⚠️ 仅供参考，不构成投资建议",
            "",
            "━━❌ 数据获取失败━━",
            "",
        ]
        
        # 列出错误
        lines.append("📋 失败原因:")
        for i, error in enumerate(self.validation_errors, 1):
            lines.append(f"  {i}. {error}")
        
        lines.append("")
        lines.append(f"📊 有效数据源：{len(self.data_sources_used)}/3")
        if self.data_sources_used:
            lines.append(f"   - {', '.join(self.data_sources_used)}")
        else:
            lines.append(f"   - 无")
        
        lines.append("")
        lines.append("💡 建议:")
        lines.append("  - 等待数据源恢复")
        lines.append("  - 检查网络连接")
        lines.append("  - 使用缓存数据（如有）")
        lines.append("")
        lines.append("="*50)
        lines.append(f"_📊 {self.VERSION} 基准版 - 严格数据验证_")
        lines.append(f"_⚠️ 数据获取失败 = 筛选失败，严禁使用替代方案_")
        
        return '\n'.join(lines)
    
    def run(self, strategy: str = 'main', top_n: int = 10, push: bool = False) -> bool:
        """
        运行基准版工作流
        
        Args:
            strategy: 策略类型
            top_n: 推荐数量
            push: 是否推送
        
        Returns:
            bool: 是否成功
        """
        print("\n" + "="*80)
        print(f"🚀 {self.VERSION} 基准版工作流启动")
        print("="*80)
        print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"策略：{strategy}")
        print(f"目标数量：Top {top_n}")
        
        # 1. 获取数据
        results = self.fetch_main_force_data(top_n)
        
        if not results:
            print("\n❌ 数据获取失败，无有效数据源")
            success = False
        else:
            # 2. 验证数据质量
            success = self.validate_data_quality(results)
        
        # 3. 处理结果
        if success:
            print("\n✅ 数据质量验证通过，继续处理...")
            # TODO: 调用后续的分析和推送逻辑
            return True
        else:
            print("\n❌ 数据质量验证失败，输出筛选失败报告")
            
            # 生成失败报告
            report = self.generate_failure_report()
            print("\n" + report)
            
            # 推送失败报告
            if push:
                self.push_report(report)
            
            return False
    
    def push_report(self, content: str):
        """
        推送报告到企业微信
        
        Args:
            content: 报告内容
        """
        from wechat_push import push_to_corp_webhook
        
        webhook = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5'
        
        title = f"❌ {self.VERSION} - 筛选失败"
        
        print(f"\n📤 正在推送失败报告...")
        success = push_to_corp_webhook(webhook, title, content)
        
        if success:
            print("✅ 推送成功")
        else:
            print("❌ 推送失败")


# CLI 入口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description=f'{V8BaselineWorkflow.VERSION} 基准版工作流')
    parser.add_argument('--strategy', default='main', choices=['main', 'gainers', 'volume'])
    parser.add_argument('--top', type=int, default=10, help='推荐数量')
    parser.add_argument('--push', action='store_true', help='推送到企业微信')
    
    args = parser.parse_args()
    
    workflow = V8BaselineWorkflow()
    success = workflow.run(
        strategy=args.strategy,
        top_n=args.top,
        push=args.push
    )
    
    sys.exit(0 if success else 1)
