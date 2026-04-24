"""
A 股智能选股系统 - 主分析模块
鹏总专用版本 v1.0

功能:
- 输入股票代码
- 输出：能否买入、10 日目标收益、成功概率
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from data_fetcher import DataFetcher
from technical_analyzer import TechnicalAnalyzer
from fundamental_analyzer import FundamentalAnalyzer
from predictor import ReturnPredictor
from config import BUY_THRESHOLDS, TRADING_PARAMS


class StockAnalyzer:
    """
    股票分析器
    
    鹏总专用选股系统
    输入股票代码，输出完整分析报告
    """
    
    def __init__(self):
        self.fetcher = DataFetcher()
        self.tech_analyzer = TechnicalAnalyzer()
        self.fund_analyzer = FundamentalAnalyzer()
        self.predictor = ReturnPredictor()
    
    def analyze(self, stock_code: str) -> dict:
        """
        分析股票
        
        参数:
            stock_code: 股票代码 (6 位数字)
        
        返回:
            完整分析报告
        """
        print(f"\n{'='*60}")
        print(f"  鹏总选股系统 - 股票分析报告")
        print(f"{'='*60}")
        print(f"  分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  股票代码：{stock_code}")
        print(f"{'='*60}\n")
        
        # 1. 获取数据
        print("📊 正在获取数据...")
        
        # 市场数据
        market_data = self.fetcher.get_stock_info(stock_code)
        if not market_data:
            return self._error_report(stock_code, "无法获取股票信息")
        
        print(f"  ✓ 股票名称：{market_data['name']}")
        print(f"  ✓ 当前价格：¥{market_data['price']}")
        print(f"  ✓ 涨跌幅：{market_data['change_pct']}%")
        
        # 历史数据
        hist_data = self.fetcher.get_historical_data(stock_code, 90)
        if hist_data.empty:
            return self._error_report(stock_code, "无法获取历史数据")
        
        print(f"  ✓ K 线数据：{len(hist_data)} 天")
        
        # 财务数据
        financial_data = self.fetcher.get_financial_data(stock_code)
        if financial_data:
            print(f"  ✓ 财务数据：已获取")
        else:
            print(f"  ⚠ 财务数据：未获取到")
            financial_data = {}
        
        # 资金数据
        money_flow = self.fetcher.get_money_flow(stock_code)
        print(f"  ✓ 资金流向：已获取")
        
        # 2. 技术分析
        print("\n📈 技术分析...")
        tech_result = self.tech_analyzer.get_technical_score(hist_data)
        print(f"  技术评分：{tech_result['score']}")
        
        # 3. 基本面分析
        print("\n📋 基本面分析...")
        fund_result = self.fund_analyzer.get_fundamental_score(financial_data, market_data)
        print(f"  基本面评分：{fund_result['score']}")
        
        # 4. 资金面分析
        print("\n💰 资金面分析...")
        money_score = self._calculate_money_flow_score(money_flow, hist_data)
        print(f"  资金面评分：{money_score}")
        
        # 5. 综合评分
        print("\n🎯 综合评估...")
        total_score = (tech_result['score'] * 0.40 + 
                      fund_result['score'] * 0.35 + 
                      money_score * 0.25)
        print(f"  综合评分：{total_score:.1f}")
        
        # 6. 收益预测
        trend_data = self.tech_analyzer.calculate_trend_strength(hist_data)
        return_prediction = self.predictor.predict_10d_return(
            technical_score=tech_result['score'],
            fundamental_score=fund_result['score'],
            money_flow_score=money_score,
            trend_data=trend_data
        )
        
        # 7. 成功概率
        volume_ratio = self.tech_analyzer.calculate_volume_analysis(hist_data)['volume_ratio']
        northbound = money_flow.get('northbound_net', 0) > 0
        success_prob = self.predictor.calculate_success_probability(
            technical_score=tech_result['score'],
            fundamental_score=fund_result['score'],
            money_flow_score=money_score,
            volume_ratio=volume_ratio,
            northbound_inflow=northbound
        )
        
        # 8. 目标价位
        target_prices = self.predictor.generate_target_price(
            current_price=market_data['price'],
            expected_return=return_prediction['expected_return']
        )
        
        # 9. 买入建议
        buy_advice = self._generate_buy_advice(total_score, success_prob, trend_data)
        
        # 10. 生成报告
        report = {
            'stock_code': stock_code,
            'stock_name': market_data['name'],
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_price': market_data['price'],
            'change_pct': market_data['change_pct'],
            
            # 评分
            'scores': {
                'technical': tech_result['score'],
                'fundamental': fund_result['score'],
                'money_flow': money_score,
                'total': round(total_score, 1),
            },
            
            # 预测
            'prediction': {
                '10d_expected_return': return_prediction['expected_return'],
                '10d_optimistic': return_prediction['optimistic'],
                '10d_pessimistic': return_prediction['pessimistic'],
                'confidence': return_prediction['confidence'],
            },
            
            # 成功概率
            'success_probability': {
                'probability': success_prob['probability'],
                'level': success_prob['level'],
                'icon': success_prob['icon'],
                'factors': success_prob['factors'],
            },
            
            # 目标价位
            'target_prices': target_prices,
            
            # 买入建议
            'buy_advice': buy_advice,
            
            # 详细信号
            'signals': {
                'technical': tech_result['signals'],
                'fundamental': fund_result['signals'],
            },
            
            # 趋势
            'trend': trend_data,
        }
        
        # 打印报告
        self._print_report(report)
        
        return report
    
    def _calculate_money_flow_score(self, money_flow: dict, hist_data) -> int:
        """计算资金面评分"""
        score = 50
        
        # 主力净流入
        main_force = money_flow.get('main_force_net', 0)
        if main_force > 1:
            score += 15
        elif main_force > 0.5:
            score += 10
        elif main_force > 0:
            score += 5
        elif main_force < -1:
            score -= 15
        elif main_force < -0.5:
            score -= 10
        
        # 成交量趋势
        if len(hist_data) >= 5:
            avg_volume_5d = hist_data['volume'].tail(5).mean()
            avg_volume_prev = hist_data['volume'].iloc[-10:-5].mean()
            if avg_volume_5d > avg_volume_prev * 1.3:
                score += 10
            elif avg_volume_5d > avg_volume_prev:
                score += 5
        
        return max(0, min(100, score))
    
    def _generate_buy_advice(self, total_score: float, 
                            success_prob: dict,
                            trend_data: dict) -> dict:
        """生成买入建议"""
        # 判断建议等级
        if total_score >= BUY_THRESHOLDS['excellent'] and success_prob['probability'] >= 70:
            action = '强烈推荐买入'
            action_code = 'STRONG_BUY'
            icon = '🟢'
        elif total_score >= BUY_THRESHOLDS['good'] and success_prob['probability'] >= 60:
            action = '推荐买入'
            action_code = 'BUY'
            icon = '🟢'
        elif total_score >= BUY_THRESHOLDS['neutral'] and success_prob['probability'] >= 50:
            action = '观望'
            action_code = 'HOLD'
            icon = '🟡'
        else:
            action = '不建议买入'
            action_code = 'SELL'
            icon = '🔴'
        
        # 仓位建议
        if action_code == 'STRONG_BUY':
            position = '30-50%'
        elif action_code == 'BUY':
            position = '20-30%'
        elif action_code == 'HOLD':
            position = '0-10%'
        else:
            position = '0%'
        
        # 操作策略
        strategies = []
        if action_code in ['STRONG_BUY', 'BUY']:
            strategies.append(f"分批建仓，首笔 30%")
            strategies.append(f"止损位：-8%")
            strategies.append(f"止盈位：+25%")
            strategies.append(f"持有周期：5-10 天")
        elif action_code == 'HOLD':
            strategies.append("等待更好机会")
            strategies.append("关注突破信号")
        else:
            strategies.append("规避风险")
            strategies.append("等待企稳信号")
        
        return {
            'action': action,
            'action_code': action_code,
            'icon': icon,
            'position': position,
            'strategies': strategies,
            'reason': f"综合评分{total_score:.1f}, 成功概率{success_prob['probability']:.1f}%",
        }
    
    def _print_report(self, report: dict):
        """打印分析报告"""
        print(f"\n{'='*60}")
        print(f"  📊 分析报告")
        print(f"{'='*60}")
        
        # 基本信息
        print(f"\n📌 股票信息")
        print(f"   代码：{report['stock_code']}")
        print(f"   名称：{report['stock_name']}")
        print(f"   现价：¥{report['current_price']} ({report['change_pct']}%)")
        
        # 评分
        print(f"\n🎯 综合评分")
        scores = report['scores']
        print(f"   技术面：{scores['technical']}/100")
        print(f"   基本面：{scores['fundamental']}/100")
        print(f"   资金面：{scores['money_flow']}/100")
        print(f"   ─────────────")
        print(f"   总评分：{scores['total']}/100")
        
        # 预测
        print(f"\n📈 10 日收益预测")
        pred = report['prediction']
        print(f"   预期收益：{pred['10d_expected_return']}%")
        print(f"   乐观情景：{pred['10d_optimistic']}%")
        print(f"   悲观情景：{pred['10d_pessimistic']}%")
        print(f"   置信度：{pred['confidence']}%")
        
        # 成功概率
        print(f"\n🎲 成功概率")
        prob = report['success_probability']
        print(f"   概率：{prob['probability']}% {prob['icon']} ({prob['level']})")
        print(f"   因素：{', '.join(prob['factors'])}")
        
        # 目标价位
        print(f"\n💰 目标价位")
        tp = report['target_prices']
        print(f"   目标价：¥{tp['target_price']} ({tp['upside']}%)")
        print(f"   止损价：¥{tp['stop_loss']} ({tp['downside']}%)")
        print(f"   盈亏比：{tp['risk_reward']}:1")
        
        # 买入建议
        print(f"\n💡 操作建议")
        advice = report['buy_advice']
        print(f"   {advice['icon']} {advice['action']}")
        print(f"   建议仓位：{advice['position']}")
        print(f"   理由：{advice['reason']}")
        print(f"   策略:")
        for s in advice['strategies']:
            print(f"     • {s}")
        
        # 详细信号
        print(f"\n📋 详细信号")
        print(f"   技术面:")
        for sig in report['signals']['technical'][:5]:
            print(f"     {sig}")
        print(f"   基本面:")
        for sig in report['signals']['fundamental'][:3]:
            print(f"     {sig}")
        
        print(f"\n{'='*60}")
        print(f"  ⚠️ 风险提示：股市有风险，投资需谨慎")
        print(f"  本报告仅供参考，不构成投资建议")
        print(f"{'='*60}\n")
    
    def _error_report(self, stock_code: str, error: str) -> dict:
        """错误报告"""
        return {
            'stock_code': stock_code,
            'error': error,
            'buy_advice': {
                'action': '无法分析',
                'action_code': 'ERROR',
                'icon': '⚠️',
                'position': '0%',
                'strategies': ['检查股票代码是否正确'],
            }
        }


# 命令行入口
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python analyzer.py <股票代码>")
        print("示例：python analyzer.py 603659")
        sys.exit(1)
    
    stock_code = sys.argv[1]
    
    analyzer = StockAnalyzer()
    report = analyzer.analyze(stock_code)
    
    # 保存报告
    output_file = Path(__file__).parent / f"reports/{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📁 报告已保存：{output_file}")
