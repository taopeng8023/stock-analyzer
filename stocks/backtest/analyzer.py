#!/usr/bin/env python3
"""
回测分析器 - v1.0

功能:
- 绩效分析
- 风险评估
- 交易分析
- 可视化报告生成

用法:
    from backtest.analyzer import BacktestAnalyzer
    
    analyzer = BacktestAnalyzer()
    report = analyzer.generate_report(result)
"""

from typing import Dict, List, Optional
from datetime import datetime
import json

from .engine import BacktestResult, Trade


class BacktestAnalyzer:
    """回测分析器"""
    
    def __init__(self):
        pass
    
    def analyze_performance(self, result: BacktestResult) -> Dict:
        """
        绩效分析
        
        Args:
            result: 回测结果
        
        Returns:
            Dict: 绩效分析结果
        """
        analysis = {
            'return_analysis': self._analyze_returns(result),
            'risk_analysis': self._analyze_risk(result),
            'trade_analysis': self._analyze_trades(result),
            'evaluation': self._evaluate_performance(result)
        }
        
        return analysis
    
    def _analyze_returns(self, result: BacktestResult) -> Dict:
        """收益分析"""
        returns = {
            'total_return': result.total_return,
            'annualized_return': result.annualized_return,
            'avg_daily_return': sum(result.daily_returns) / len(result.daily_returns) if result.daily_returns else 0,
            'best_day': max(result.daily_returns) if result.daily_returns else 0,
            'worst_day': min(result.daily_returns) if result.daily_returns else 0,
            'positive_days': sum(1 for r in result.daily_returns if r > 0),
            'negative_days': sum(1 for r in result.daily_returns if r < 0),
        }
        
        returns['profit_days_ratio'] = (
            returns['positive_days'] / len(result.daily_returns) * 100 
            if result.daily_returns else 0
        )
        
        return returns
    
    def _analyze_risk(self, result: BacktestResult) -> Dict:
        """风险分析"""
        risk = {
            'volatility': result.volatility,
            'max_drawdown': result.max_drawdown,
            'sharpe_ratio': result.sharpe_ratio,
            'sortino_ratio': result.sortino_ratio,
            'calmar_ratio': result.annualized_return / result.max_drawdown if result.max_drawdown > 0 else 0,
        }
        
        # 风险评级
        if result.sharpe_ratio >= 2:
            risk['rating'] = '优秀'
        elif result.sharpe_ratio >= 1:
            risk['rating'] = '良好'
        elif result.sharpe_ratio >= 0:
            risk['rating'] = '一般'
        else:
            risk['rating'] = '较差'
        
        return risk
    
    def _analyze_trades(self, result: BacktestResult) -> Dict:
        """交易分析"""
        trades = result.trades
        
        # 按股票统计
        stock_stats = {}
        for trade in trades:
            if trade.code not in stock_stats:
                stock_stats[trade.code] = {
                    'total_trades': 0,
                    'buy_count': 0,
                    'sell_count': 0,
                    'total_amount': 0
                }
            
            stock_stats[trade.code]['total_trades'] += 1
            if trade.direction == 'buy':
                stock_stats[trade.code]['buy_count'] += 1
            else:
                stock_stats[trade.code]['sell_count'] += 1
            stock_stats[trade.code]['total_amount'] += trade.amount
        
        return {
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate': result.win_rate,
            'avg_profit': result.avg_profit,
            'avg_loss': result.avg_loss,
            'profit_factor': result.profit_factor,
            'stock_stats': stock_stats
        }
    
    def _evaluate_performance(self, result: BacktestResult) -> Dict:
        """综合评价"""
        scores = {
            'return_score': 0,
            'risk_score': 0,
            'stability_score': 0,
            'total_score': 0
        }
        
        # 收益评分（0-40 分）
        if result.annualized_return >= 30:
            scores['return_score'] = 40
        elif result.annualized_return >= 20:
            scores['return_score'] = 35
        elif result.annualized_return >= 15:
            scores['return_score'] = 30
        elif result.annualized_return >= 10:
            scores['return_score'] = 25
        elif result.annualized_return >= 5:
            scores['return_score'] = 20
        elif result.annualized_return >= 0:
            scores['return_score'] = 10
        else:
            scores['return_score'] = max(0, 10 + result.annualized_return)
        
        # 风险评分（0-30 分）
        if result.sharpe_ratio >= 2:
            scores['risk_score'] = 30
        elif result.sharpe_ratio >= 1.5:
            scores['risk_score'] = 25
        elif result.sharpe_ratio >= 1:
            scores['risk_score'] = 20
        elif result.sharpe_ratio >= 0.5:
            scores['risk_score'] = 15
        elif result.sharpe_ratio >= 0:
            scores['risk_score'] = 10
        else:
            scores['risk_score'] = max(0, 10 + result.sharpe_ratio * 10)
        
        # 稳定性评分（0-30 分）
        if result.max_drawdown <= 10:
            scores['stability_score'] = 30
        elif result.max_drawdown <= 15:
            scores['stability_score'] = 25
        elif result.max_drawdown <= 20:
            scores['stability_score'] = 20
        elif result.max_drawdown <= 30:
            scores['stability_score'] = 15
        else:
            scores['stability_score'] = max(0, 15 - result.max_drawdown / 2)
        
        scores['total_score'] = (
            scores['return_score'] + 
            scores['risk_score'] + 
            scores['stability_score']
        )
        
        # 综合评级
        if scores['total_score'] >= 90:
            scores['rating'] = 'AAA'
        elif scores['total_score'] >= 80:
            scores['rating'] = 'AA'
        elif scores['total_score'] >= 70:
            scores['rating'] = 'A'
        elif scores['total_score'] >= 60:
            scores['rating'] = 'BBB'
        elif scores['total_score'] >= 50:
            scores['rating'] = 'BB'
        else:
            scores['rating'] = 'B'
        
        return scores
    
    def generate_report(self, result: BacktestResult, 
                        format: str = 'text') -> str:
        """
        生成回测报告
        
        Args:
            result: 回测结果
            format: 报告格式（text/json/markdown）
        
        Returns:
            str: 报告内容
        """
        analysis = self.analyze_performance(result)
        
        if format == 'json':
            return json.dumps({
                'backtest_result': result.to_dict(),
                'analysis': analysis
            }, indent=2, ensure_ascii=False)
        
        elif format == 'markdown':
            return self._generate_markdown_report(result, analysis)
        
        else:  # text
            return self._generate_text_report(result, analysis)
    
    def _generate_text_report(self, result: BacktestResult, 
                              analysis: Dict) -> str:
        """生成文本报告"""
        lines = [
            "="*80,
            "📊 回测分析报告",
            "="*80,
            "",
            result.summary(),
            "",
            "📈 收益分析:",
            f"  平均日收益：{analysis['return_analysis']['avg_daily_return']:.3f}%",
            f"  最佳单日：{analysis['return_analysis']['best_day']:+.2f}%",
            f"  最差单日：{analysis['return_analysis']['worst_day']:+.2f}%",
            f"  盈利天数：{analysis['return_analysis']['positive_days']} ({analysis['return_analysis']['profit_days_ratio']:.1f}%)",
            "",
            "⚠️ 风险分析:",
            f"  风险评级：{analysis['risk_analysis']['rating']}",
            f"  卡玛比率：{analysis['risk_analysis']['calmar_ratio']:.2f}",
            "",
            "💰 交易分析:",
            f"  盈利因子：{analysis['trade_analysis']['profit_factor']:.2f}",
            "",
            "🎯 综合评价:",
            f"  总分：{analysis['evaluation']['total_score']:.0f}/100",
            f"  评级：{analysis['evaluation']['rating']}",
            "",
            "="*80,
        ]
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self, result: BacktestResult, 
                                  analysis: Dict) -> str:
        """生成 Markdown 报告"""
        lines = [
            "# 📊 回测分析报告",
            "",
            "## 基本信息",
            "",
            f"- **回测区间**: {result.start_date} 至 {result.end_date}",
            f"- **初始资金**: ¥{result.initial_capital:,.0f}",
            f"- **最终资金**: ¥{result.final_capital:,.0f}",
            "",
            "## 📈 收益指标",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总收益率 | {result.total_return:+.2f}% |",
            f"| 年化收益率 | {result.annualized_return:+.2f}% |",
            f"| 平均日收益 | {analysis['return_analysis']['avg_daily_return']:.3f}% |",
            f"| 最佳单日 | {analysis['return_analysis']['best_day']:+.2f}% |",
            f"| 最差单日 | {analysis['return_analysis']['worst_day']:+.2f}% |",
            "",
            "## ⚠️ 风险指标",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 波动率 | {result.volatility:.2f}% |",
            f"| 最大回撤 | {result.max_drawdown:.2f}% |",
            f"| 夏普比率 | {result.sharpe_ratio:.2f} |",
            f"| 索提诺比率 | {result.sortino_ratio:.2f} |",
            f"| 风险评级 | {analysis['risk_analysis']['rating']} |",
            "",
            "## 💰 交易统计",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总交易次数 | {result.total_trades} |",
            f"| 胜率 | {result.win_rate:.2f}% |",
            f"| 平均盈利 | {result.avg_profit:+.2f}% |",
            f"| 平均亏损 | {result.avg_loss:+.2f}% |",
            f"| 盈利因子 | {result.profit_factor:.2f} |",
            "",
            "## 🎯 综合评价",
            "",
            f"- **总分**: {analysis['evaluation']['total_score']:.0f}/100",
            f"- **评级**: {analysis['evaluation']['rating']}",
            "",
            "### 评分明细",
            "",
            f"- 收益评分：{analysis['evaluation']['return_score']}/40",
            f"- 风险评分：{analysis['evaluation']['risk_score']}/30",
            f"- 稳定性评分：{analysis['evaluation']['stability_score']}/30",
            "",
            "---",
            f"*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ]
        
        return "\n".join(lines)


# 测试
if __name__ == '__main__':
    from .engine import BacktestEngine
    
    print("="*80)
    print("🔍 回测分析器测试")
    print("="*80)
    
    # 创建回测引擎并运行简单回测
    engine = BacktestEngine(initial_capital=1000000)
    
    def simple_strategy(day_data):
        signals = []
        date = day_data.get('date', '')
        if date == '2026-01-01':
            for code, data in day_data.items():
                if code != 'date':
                    signals.append({
                        'code': code,
                        'action': 'buy',
                        'shares': 100,
                        'price': data.get('close', 0)
                    })
        return signals
    
    import random
    from datetime import datetime, timedelta
    
    data = []
    codes = ['600519', '000858', '600036']
    
    for i in range(60):
        date = (datetime(2026, 1, 1) + timedelta(days=i)).strftime('%Y-%m-%d')
        day_data = {'date': date}
        
        for code in codes:
            base_price = {'600519': 1800, '000858': 150, '600036': 35}[code]
            price = base_price * (1 + random.uniform(-0.02, 0.02) * (i / 30))
            day_data[code] = {'close': price}
        
        data.append(day_data)
    
    result = engine.run_backtest(
        strategy=simple_strategy,
        data=data,
        start_date='2026-01-01',
        end_date='2026-03-01'
    )
    
    # 分析回测结果
    analyzer = BacktestAnalyzer()
    analysis = analyzer.analyze_performance(result)
    
    print("\n📊 绩效分析:")
    print(f"  收益评分：{analysis['evaluation']['return_score']}/40")
    print(f"  风险评分：{analysis['evaluation']['risk_score']}/30")
    print(f"  稳定性评分：{analysis['evaluation']['stability_score']}/30")
    print(f"  总分：{analysis['evaluation']['total_score']:.0f}/100")
    print(f"  评级：{analysis['evaluation']['rating']}")
    
    print("\n" + "="*80)
    print("📄 Markdown 报告预览:")
    print("="*80)
    report = analyzer.generate_report(result, format='markdown')
    print(report[:2000])
