#!/usr/bin/env python3
"""
Market Analysis Skill - 市场分析技能（整合版）

整合所有市场分析工具：
- 技术面分析
- 基本面分析
- 资金流分析
- 概率计算
- 目标价计算
- 报告生成与推送

⚠️  核心原则：
1. 只使用真实数据
2. 严格数据验证
3. 明确标注来源
4. 无真实数据不分析

用法:
    python market_analysis_skill.py --full        # 完整分析
    python market_analysis_skill.py --stock CODE  # 分析个股
    python market_analysis_skill.py --push        # 推送报告
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'stocks'))


class MarketAnalysisSkill:
    """市场分析技能主类"""
    
    def __init__(self, config=None):
        """
        初始化技能
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.data_cache = {}
        
        # 导入模块
        self._import_modules()
    
    def _import_modules(self):
        """导入分析模块"""
        try:
            # 添加 stocks 路径
            stocks_path = Path(__file__).parent.parent.parent / 'stocks'
            sys.path.insert(0, str(stocks_path))
            
            # 数据获取
            from fund_flow import FundFlowFetcher
            self.data_fetcher = FundFlowFetcher()
            
            # 技术面分析
            from technical_analysis import calculate_technical_score
            self.technical_analyzer = calculate_technical_score
            
            # 基本面分析
            from fundamental_analysis import calculate_fundamental_score
            self.fundamental_analyzer = calculate_fundamental_score
            
            # 概率计算
            from market_analysis_complete import calculate_probability
            self.probability_calculator = calculate_probability
            
            # 目标价计算
            from market_analysis_complete import calculate_sell_price
            self.target_price_calculator = calculate_sell_price
            
            # 数据验证
            from data_validation import DataValidator
            self.validator = DataValidator(strict_mode=True)
            
            # 微信推送
            from wechat_push import push_to_corp_webhook
            self.push_function = push_to_corp_webhook
            
        except Exception as e:
            print(f"⚠️  模块导入警告：{e}")
    
    def fetch_data(self, count=50):
        """
        获取市场数据
        
        Args:
            count: 获取股票数量
        
        Returns:
            股票数据列表
        """
        print(f"📊 获取市场数据（{count}只）...")
        
        try:
            stocks = self.data_fetcher.fetch_tencent_estimate(count=count)
            print(f"✅ 获取到 {len(stocks)} 只股票数据")
            return stocks
        except Exception as e:
            print(f"❌ 数据获取失败：{e}")
            return []
    
    def analyze_stock(self, stock_data):
        """
        分析单只股票
        
        Args:
            stock_data: 股票数据
        
        Returns:
            分析结果
        """
        symbol = stock_data.get('symbol', '')
        name = stock_data.get('name', '')
        
        # 数据验证
        if not self.validator.validate_stock_data(stock_data, symbol):
            return {
                'error': '数据验证失败',
                'symbol': symbol,
                'name': name,
            }
        
        # 技术面分析
        technical = self.technical_analyzer(stock_data)
        
        # 基本面分析
        fundamental = self.fundamental_analyzer(stock_data)
        
        # 概率计算
        probability = self.probability_calculator(stock_data)
        
        # 目标价计算
        target_price = self.target_price_calculator(stock_data)
        
        return {
            'symbol': symbol,
            'name': name,
            'source': stock_data.get('source', 'real'),
            'price_data': {
                'price': stock_data.get('price', 0),
                'change_pct': stock_data.get('change_pct', 0),
                'amount_wan': stock_data.get('amount_wan', 0),
                'main_net': stock_data.get('main_net', 0),
            },
            'technical': technical,
            'fundamental': fundamental,
            'probability': probability,
            'target_price': target_price,
        }
    
    def filter_quality(self, stocks_data, min_score=60, min_probability=50):
        """
        筛选优质股票
        
        Args:
            stocks_data: 股票数据列表
            min_score: 最小综合评分
            min_probability: 最小上涨概率
        
        Returns:
            优质股票列表
        """
        quality_stocks = []
        
        for stock in stocks_data:
            tech_score = stock.get('technical', {}).get('total_score', 0)
            fund_score = stock.get('fundamental', {}).get('total_score', 0)
            avg_score = (tech_score + fund_score) / 2
            
            rise_prob = stock.get('probability', {}).get('rise_probability', 0)
            
            if avg_score >= min_score and rise_prob >= min_probability:
                quality_stocks.append(stock)
        
        print(f"📈 筛选出 {len(quality_stocks)} 只优质股票")
        return quality_stocks
    
    def generate_report(self, stocks_data, report_type='full'):
        """
        生成分析报告
        
        Args:
            stocks_data: 股票数据列表
            report_type: 报告类型（quick/full/detailed）
        
        Returns:
            报告文本
        """
        lines = []
        lines.append("="*90)
        lines.append("📊 市场分析报告")
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("="*90)
        lines.append("")
        
        # 市场概况
        if stocks_data:
            avg_change = sum(s.get('price_data', {}).get('change_pct', 0) for s in stocks_data) / len(stocks_data)
            total_amount = sum(s.get('price_data', {}).get('amount_wan', 0) for s in stocks_data)
            
            if avg_change > 5:
                sentiment = "强势上涨"
            elif avg_change > 0:
                sentiment = "偏强"
            elif avg_change > -5:
                sentiment = "震荡"
            else:
                sentiment = "偏弱"
            
            lines.append("📋 **市场概况**")
            lines.append(f"  分析股票：{len(stocks_data)}只")
            lines.append(f"  平均涨幅：{avg_change:+.2f}%")
            lines.append(f"  总成交额：{total_amount/10000:.2f}亿")
            lines.append(f"  市场情绪：{sentiment}")
            lines.append("")
            lines.append("-"*90)
            lines.append("")
        
        # 个股详细分析
        if report_type in ['full', 'detailed']:
            lines.append("📈 **个股详细分析**")
            lines.append("")
            
            for i, stock in enumerate(stocks_data[:10], 1):
                name = stock.get('name', 'Unknown')
                symbol = stock.get('symbol', '')
                source = '✅' if stock.get('source') == 'real' else '⚠️'
                
                lines.append(f"### {i}. {name} ({symbol}) {source}")
                lines.append("")
                
                # 行情数据
                price_data = stock.get('price_data', {})
                lines.append("**行情数据：**")
                lines.append(f"- 现价：¥{price_data.get('price', 0):.2f}")
                lines.append(f"- 涨跌：{price_data.get('change_pct', 0):+.2f}%")
                lines.append(f"- 成交：{price_data.get('amount_wan', 0):.0f}万")
                lines.append(f"- 主力：{price_data.get('main_net', 0)/10000:.0f}万")
                lines.append("")
                
                # 概率分析
                prob = stock.get('probability', {})
                if prob and 'error' not in prob:
                    lines.append("**概率分析：**")
                    lines.append(f"- 上涨概率：{prob.get('rise_probability', 0):.1f}% {prob.get('stars', '')}")
                    lines.append(f"- 下跌概率：{prob.get('fall_probability', 0):.1f}%")
                    lines.append(f"- 评级：{prob.get('rating', 'N/A')}")
                    lines.append("")
                
                # 目标价
                target = stock.get('target_price', {})
                if target and 'error' not in target:
                    lines.append("**目标价：**")
                    lines.append(f"- 当前：¥{target.get('current_price', 0):.2f}")
                    lines.append(f"- 目标：¥{target.get('take_profit', 0):.2f}")
                    lines.append(f"- 止损：¥{target.get('stop_loss', 0):.2f}")
                    lines.append("")
                
                lines.append("-"*90)
                lines.append("")
        
        # 综合对比表
        lines.append("📊 **综合对比**")
        lines.append("")
        lines.append(f"{'股票':<10} {'现价':<8} {'上涨概率':<10} {'止损价':<10} {'止盈价':<10} {'评级':<15}")
        lines.append("-"*90)
        
        for stock in stocks_data[:10]:
            name = stock.get('name', '')
            price = stock.get('price_data', {}).get('price', 0)
            prob = stock.get('probability', {})
            target = stock.get('target_price', {})
            
            rise_prob = f"{prob.get('rise_probability', 0):.1f}%"
            stop_loss = f"¥{target.get('stop_loss', 0):.2f}" if target else 'N/A'
            take_profit = f"¥{target.get('take_profit', 0):.2f}" if target else 'N/A'
            rating = prob.get('rating', 'N/A')
            
            lines.append(f"{name:<10} ¥{price:<6.2f} {rise_prob:<10} {stop_loss:<10} {take_profit:<10} {rating:<15}")
        
        lines.append("")
        lines.append("-"*90)
        lines.append("")
        
        # 风险提示
        lines.append("⚠️ **风险提示**")
        lines.append("")
        lines.append("1. **数据说明**")
        lines.append("   - ✅ 真实数据：来自腾讯财经")
        lines.append("   - ⚠️ 估算数据：主力=成交额×15%")
        lines.append("   - 📊 模型分析：概率/目标价为模型计算")
        lines.append("")
        lines.append("2. **投资风险**")
        lines.append("   - 概率不保证实现")
        lines.append("   - 目标价不保证达到")
        lines.append("   - 请设置止损，控制仓位")
        lines.append("   - 本报告仅供参考，不构成投资建议")
        lines.append("")
        lines.append("="*90)
        
        return "\n".join(lines)
    
    def push_report(self, report_text, title="📊 市场分析报告"):
        """
        推送报告
        
        Args:
            report_text: 报告文本
            title: 报告标题
        
        Returns:
            bool: 是否成功
        """
        print("📤 推送报告...")
        
        # 获取 Webhook（从环境变量或配置）
        webhook = os.getenv('WECHAT_WEBHOOK') or self.config.get('webhook')
        
        if not webhook:
            print("❌ Webhook 未配置")
            return False
        
        try:
            success = self.push_function(webhook, title, report_text)
            if success:
                print("✅ 报告推送成功！")
                return True
            else:
                print("❌ 报告推送失败")
                return False
        except Exception as e:
            print(f"❌ 推送异常：{e}")
            return False
    
    def run_full_analysis(self, count=50, push=False):
        """
        运行完整分析流程
        
        Args:
            count: 分析股票数量
            push: 是否推送报告
        
        Returns:
            分析结果
        """
        print("="*90)
        print("📊 市场分析报告（整合版）")
        print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*90)
        print("")
        
        # 1. 获取数据
        stocks = self.fetch_data(count=count)
        if not stocks:
            return {'error': '数据获取失败'}
        
        # 2. 分析每只股票
        print("\n📈 分析股票...")
        analyzed_stocks = []
        for stock in stocks:
            result = self.analyze_stock(stock)
            if 'error' not in result:
                analyzed_stocks.append(result)
        
        print(f"✅ 完成 {len(analyzed_stocks)} 只股票分析")
        
        # 3. 筛选优质股票
        quality_stocks = self.filter_quality(analyzed_stocks, min_score=60, min_probability=50)
        
        # 4. 生成报告
        report = self.generate_report(quality_stocks, report_type='full')
        
        # 5. 推送报告
        if push:
            self.push_report(report)
        
        return {
            'total': len(stocks),
            'analyzed': len(analyzed_stocks),
            'quality': len(quality_stocks),
            'report': report,
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='市场分析技能（整合版）')
    parser.add_argument('--full', action='store_true', help='完整分析')
    parser.add_argument('--stock', type=str, help='分析特定股票')
    parser.add_argument('--push', action='store_true', help='推送报告')
    parser.add_argument('--count', type=int, default=50, help='分析股票数量')
    
    args = parser.parse_args()
    
    # 初始化技能
    skill = MarketAnalysisSkill()
    
    if args.full:
        # 完整分析
        result = skill.run_full_analysis(count=args.count, push=args.push)
        print(f"\n分析完成：{result.get('quality', 0)}只优质股票")
    
    elif args.stock:
        # 分析特定股票
        print(f"分析股票：{args.stock}")
        # TODO: 实现个股分析
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
