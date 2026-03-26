#!/usr/bin/env python3
"""
决策结果回溯模块
记录每次决策结果，跟踪后续 10 个交易日表现，自动优化决策机制

功能:
1. 记录每次决策结果
2. 跟踪后续 10 个交易日涨跌幅
3. 计算决策准确率
4. 自动优化评分权重
5. 生成回测报告

用法:
    python3 backtest.py --record              # 记录当前决策
    python3 backtest.py --track               # 跟踪已有决策
    python3 backtest.py --report              # 生成回测报告
    python3 backtest.py --optimize            # 自动优化权重
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
import re

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


class DecisionTracker:
    """决策结果跟踪器"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path(__file__).parent / 'backtest_data'
        self.data_dir.mkdir(exist_ok=True)
        
        self.decisions_file = self.data_dir / 'decisions.json'
        self.tracking_file = self.data_dir / 'tracking.json'
        self.results_file = self.data_dir / 'results.json'
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    def record_decision(self, decision_data: dict, workflow_name: str = '股票筛选工作流') -> bool:
        """
        记录一次决策结果
        
        Args:
            decision_data: 决策结果数据 (包含股票列表)
            workflow_name: 工作流名称
        
        Returns:
            bool: 是否成功
        """
        # 加载已有决策
        decisions = self._load_decisions()
        
        # 创建新决策记录
        decision_id = f"decision_{datetime.now().strftime('%Y%m%d')}"
        
        record = {
            'decision_id': decision_id,
            'workflow_name': workflow_name,
            'decision_date': datetime.now().strftime('%Y-%m-%d'),
            'decision_time': datetime.now().isoformat(),
            'stock_count': len(decision_data.get('stocks', [])),
            'stocks': [],
            'tracking_days': 10,
            'status': 'tracking'  # tracking / completed
        }
        
        # 记录每只股票
        for i, stock in enumerate(decision_data.get('stocks', []), 1):
            stock_record = {
                'rank': i,
                'symbol': stock.get('symbol', ''),
                'name': stock.get('name', ''),
                'price_at_decision': stock.get('price', 0),
                'rating': stock.get('rating', ''),
                'confidence': stock.get('confidence', 0),
                'stop_profit': stock.get('stop_profit', 0),
                'stop_loss': stock.get('stop_loss', 0),
                'reasons': stock.get('reasons', []),
                'tracking': {
                    'day_1': None,
                    'day_2': None,
                    'day_3': None,
                    'day_4': None,
                    'day_5': None,
                    'day_6': None,
                    'day_7': None,
                    'day_8': None,
                    'day_9': None,
                    'day_10': None,
                },
                'final_return': 0,
                'hit_stop_profit': False,
                'hit_stop_loss': False,
                'max_return': 0,
                'min_return': 0,
            }
            record['stocks'].append(stock_record)
        
        # 保存
        decisions[decision_id] = record
        self._save_decisions(decisions)
        
        print(f"✅ 决策已记录：{decision_id}")
        print(f"   工作流：{workflow_name}")
        print(f"   决策日期：{record['decision_date']}")
        print(f"   股票数量：{record['stock_count']} 只")
        print(f"   跟踪天数：{record['tracking_days']} 天")
        
        return True
    
    def track_progress(self) -> dict:
        """
        跟踪所有进行中的决策
        
        Returns:
            dict: 跟踪结果
        """
        decisions = self._load_decisions()
        tracking_results = {
            'total': 0,
            'tracking': 0,
            'completed': 0,
            'updated': 0,
        }
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        for decision_id, decision in decisions.items():
            if decision.get('status') == 'completed':
                tracking_results['completed'] += 1
                continue
            
            tracking_results['total'] += 1
            tracking_results['tracking'] += 1
            
            # 计算交易日
            decision_date = datetime.strptime(decision['decision_date'], '%Y-%m-%d')
            trading_days = self._get_trading_days(decision_date, 10)
            
            # 更新每只股票的跟踪数据
            updated = False
            for stock in decision.get('stocks', []):
                symbol = stock.get('symbol', '')
                if not symbol:
                    continue
                
                # 获取历史价格
                prices = self._get_stock_history(symbol, decision_date, 10)
                
                if prices:
                    # 更新跟踪数据
                    for i, price_data in enumerate(prices, 1):
                        day_key = f'day_{i}'
                        if day_key in stock['tracking']:
                            decision_price = stock['price_at_decision']
                            current_price = price_data.get('close', 0)
                            
                            if decision_price > 0 and current_price > 0:
                                daily_return = (current_price - decision_price) / decision_price * 100
                                stock['tracking'][day_key] = {
                                    'date': price_data.get('date', ''),
                                    'price': current_price,
                                    'return': round(daily_return, 2),
                                    'high': price_data.get('high', 0),
                                    'low': price_data.get('low', 0),
                                }
                                
                                # 检查止盈止损
                                stop_profit = stock.get('stop_profit', 0)
                                stop_loss = stock.get('stop_loss', 0)
                                
                                if stop_profit > 0 and current_price >= stop_profit:
                                    stock['hit_stop_profit'] = True
                                if stop_loss > 0 and current_price <= stop_loss:
                                    stock['hit_stop_loss'] = True
                                
                                # 更新最大/最小收益
                                if daily_return > stock['max_return']:
                                    stock['max_return'] = daily_return
                                if daily_return < stock['min_return']:
                                    stock['min_return'] = daily_return
                                
                                # 最终收益 (第 10 天或止盈止损)
                                if i == 10 or stock['hit_stop_profit'] or stock['hit_stop_loss']:
                                    stock['final_return'] = daily_return
                    
                    updated = True
            
            # 检查是否完成跟踪
            if len(trading_days) >= 10 or updated:
                # 检查所有股票是否都有第 10 天数据
                all_completed = True
                for stock in decision.get('stocks', []):
                    if stock['tracking'].get('day_10') is None:
                        all_completed = False
                        break
                
                if all_completed:
                    decision['status'] = 'completed'
                    decision['complete_date'] = today
                    tracking_results['completed'] += 1
                    tracking_results['tracking'] -= 1
            
            if updated:
                tracking_results['updated'] += 1
        
        # 保存更新
        self._save_decisions(decisions)
        
        print(f"📊 跟踪结果:")
        print(f"   总决策数：{tracking_results['total']}")
        print(f"   跟踪中：{tracking_results['tracking']}")
        print(f"   已完成：{tracking_results['completed']}")
        print(f"   本次更新：{tracking_results['updated']}")
        
        return tracking_results
    
    def generate_report(self, decision_id: str = None) -> dict:
        """
        生成回测报告
        
        Args:
            decision_id: 指定决策 ID，None 则生成所有决策汇总
        
        Returns:
            dict: 回测报告
        """
        decisions = self._load_decisions()
        
        if decision_id:
            # 单个决策报告
            if decision_id not in decisions:
                print(f"❌ 未找到决策：{decision_id}")
                return {}
            
            return self._generate_single_report(decisions[decision_id])
        else:
            # 汇总报告
            return self._generate_summary_report(decisions)
    
    def _generate_single_report(self, decision: dict) -> dict:
        """生成单个决策回测报告"""
        report = {
            'decision_id': decision['decision_id'],
            'decision_date': decision['decision_date'],
            'workflow_name': decision.get('workflow_name', ''),
            'stock_count': len(decision.get('stocks', [])),
            'status': decision.get('status', ''),
            'performance': {
                'avg_return': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'best_stock': '',
                'worst_stock': '',
                'hit_stop_profit_count': 0,
                'hit_stop_loss_count': 0,
            },
            'stocks': []
        }
        
        total_return = 0
        win_count = 0
        total_win = 0
        total_loss = 0
        best_return = -999
        worst_return = 999
        
        for stock in decision.get('stocks', []):
            final_return = stock.get('final_return', 0)
            total_return += final_return
            
            if final_return > 0:
                win_count += 1
                total_win += final_return
            else:
                total_loss += final_return
            
            if final_return > best_return:
                best_return = final_return
                report['performance']['best_stock'] = stock.get('name', '')
            
            if final_return < worst_return:
                worst_return = final_return
                report['performance']['worst_stock'] = stock.get('name', '')
            
            if stock.get('hit_stop_profit'):
                report['performance']['hit_stop_profit_count'] += 1
            if stock.get('hit_stop_loss'):
                report['performance']['hit_stop_loss_count'] += 1
            
            report['stocks'].append({
                'rank': stock.get('rank', 0),
                'symbol': stock.get('symbol', ''),
                'name': stock.get('name', ''),
                'rating': stock.get('rating', ''),
                'final_return': final_return,
                'max_return': stock.get('max_return', 0),
                'min_return': stock.get('min_return', 0),
                'hit_stop_profit': stock.get('hit_stop_profit', False),
                'hit_stop_loss': stock.get('hit_stop_loss', False),
            })
        
        stock_count = len(decision.get('stocks', []))
        if stock_count > 0:
            report['performance']['avg_return'] = round(total_return / stock_count, 2)
            report['performance']['win_rate'] = round(win_count / stock_count * 100, 2)
            if win_count > 0:
                report['performance']['avg_win'] = round(total_win / win_count, 2)
            if stock_count - win_count > 0:
                report['performance']['avg_loss'] = round(total_loss / (stock_count - win_count), 2)
        
        # 打印报告
        self._print_report(report)
        
        return report
    
    def _generate_summary_report(self, decisions: dict) -> dict:
        """生成汇总回测报告"""
        completed_decisions = [d for d in decisions.values() if d.get('status') == 'completed']
        
        report = {
            'total_decisions': len(decisions),
            'completed_decisions': len(completed_decisions),
            'tracking_decisions': len(decisions) - len(completed_decisions),
            'overall_performance': {
                'avg_return': 0,
                'win_rate': 0,
                'total_stocks': 0,
                'best_decision': '',
                'worst_decision': '',
            },
            'rating_performance': {},
            'date_range': {
                'first': '',
                'last': ''
            }
        }
        
        if not completed_decisions:
            print("⚠️  暂无已完成的决策")
            return report
        
        total_return = 0
        total_stocks = 0
        win_count = 0
        best_decision_return = -999
        worst_decision_return = 999
        
        # 按评级统计
        rating_stats = {}
        
        for decision in completed_decisions:
            decision_return = 0
            decision_stocks = 0
            decision_wins = 0
            
            for stock in decision.get('stocks', []):
                final_return = stock.get('final_return', 0)
                rating = stock.get('rating', 'unknown')
                
                # 评级统计
                if rating not in rating_stats:
                    rating_stats[rating] = {
                        'count': 0,
                        'total_return': 0,
                        'wins': 0
                    }
                rating_stats[rating]['count'] += 1
                rating_stats[rating]['total_return'] += final_return
                if final_return > 0:
                    rating_stats[rating]['wins'] += 1
                
                # 决策统计
                decision_return += final_return
                decision_stocks += 1
                if final_return > 0:
                    decision_wins += 1
                
                # 总体统计
                total_return += final_return
                total_stocks += 1
                if final_return > 0:
                    win_count += 1
            
            # 计算决策平均收益
            if decision_stocks > 0:
                decision_avg = decision_return / decision_stocks
                
                if decision_avg > best_decision_return:
                    best_decision_return = decision_avg
                    report['overall_performance']['best_decision'] = decision.get('decision_id', '')
                
                if decision_avg < worst_decision_return:
                    worst_decision_return = decision_avg
                    report['overall_performance']['worst_decision'] = decision.get('decision_id', '')
        
        # 计算总体指标
        if total_stocks > 0:
            report['overall_performance']['avg_return'] = round(total_return / total_stocks, 2)
            report['overall_performance']['win_rate'] = round(win_count / total_stocks * 100, 2)
            report['overall_performance']['total_stocks'] = total_stocks
        
        # 计算评级表现
        for rating, stats in rating_stats.items():
            if stats['count'] > 0:
                report['rating_performance'][rating] = {
                    'count': stats['count'],
                    'avg_return': round(stats['total_return'] / stats['count'], 2),
                    'win_rate': round(stats['wins'] / stats['count'] * 100, 2),
                }
        
        # 日期范围
        dates = [d.get('decision_date', '') for d in completed_decisions]
        if dates:
            report['date_range']['first'] = min(dates)
            report['date_range']['last'] = max(dates)
        
        # 打印报告
        self._print_summary_report(report)
        
        return report
    
    def optimize_weights(self) -> dict:
        """
        自动优化评分权重
        
        基于历史回测数据，优化:
        - 成交额权重
        - 涨幅权重
        - 成交量权重
        - 评级置信度阈值
        
        Returns:
            dict: 优化建议
        """
        decisions = self._load_decisions()
        completed = [d for d in decisions.values() if d.get('status') == 'completed']
        
        if len(completed) < 5:
            print("⚠️  数据不足，需要至少 5 个已完成决策")
            return {'success': False, 'reason': '数据不足'}
        
        # 分析不同评级的表现
        rating_performance = {}
        for decision in completed:
            for stock in decision.get('stocks', []):
                rating = stock.get('rating', '')
                final_return = stock.get('final_return', 0)
                
                if rating not in rating_performance:
                    rating_performance[rating] = []
                rating_performance[rating].append(final_return)
        
        # 计算优化建议
        suggestions = {
            'success': True,
            'rating_analysis': {},
            'weight_adjustments': {},
            'confidence_thresholds': {}
        }
        
        # 分析各评级表现
        for rating, returns in rating_performance.items():
            avg_return = sum(returns) / len(returns)
            win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100
            
            suggestions['rating_analysis'][rating] = {
                'count': len(returns),
                'avg_return': round(avg_return, 2),
                'win_rate': round(win_rate, 2),
            }
        
        # 生成权重调整建议
        if '强烈推荐' in rating_performance:
            sr_perf = suggestions['rating_analysis'].get('强烈推荐', {})
            if sr_perf.get('win_rate', 0) < 60:
                suggestions['weight_adjustments']['强烈推荐'] = '提高筛选标准'
            elif sr_perf.get('win_rate', 0) > 80:
                suggestions['weight_adjustments']['强烈推荐'] = '可适当放宽'
        
        if '观望' in rating_performance:
            wg_perf = suggestions['rating_analysis'].get('观望', {})
            if wg_perf.get('win_rate', 0) > 50:
                suggestions['weight_adjustments']['观望'] = '考虑升级为谨慎推荐'
        
        # 置信度阈值优化
        high_confidence_wins = []
        low_confidence_wins = []
        for decision in completed:
            for stock in decision.get('stocks', []):
                confidence = stock.get('confidence', 0)
                final_return = stock.get('final_return', 0)
                
                if confidence >= 75:
                    high_confidence_wins.append(final_return > 0)
                else:
                    low_confidence_wins.append(final_return > 0)
        
        if high_confidence_wins:
            high_win_rate = sum(high_confidence_wins) / len(high_confidence_wins) * 100
            suggestions['confidence_thresholds']['high'] = round(high_win_rate, 2)
        
        if low_confidence_wins:
            low_win_rate = sum(low_confidence_wins) / len(low_confidence_wins) * 100
            suggestions['confidence_thresholds']['low'] = round(low_win_rate, 2)
        
        # 保存优化建议
        suggestions_file = self.data_dir / 'optimization_suggestions.json'
        with open(suggestions_file, 'w', encoding='utf-8') as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)
        
        # 打印建议
        self._print_optimization_suggestions(suggestions)
        
        return suggestions
    
    def _load_decisions(self) -> dict:
        """加载决策记录"""
        if not self.decisions_file.exists():
            return {}
        
        try:
            with open(self.decisions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_decisions(self, decisions: dict):
        """保存决策记录"""
        with open(self.decisions_file, 'w', encoding='utf-8') as f:
            json.dump(decisions, f, ensure_ascii=False, indent=2)
    
    def _get_trading_days(self, start_date: datetime, days: int) -> list:
        """获取交易日列表 (简化版，未考虑节假日)"""
        trading_days = []
        current = start_date
        
        while len(trading_days) < days:
            current += timedelta(days=1)
            # 排除周末
            if current.weekday() < 5:
                trading_days.append(current.strftime('%Y-%m-%d'))
        
        return trading_days
    
    def _get_stock_history(self, symbol: str, start_date: datetime, days: int) -> list:
        """获取股票历史价格 (腾讯财经)"""
        # 腾讯财经 K 线 API
        end_date = start_date + timedelta(days=days + 5)
        
        param = f"{param},{start_date.strftime('%Y%m%d')},{end_date.strftime('%Y%m%d')}"
        
        url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {
            'param': f"{symbol},day,{start_date.strftime('%Y%m%d')},{end_date.strftime('%Y%m%d')},300,qfq"
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()
            
            if data.get('code') == 0:
                kline_data = data.get('data', {})
                key = 'qfqday'
                klines = kline_data.get(key, [])
                
                result = []
                for k in klines:
                    if len(k) >= 7:
                        result.append({
                            'date': k[0],
                            'open': float(k[1]) if k[1] else 0,
                            'close': float(k[3]) if k[3] else 0,
                            'high': float(k[4]) if k[4] else 0,
                            'low': float(k[5]) if k[5] else 0,
                            'volume': float(k[6]) if k[6] else 0,
                        })
                
                return result[:days]
        except:
            pass
        
        return []
    
    def _print_report(self, report: dict):
        """打印单个决策报告"""
        print(f"\n{'='*80}")
        print(f"📊 决策回测报告 - {report.get('decision_id', '')}")
        print(f"{'='*80}")
        print(f"决策日期：{report.get('decision_date', '')}")
        print(f"工作流：{report.get('workflow_name', '')}")
        print(f"状态：{report.get('status', '')}")
        print()
        
        perf = report.get('performance', {})
        print(f"📈 表现统计:")
        print(f"   平均收益：{perf.get('avg_return', 0):+.2f}%")
        print(f"   胜率：{perf.get('win_rate', 0):.1f}%")
        print(f"   平均盈利：{perf.get('avg_win', 0):+.2f}%")
        print(f"   平均亏损：{perf.get('avg_loss', 0):+.2f}%")
        print(f"   最佳股票：{perf.get('best_stock', '')}")
        print(f"   最差股票：{perf.get('worst_stock', '')}")
        print(f"   触发止盈：{perf.get('hit_stop_profit_count', 0)} 只")
        print(f"   触发止损：{perf.get('hit_stop_loss_count', 0)} 只")
        print()
        
        print(f"📋 个股详情:")
        print(f"{'排名':<4} {'代码':<10} {'名称':<10} {'评级':<8} {'收益':>10} {'最大':>10} {'最小':>10}")
        print(f"{'-'*80}")
        
        for stock in report.get('stocks', []):
            rank = stock.get('rank', 0)
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')
            rating = stock.get('rating', '')
            final_return = stock.get('final_return', 0)
            max_return = stock.get('max_return', 0)
            min_return = stock.get('min_return', 0)
            
            return_str = f"{final_return:+.2f}%"
            max_str = f"{max_return:+.2f}%"
            min_str = f"{min_return:+.2f}%"
            
            print(f"{rank:<4} {symbol:<10} {name:<10} {rating:<8} {return_str:>10} {max_str:>10} {min_str:>10}")
        
        print(f"{'='*80}")
    
    def _print_summary_report(self, report: dict):
        """打印汇总报告"""
        print(f"\n{'='*80}")
        print(f"📊 决策回测汇总报告")
        print(f"{'='*80}")
        print(f"总决策数：{report.get('total_decisions', 0)}")
        print(f"已完成：{report.get('completed_decisions', 0)}")
        print(f"跟踪中：{report.get('tracking_decisions', 0)}")
        print(f"日期范围：{report.get('date_range', {}).get('first', '')} ~ {report.get('date_range', {}).get('last', '')}")
        print()
        
        perf = report.get('overall_performance', {})
        print(f"📈 总体表现:")
        print(f"   平均收益：{perf.get('avg_return', 0):+.2f}%")
        print(f"   胜率：{perf.get('win_rate', 0):.1f}%")
        print(f"   总股票数：{perf.get('total_stocks', 0)}")
        print(f"   最佳决策：{perf.get('best_decision', '')}")
        print(f"   最差决策：{perf.get('worst_decision', '')}")
        print()
        
        print(f"📋 评级表现:")
        for rating, stats in report.get('rating_performance', {}).items():
            print(f"   {rating}: {stats.get('count', 0)}只 | 平均收益：{stats.get('avg_return', 0):+.2f}% | 胜率：{stats.get('win_rate', 0):.1f}%")
        
        print(f"{'='*80}")
    
    def _print_optimization_suggestions(self, suggestions: dict):
        """打印优化建议"""
        print(f"\n{'='*80}")
        print(f"🎯 决策优化建议")
        print(f"{'='*80}")
        
        print(f"\n📊 评级分析:")
        for rating, stats in suggestions.get('rating_analysis', {}).items():
            print(f"   {rating}: {stats.get('count', 0)}只 | 平均收益：{stats.get('avg_return', 0):+.2f}% | 胜率：{stats.get('win_rate', 0):.1f}%")
        
        print(f"\n💡 权重调整建议:")
        for rating, adj in suggestions.get('weight_adjustments', {}).items():
            print(f"   {rating}: {adj}")
        
        print(f"\n🎯 置信度阈值:")
        conf = suggestions.get('confidence_thresholds', {})
        if 'high' in conf:
            print(f"   高置信度 (≥75%): 胜率 {conf['high']:.1f}%")
        if 'low' in conf:
            print(f"   低置信度 (<75%): 胜率 {conf['low']:.1f}%")
        
        print(f"\n✅ 优化建议已保存：{self.data_dir / 'optimization_suggestions.json'}")
        print(f"{'='*80}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='决策结果回溯模块')
    parser.add_argument('--record', action='store_true', help='记录当前决策')
    parser.add_argument('--track', action='store_true', help='跟踪进行中的决策')
    parser.add_argument('--report', action='store_true', help='生成回测报告')
    parser.add_argument('--optimize', action='store_true', help='自动优化权重')
    parser.add_argument('--decision-id', type=str, help='指定决策 ID')
    parser.add_argument('--data-dir', type=str, help='数据目录')
    
    args = parser.parse_args()
    
    tracker = DecisionTracker(Path(args.data_dir) if args.data_dir else None)
    
    if args.record:
        # 从最近的决策文件加载
        cache_dir = Path(__file__).parent / 'cache'
        workflow_files = list(cache_dir.glob('workflow_result_*.json'))
        
        if not workflow_files:
            print("❌ 未找到工作流结果文件")
            return
        
        # 获取最新的文件
        latest_file = max(workflow_files, key=lambda f: f.stat().st_mtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            workflow_result = json.load(f)
        
        final_decision = workflow_result.get('final_decision', [])
        
        if not final_decision:
            print("❌ 无决策数据")
            return
        
        tracker.record_decision({
            'stocks': final_decision
        })
    
    elif args.track:
        tracker.track_progress()
    
    elif args.report:
        tracker.generate_report(args.decision_id)
    
    elif args.optimize:
        tracker.optimize_weights()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
