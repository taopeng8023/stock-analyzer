#!/usr/bin/env python3
"""
历史回测模块
使用指定股票列表 + 历史一年数据进行工作流回溯测试

用法:
    python3 historical_backtest.py --symbols 300308,300274,... --days 250
    python3 historical_backtest.py --symbols 300308,300274,... --days 250 --report
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
import time

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


class HistoricalBacktester:
    """历史回测器"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'backtest_cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://q.stock.sohu.com',
        }
    
    def get_historical_data(self, symbol: str, days: int = 250) -> list:
        """
        获取股票历史 K 线数据 (腾讯财经日线 API)
        
        Args:
            symbol: 股票代码 (如 300308)
            days: 获取天数
        
        Returns:
            list: 历史数据列表，按日期升序
        """
        # 添加市场前缀
        if symbol.startswith('6') or symbol.startswith('5'):
            full_symbol = f'sh{symbol}'
        elif symbol.startswith('0') or symbol.startswith('3') or symbol.startswith('4') or symbol.startswith('8'):
            full_symbol = f'sz{symbol}'
        else:
            full_symbol = symbol
        
        # 腾讯财经日线 API (前复权)
        url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {
            'param': f"{full_symbol},day,,,500,qfq"
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = resp.json()
            
            if data.get('code') == 0:
                kline_data = data.get('data', {})
                if full_symbol in kline_data:
                    klines = kline_data[full_symbol].get('qfqday', [])
                else:
                    klines = []
                
                result = []
                for k in klines:
                    if len(k) >= 6:
                        # 格式：[date, open, close, high, low, volume]
                        result.append({
                            'date': k[0],
                            'open': float(k[1]) if k[1] else 0,
                            'close': float(k[2]) if k[2] else 0,
                            'high': float(k[3]) if k[3] else 0,
                            'low': float(k[4]) if k[4] else 0,
                            'volume': float(k[5]) if k[5] else 0,
                        })
                
                # 返回最近 N 天
                return result[-days:] if len(result) > days else result
        except Exception as e:
            print(f"  ⚠️ 获取 {symbol} 历史数据失败：{e}")
        
        return []
    
    def get_stock_info(self, symbol: str) -> dict:
        """获取股票基本信息 (实时)"""
        if symbol.startswith('6'):
            full_symbol = f'sh{symbol}'
        else:
            full_symbol = f'sz{symbol}'
        
        url = f"http://qt.gtimg.cn/q={full_symbol}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.encoding = 'gbk'
            content = resp.text
            
            # v_sh600000="51~工商银行~600000~3.73~3.72~3.73~544082~302295~222287~321795~0.01~0.27%~...
            parts = content.split('~')
            if len(parts) >= 50:
                return {
                    'symbol': symbol,
                    'name': parts[1] if len(parts) > 1 else '',
                    'current_price': float(parts[3]) if parts[3] else 0,
                    'open': float(parts[5]) if parts[5] else 0,
                    'prev_close': float(parts[4]) if parts[4] else 0,
                    'high': float(parts[33]) if parts[33] else 0,
                    'low': float(parts[34]) if parts[34] else 0,
                    'volume': float(parts[6]) if parts[6] else 0,
                    'amount': float(parts[37]) if parts[37] else 0,
                    'change_pct': float(parts[32][:-1]) if parts[32] else 0,
                }
        except:
            pass
        
        return {'symbol': symbol, 'name': '', 'current_price': 0}
    
    def simulate_workflow_decision(self, stocks_data: list, date: str, use_financial_models: bool = False) -> list:
        """
        模拟工作流决策逻辑
        
        Args:
            stocks_data: 股票数据列表 (包含历史数据)
            date: 决策日期
            use_financial_models: 是否使用金融模型增强
        
        Returns:
            list: 决策结果 (选中的股票)
        """
        from optimization_config import (
            RATING_THRESHOLDS, BLACKLIST_SYMBOLS, WATCHLIST_SYMBOLS,
            STOP_PROFIT_LOSS_CONFIG, CONFIDENCE_ADJUSTMENTS
        )
        
        # 金融模型增强
        if use_financial_models:
            try:
                from financial_models import FinancialModelsEnsemble
                fm_ensemble = FinancialModelsEnsemble()
            except:
                fm_ensemble = None
        
        decisions = []
        
        for stock_info in stocks_data:
            symbol = stock_info.get('symbol', '')
            history = stock_info.get('history', [])
            
            # 找到决策日期的数据
            decision_data = None
            for h in history:
                if h.get('date') == date:
                    decision_data = h
                    break
            
            if not decision_data:
                continue
            
            # 获取数据
            price = decision_data.get('close', 0)
            open_price = decision_data.get('open', 0)
            high = decision_data.get('high', 0)
            low = decision_data.get('low', 0)
            volume = decision_data.get('volume', 0)
            
            # 计算涨跌幅
            if len(history) > 1:
                prev_close = None
                for i, h in enumerate(history):
                    if h.get('date') == date and i > 0:
                        prev_close = history[i-1].get('close', 0)
                        break
                if not prev_close:
                    continue
                change_pct = (price - prev_close) / prev_close * 100
            else:
                continue
            
            # 估算成交额
            amount = price * volume * 100
            
            # 综合评分 (v5.1 优化版)
            score = 0
            
            # 涨跌幅评分 (提高阈值)
            if change_pct > 7:
                score += 35
            elif change_pct > 5:
                score += 25
            elif change_pct > 3:
                score += 15
            elif change_pct > 0:
                score += 5
            
            # 成交量评分
            if volume > 50000000:
                score += 20
            elif volume > 20000000:
                score += 10
            
            # 成交额评分
            if amount > 10000000000:  # 100 亿
                score += 25
            elif amount > 5000000000:  # 50 亿
                score += 15
            elif amount > 1000000000:  # 10 亿
                score += 5
            
            # 黑名单检查 → 直接降分 70%
            if symbol in BLACKLIST_SYMBOLS:
                score = int(score * 0.3)
            # 观察名单 → 降分 40%
            elif symbol in WATCHLIST_SYMBOLS:
                score = int(score * 0.6)
            
            # 生成评级 (v5.1 优化阈值)
            appear_count = 1 if change_pct > 3 else 0  # 简化模拟
            if change_pct > 5 and volume > 30000000:
                appear_count += 1
            
            # v5.1 评级逻辑
            if (appear_count >= RATING_THRESHOLDS['strong_buy']['min_appear_count'] and 
                change_pct > RATING_THRESHOLDS['strong_buy']['min_change_pct']):
                rating = '强烈推荐'
                confidence = RATING_THRESHOLDS['strong_buy']['min_confidence']
            elif (appear_count >= RATING_THRESHOLDS['buy']['min_appear_count'] and 
                  change_pct > RATING_THRESHOLDS['buy']['min_change_pct']):
                rating = '推荐'
                confidence = RATING_THRESHOLDS['buy']['min_confidence']
            elif appear_count >= RATING_THRESHOLDS['cautious_buy']['min_appear_count']:
                rating = '谨慎推荐'
                confidence = RATING_THRESHOLDS['cautious_buy']['min_confidence']
            elif change_pct > 5:
                rating = '谨慎推荐'
                confidence = 60
            elif change_pct > 0:
                rating = '观望'
                confidence = 50
            else:
                rating = '观望'
                confidence = RATING_THRESHOLDS['hold']['min_confidence']
            
            # 黑名单/观察名单调整
            if symbol in BLACKLIST_SYMBOLS:
                rating = '观望'
                confidence = 30
            elif symbol in WATCHLIST_SYMBOLS:
                if rating == '强烈推荐':
                    rating = '推荐'
                elif rating == '推荐':
                    rating = '谨慎推荐'
                elif rating == '谨慎推荐':
                    rating = '观望'
                confidence = max(30, confidence + CONFIDENCE_ADJUSTMENTS['watchlist_penalty'])
            
            # 止盈止损 (v6.2 优化)
            if change_pct > 10:
                cfg = STOP_PROFIT_LOSS_CONFIG['high_volatility']
            elif change_pct > 5:
                cfg = STOP_PROFIT_LOSS_CONFIG['medium_volatility']
            elif change_pct > 0:
                cfg = STOP_PROFIT_LOSS_CONFIG['low_volatility']
            else:
                cfg = STOP_PROFIT_LOSS_CONFIG['negative']
            
            stop_profit = price * (1 + cfg['stop_profit_pct'])
            stop_loss = price * (1 - cfg['stop_loss_pct'])
            
            # 金融模型增强
            fm_score = None
            fm_rating = None
            if use_financial_models and fm_ensemble:
                try:
                    stock_data = {
                        'symbol': symbol,
                        'name': stock_info.get('name', ''),
                        'price': price,
                        'change_pct': change_pct,
                        'volume': volume,
                        'amount': amount,
                    }
                    fm_result = fm_ensemble.analyze(stock_data, history[-60:] if len(history) >= 60 else history)
                    fm_score = fm_result['final_score']
                    fm_rating = fm_result['rating']
                    
                    # 融合金融模型评分 (25% 权重)
                    score = int(score * 0.75 + fm_score * 0.25)
                    
                    # 金融模型评级调整
                    if fm_rating == '强烈推荐':
                        rating = '强烈推荐'
                        confidence = min(95, confidence + 10)
                    elif fm_rating == '推荐' and rating == '谨慎推荐':
                        rating = '推荐'
                        confidence = min(85, confidence + 5)
                except Exception as e:
                    pass
            
            decisions.append({
                'symbol': symbol,
                'name': stock_info.get('name', ''),
                'price': price,
                'change_pct': change_pct,
                'volume': volume,
                'amount': amount,
                'score': score,
                'rating': rating,
                'confidence': confidence,
                'stop_profit': stop_profit,
                'stop_loss': stop_loss,
                'decision_date': date,
                'is_blacklist': symbol in BLACKLIST_SYMBOLS,
                'is_watchlist': symbol in WATCHLIST_SYMBOLS,
                'fm_score': fm_score,
                'fm_rating': fm_rating,
            })
        
        # 按评分排序
        decisions.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return decisions
    
    def run_backtest(self, symbols: list, days: int = 250, top_n: int = 10, 
                     test_dates: list = None, use_financial_models: bool = False) -> dict:
        """
        运行历史回测
        
        Args:
            symbols: 股票代码列表
            days: 历史天数
            top_n: 每次决策选取的股票数量
            test_dates: 测试日期列表 (默认每月 1 次)
            use_financial_models: 是否使用金融模型增强
        
        Returns:
            dict: 回测结果
        """
        print("\n" + "="*80)
        if use_financial_models:
            print("📊 历史回测 - 工作流 v7.0 (金融模型增强)")
        else:
            print("📊 历史回测 - 工作流决策")
        print("="*80)
        print(f"股票数量：{len(symbols)} 只")
        print(f"历史天数：{days} 天")
        print(f"每次决策：Top{top_n}")
        if use_financial_models:
            print("金融模型：✅ 启用 (CAPM/Fama-French/Carhart/Black-Litterman/Risk)")
        print("="*80)
        
        # 1. 获取所有股票的历史数据
        print("\n[1/4] 获取历史数据...")
        stocks_data = []
        for i, symbol in enumerate(symbols, 1):
            print(f"  [{i}/{len(symbols)}] {symbol}...", end=" ")
            history = self.get_historical_data(symbol, days)
            info = self.get_stock_info(symbol)
            
            if history:
                stocks_data.append({
                    'symbol': symbol,
                    'name': info.get('name', ''),
                    'history': history,
                })
                print(f"✅ {len(history)} 条")
            else:
                print("❌ 失败")
            time.sleep(0.1)  # 避免请求过快
        
        if not stocks_data:
            print("❌ 无有效数据")
            return {}
        
        # 2. 生成测试日期 (每月一次)
        if not test_dates:
            all_dates = set()
            for stock in stocks_data:
                for h in stock['history']:
                    all_dates.add(h.get('date', ''))
            all_dates = sorted(list(all_dates))
            
            # 每月选一个日期
            test_dates = []
            current_month = None
            for date in all_dates:
                month = date[:7]  # YYYY-MM
                if month != current_month:
                    test_dates.append(date)
                    current_month = month
            
            # 限制测试次数
            test_dates = test_dates[-12:]  # 最近 12 个月
        
        print(f"\n[2/4] 测试日期：{len(test_dates)} 次决策")
        
        # 3. 模拟每次决策并跟踪表现
        print("\n[3/4] 模拟决策并跟踪...")
        all_decisions = []
        
        for date in test_dates:
            # 模拟决策
            decisions = self.simulate_workflow_decision(stocks_data, date, use_financial_models)
            top_decisions = decisions[:top_n]
            
            if not top_decisions:
                continue
            
            # 跟踪每只股票后续 10 天表现
            for decision in top_decisions:
                symbol = decision['symbol']
                decision_date = decision['decision_date']
                decision_price = decision['price']
                
                # 找到该股票的历史数据
                stock = next((s for s in stocks_data if s['symbol'] == symbol), None)
                if not stock:
                    continue
                
                history = stock['history']
                
                # 找到决策日期索引
                decision_idx = -1
                for i, h in enumerate(history):
                    if h.get('date') == decision_date:
                        decision_idx = i
                        break
                
                if decision_idx < 0 or decision_idx >= len(history) - 1:
                    continue
                
                # 跟踪后续 10 个交易日
                tracking = {}
                final_return = 0
                hit_stop_profit = False
                hit_stop_loss = False
                max_return = 0
                min_return = 0
                
                for day in range(1, 11):
                    if decision_idx + day >= len(history):
                        break
                    
                    day_data = history[decision_idx + day]
                    day_price = day_data.get('close', 0)
                    
                    if day_price > 0 and decision_price > 0:
                        daily_return = (day_price - decision_price) / decision_price * 100
                        
                        tracking[f'day_{day}'] = {
                            'date': day_data.get('date', ''),
                            'price': day_price,
                            'return': round(daily_return, 2),
                        }
                        
                        if daily_return > max_return:
                            max_return = daily_return
                        if daily_return < min_return:
                            min_return = daily_return
                        
                        # 检查止盈止损
                        if decision['stop_profit'] > 0 and day_price >= decision['stop_profit']:
                            hit_stop_profit = True
                            final_return = daily_return
                            break
                        if decision['stop_loss'] > 0 and day_price <= decision['stop_loss']:
                            hit_stop_loss = True
                            final_return = daily_return
                            break
                        
                        final_return = daily_return
                
                decision['tracking'] = tracking
                decision['final_return'] = round(final_return, 2)
                decision['max_return'] = round(max_return, 2)
                decision['min_return'] = round(min_return, 2)
                decision['hit_stop_profit'] = hit_stop_profit
                decision['hit_stop_loss'] = hit_stop_loss
                decision['is_win'] = final_return > 0
            
            all_decisions.extend(top_decisions)
            print(f"  ✅ {date}: {len(top_decisions)} 只")
        
        # 4. 生成回测报告
        print("\n[4/4] 生成回测报告...")
        report = self._generate_report(all_decisions)
        
        # 保存结果
        result_file = self.cache_dir / f"backtest_result_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'backtest_date': datetime.now().isoformat(),
                'symbols_count': len(symbols),
                'days': days,
                'test_dates_count': len(test_dates),
                'top_n': top_n,
                'decisions': all_decisions,
                'report': report
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 回测结果已保存：{result_file}")
        
        return {
            'decisions': all_decisions,
            'report': report
        }
    
    def _generate_report(self, decisions: list) -> dict:
        """生成回测报告 (v5.1 增强版)"""
        if not decisions:
            return {}
        
        total = len(decisions)
        wins = sum(1 for d in decisions if d.get('is_win', False))
        total_return = sum(d.get('final_return', 0) for d in decisions)
        
        # 按评级统计
        rating_stats = {}
        for d in decisions:
            rating = d.get('rating', 'unknown')
            if rating not in rating_stats:
                rating_stats[rating] = {
                    'count': 0,
                    'wins': 0,
                    'total_return': 0
                }
            rating_stats[rating]['count'] += 1
            rating_stats[rating]['total_return'] += d.get('final_return', 0)
            if d.get('is_win'):
                rating_stats[rating]['wins'] += 1
        
        # 计算各评级表现
        rating_performance = {}
        for rating, stats in rating_stats.items():
            if stats['count'] > 0:
                rating_performance[rating] = {
                    'count': stats['count'],
                    'win_rate': round(stats['wins'] / stats['count'] * 100, 2),
                    'avg_return': round(stats['total_return'] / stats['count'], 2),
                }
        
        # 黑名单/观察名单表现统计
        blacklist_decisions = [d for d in decisions if d.get('is_blacklist')]
        watchlist_decisions = [d for d in decisions if d.get('is_watchlist')]
        
        blacklist_stats = {
            'count': len(blacklist_decisions),
            'wins': sum(1 for d in blacklist_decisions if d.get('is_win')),
            'avg_return': round(sum(d.get('final_return', 0) for d in blacklist_decisions) / len(blacklist_decisions), 2) if blacklist_decisions else 0
        }
        
        watchlist_stats = {
            'count': len(watchlist_decisions),
            'wins': sum(1 for d in watchlist_decisions if d.get('is_win')),
            'avg_return': round(sum(d.get('final_return', 0) for d in watchlist_decisions) / len(watchlist_decisions), 2) if watchlist_decisions else 0
        }
        
        # 最佳/最差股票
        sorted_by_return = sorted(decisions, key=lambda x: x.get('final_return', 0), reverse=True)
        best = sorted_by_return[0] if sorted_by_return else {}
        worst = sorted_by_return[-1] if sorted_by_return else {}
        
        # 止盈止损统计
        hit_stop_profit = sum(1 for d in decisions if d.get('hit_stop_profit'))
        hit_stop_loss = sum(1 for d in decisions if d.get('hit_stop_loss'))
        
        report = {
            'total_decisions': total,
            'wins': wins,
            'losses': total - wins,
            'win_rate': round(wins / total * 100, 2) if total > 0 else 0,
            'total_return': round(total_return, 2),
            'avg_return': round(total_return / total, 2) if total > 0 else 0,
            'hit_stop_profit': hit_stop_profit,
            'hit_stop_loss': hit_stop_loss,
            'stop_ratio': round(hit_stop_profit / hit_stop_loss, 2) if hit_stop_loss > 0 else 999,
            'best_stock': {
                'symbol': best.get('symbol', ''),
                'name': best.get('name', ''),
                'return': best.get('final_return', 0),
                'date': best.get('decision_date', ''),
            },
            'worst_stock': {
                'symbol': worst.get('symbol', ''),
                'name': worst.get('name', ''),
                'return': worst.get('final_return', 0),
                'date': worst.get('decision_date', ''),
            },
            'rating_performance': rating_performance,
            'blacklist_performance': blacklist_stats,
            'watchlist_performance': watchlist_stats,
        }
        
        return report
    
    def print_report(self, report: dict, version: str = 'v8.0-Baseline', compare_baseline: bool = False):
        """
        打印回测报告
        
        Args:
            report: 回测报告数据
            version: 版本号
            compare_baseline: 是否与 v8.0 基准版对比
        """
        print("\n" + "="*80)
        if version == 'v8.0-Baseline':
            print(f"📊 历史回测报告 - 工作流 {version} 🏆 (基准版)")
        else:
            print(f"📊 历史回测报告 - 工作流 {version}")
        print("="*80)
        
        print(f"\n📈 总体表现:")
        print(f"   总决策数：{report.get('total_decisions', 0)}")
        print(f"   盈利：{report.get('wins', 0)} | 亏损：{report.get('losses', 0)}")
        print(f"   胜率：{report.get('win_rate', 0):.1f}%")
        print(f"   总收益：{report.get('total_return', 0):+.2f}%")
        print(f"   平均收益：{report.get('avg_return', 0):+.2f}% / 次")
        print(f"   触发止盈：{report.get('hit_stop_profit', 0)} 次")
        print(f"   触发止损：{report.get('hit_stop_loss', 0)} 次")
        print(f"   止盈/止损比：{report.get('stop_ratio', 0):.2f}:1")
        
        print(f"\n🏆 最佳股票:")
        best = report.get('best_stock', {})
        print(f"   {best.get('name', '')} ({best.get('symbol', '')})")
        print(f"   决策日期：{best.get('date', '')}")
        print(f"   收益：{best.get('return', 0):+.2f}%")
        
        print(f"\n📉 最差股票:")
        worst = report.get('worst_stock', {})
        print(f"   {worst.get('name', '')} ({worst.get('symbol', '')})")
        print(f"   决策日期：{worst.get('date', '')}")
        print(f"   收益：{worst.get('return', 0):+.2f}%")
        
        print(f"\n📋 评级表现:")
        print(f"   {'评级':<10} {'次数':>6} {'胜率':>10} {'平均收益':>12}")
        print(f"   {'-'*40}")
        for rating, perf in report.get('rating_performance', {}).items():
            print(f"   {rating:<10} {perf.get('count', 0):>6}次 {perf.get('win_rate', 0):>9.1f}% {perf.get('avg_return', 0):>+11.2f}%")
        
        # 黑名单/观察名单表现
        print(f"\n🚫 黑名单/观察名单机制效果:")
        bl = report.get('blacklist_performance', {})
        wl = report.get('watchlist_performance', {})
        bl_count = bl.get('count', 0)
        wl_count = wl.get('count', 0)
        if bl_count > 0:
            print(f"   黑名单：{bl_count}次 | 胜率 {bl.get('wins', 0)/bl_count*100:.1f}% | 平均收益 {bl.get('avg_return', 0):+.2f}%")
        else:
            print(f"   黑名单：0 次 (未触发)")
        if wl_count > 0:
            print(f"   观察名单：{wl_count}次 | 胜率 {wl.get('wins', 0)/wl_count*100:.1f}% | 平均收益 {wl.get('avg_return', 0):+.2f}%")
        else:
            print(f"   观察名单：0 次 (未触发)")
        
        # v8.0 基准版对比
        if compare_baseline or version != 'v8.0-Baseline':
            self._print_baseline_comparison(report, version)
        
        print("\n" + "="*80)
    
    def _print_baseline_comparison(self, report: dict, version: str):
        """
        与 v8.0 基准版对比
        
        Args:
            report: 当前回测报告
            version: 当前版本号
        """
        # v8.0 基准版数据 (基于十轮回测平均值)
        baseline = {
            'version': 'v8.0-Baseline',
            'win_rate': 48.3,
            'total_return': 148.84,
            'avg_return': 1.24,
            'stop_ratio': 0.51,
        }
        
        current_win_rate = report.get('win_rate', 0)
        current_avg_return = report.get('avg_return', 0)
        current_total_return = report.get('total_return', 0)
        current_stop_ratio = report.get('stop_ratio', 0)
        
        win_rate_diff = current_win_rate - baseline['win_rate']
        avg_return_diff = current_avg_return - baseline['avg_return']
        total_return_diff = current_total_return - baseline['total_return']
        stop_ratio_diff = current_stop_ratio - baseline['stop_ratio']
        
        print(f"\n📊 vs v8.0 基准版对比")
        print(f"   {'指标':<15} {'v8.0 基准':>12} {'当前':>12} {'差异':>12}")
        print(f"   {'-'*55}")
        print(f"   {'胜率':<15} {baseline['win_rate']:>11.1f}% {current_win_rate:>11.1f}% {win_rate_diff:>+11.1f}%")
        print(f"   {'平均收益/次':<15} {baseline['avg_return']:>11.2f}% {current_avg_return:>11.2f}% {avg_return_diff:>+11.2f}%")
        print(f"   {'总收益':<15} {baseline['total_return']:>11.2f}% {current_total_return:>11.2f}% {total_return_diff:>+11.2f}%")
        print(f"   {'止盈/止损比':<15} {baseline['stop_ratio']:>11.2f}:1 {current_stop_ratio:>11.2f}:1 {stop_ratio_diff:>+11.2f}")
        
        # 评估
        print(f"\n   📈 评估:")
        if avg_return_diff > 0.1:
            print(f"   ✅ 显著优于基准 (+{avg_return_diff:.2f}%)")
        elif avg_return_diff > 0:
            print(f"   ✅ 略优于基准 (+{avg_return_diff:.2f}%)")
        elif avg_return_diff > -0.1:
            print(f"   ⚠️ 与基准持平 ({avg_return_diff:.2f}%)")
        else:
            print(f"   ⚠️ 略低于基准 ({avg_return_diff:.2f}%)")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='历史回测模块')
    parser.add_argument('--symbols', type=str, required=True, help='股票代码列表，逗号分隔')
    parser.add_argument('--days', type=int, default=250, help='历史天数 (默认 250 交易日)')
    parser.add_argument('--top', type=int, default=10, help='每次决策选取数量')
    parser.add_argument('--report', action='store_true', help='打印报告')
    parser.add_argument('--version', type=str, default='v8.0-Baseline', help='工作流版本 (默认 v8.0 基准版)')
    parser.add_argument('--financial-models', action='store_true', help='使用金融模型增强')
    parser.add_argument('--compare-baseline', action='store_true', help='与 v8.0 基准版对比')
    
    args = parser.parse_args()
    
    # 解析股票代码
    symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
    
    if not symbols:
        print("❌ 未提供股票代码")
        return
    
    # 运行回测
    backtester = HistoricalBacktester()
    result = backtester.run_backtest(symbols, days=args.days, top_n=args.top, use_financial_models=args.financial_models)
    
    if result and args.report:
        backtester.print_report(result['report'], version=args.version, compare_baseline=args.compare_baseline)


if __name__ == '__main__':
    main()
