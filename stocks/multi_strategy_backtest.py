#!/usr/bin/env python3
"""
多策略批量回测系统

支持策略:
1. 多因子选股 (Multi-Factor)
2. 指数增强 (Index Enhancement)
3. 日内回转交易 (T+0)
4. 海龟交易法 (Turtle Trading)
5. 行业轮动 (Sector Rotation)
6. 机器学习 (Machine Learning)

用法:
    python3 multi_strategy_backtest.py --all     # 回测所有策略
    python3 multi_strategy_backtest.py --strategy turtle  # 回测海龟策略
"""

import json
import sys
import time
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import math

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


class MultiStrategyBacktester:
    """多策略回测器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.results_dir = Path(__file__).parent / 'backtest_results'
        self.results_dir.mkdir(exist_ok=True)
        
        # 策略列表
        self.strategies = {
            'multi_factor': '多因子选股',
            'index_enhance': '指数增强',
            'intraday_t0': '日内回转交易',
            'turtle': '海龟交易法',
            'sector_rotation': '行业轮动',
            'ml_strategy': '机器学习',
        }
        
        # 基准指数 (简化版，使用全市场平均)
        self.benchmark_return = 0
    
    def load_stock_data(self, symbol: str) -> Optional[List[Dict]]:
        """加载单只股票数据"""
        month_dirs = sorted([d for d in self.cache_dir.iterdir() if d.is_dir()], reverse=True)
        
        for month_dir in month_dirs:
            filepath = month_dir / f'{symbol}.json'
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return data.get('data', [])
                except:
                    continue
        return None
    
    def get_stock_info(self, symbol: str) -> Dict:
        """获取股票基本信息 (简化版)"""
        # 根据代码判断行业
        code = symbol
        if code.startswith('688'):
            sector = '科创板'
        elif code.startswith('300') or code.startswith('301'):
            sector = '创业板'
        elif code.startswith('600') or code.startswith('601') or code.startswith('603') or code.startswith('605'):
            sector = '沪市主板'
        else:
            sector = '深市主板'
        
        return {'symbol': symbol, 'sector': sector}
    
    def calc_ma(self, data: List[Dict], period: int, idx: int) -> Optional[float]:
        """计算移动平均线"""
        if idx < period - 1:
            return None
        return sum(data[i]['收盘'] for i in range(idx-period+1, idx+1)) / period
    
    def calc_rsi(self, data: List[Dict], period: int, idx: int) -> Optional[float]:
        """计算 RSI"""
        if idx < period:
            return None
        
        gains, losses = [], []
        for i in range(idx-period+1, idx+1):
            change = data[i]['收盘'] - data[i-1]['收盘']
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calc_atr(self, data: List[Dict], period: int, idx: int) -> Optional[float]:
        """计算 ATR (平均真实波动幅度)"""
        if idx < period:
            return None
        
        tr_values = []
        for i in range(idx-period+1, idx+1):
            high = data[i]['高'] if '高' in data[i] else data[i]['最高']
            low = data[i]['低'] if '低' in data[i] else data[i]['最低']
            prev_close = data[i-1]['收盘']
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)
        
        return sum(tr_values) / period
    
    # ==================== 策略 1: 多因子选股 ====================
    
    def backtest_multi_factor(self, data: List[Dict]) -> Dict:
        """
        多因子选股策略
        
        因子:
        1. 动量因子 (近 20 日涨幅)
        2. 价值因子 (RSI 超卖)
        3. 趋势因子 (价格>MA20>MA60)
        4. 波动因子 (ATR 较低)
        
        评分系统: 每个因子 0-1 分，总分>2.5 买入
        """
        if len(data) < 100:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        capital = initial_capital
        shares = 0
        trades = []
        holding = False
        buy_price = 0
        
        for i in range(60, len(data)):
            # 因子 1: 动量因子 (近 20 日涨幅)
            momentum = (data[i]['收盘'] - data[i-20]['收盘']) / data[i-20]['收盘']
            momentum_score = min(max((momentum + 0.1) / 0.2, 0), 1)  # 归一化到 0-1
            
            # 因子 2: 价值因子 (RSI 超卖)
            rsi = self.calc_rsi(data, 14, i)
            if rsi:
                value_score = 1 - (rsi / 100)  # RSI 越低分越高
            else:
                value_score = 0.5
            
            # 因子 3: 趋势因子
            ma20 = self.calc_ma(data, 20, i)
            ma60 = self.calc_ma(data, 60, i)
            price = data[i]['收盘']
            if ma20 and ma60:
                trend_score = 1 if (price > ma20 > ma60) else (0.5 if price > ma60 else 0)
            else:
                trend_score = 0.5
            
            # 因子 4: 波动因子 (简化版)
            volatility_score = 0.5  # 简化处理
            
            # 综合评分
            total_score = momentum_score + value_score + trend_score + volatility_score
            
            # 交易信号
            if not holding and total_score > 2.5:
                buy_price = data[i]['收盘']
                shares = int(capital * 0.95 / buy_price / 100) * 100
                if shares > 0:
                    cost = shares * buy_price * 1.0003
                    capital -= cost
                    holding = True
                    trades.append({'date': data[i]['日期'], 'type': '买入', 'price': buy_price, 'score': total_score})
            
            elif holding and (total_score < 1.5 or (data[i]['收盘'] - buy_price) / buy_price < -0.10):
                sell_price = data[i]['收盘']
                revenue = shares * sell_price * 0.9997
                capital += revenue
                profit = ((sell_price - buy_price) / buy_price) * 100
                trades.append({'date': data[i]['日期'], 'type': '卖出', 'price': sell_price, 'profit': profit})
                shares = 0
                holding = False
        
        # 最终资产
        if shares > 0:
            final_value = capital + shares * data[-1]['收盘'] * 0.9997
        else:
            final_value = capital
        
        total_return = ((final_value / initial_capital) - 1) * 100
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_count': len(trades),
            'trades': trades,
        }
    
    # ==================== 策略 2: 指数增强 ====================
    
    def backtest_index_enhance(self, data: List[Dict]) -> Dict:
        """
        指数增强策略
        
        思路:
        1. 80% 资金跟踪基准 (简化为持有)
        2. 20% 资金主动管理 (均线策略增强)
        3. 目标：跑赢基准 3-5%
        """
        if len(data) < 100:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        base_capital = initial_capital * 0.8  # 80% 跟踪基准
        active_capital = initial_capital * 0.2  # 20% 主动管理
        
        # 主动管理部分
        active_shares = 0
        active_holding = False
        active_buy_price = 0
        active_trades = []
        
        for i in range(60, len(data)):
            ma20 = self.calc_ma(data, 20, i)
            ma60 = self.calc_ma(data, 60, i)
            
            if ma20 and ma60:
                # 金叉买入
                if not active_holding and ma20 > ma60:
                    active_buy_price = data[i]['收盘']
                    active_shares = int(active_capital * 0.95 / active_buy_price / 100) * 100
                    if active_shares > 0:
                        cost = active_shares * active_buy_price * 1.0003
                        active_capital -= cost
                        active_holding = True
                        active_trades.append({'date': data[i]['日期'], 'type': '买入', 'price': active_buy_price})
                
                # 死叉卖出
                elif active_holding and ma20 < ma60:
                    sell_price = data[i]['收盘']
                    revenue = active_shares * sell_price * 0.9997
                    active_capital += revenue
                    profit = ((sell_price - active_buy_price) / active_buy_price) * 100
                    active_trades.append({'date': data[i]['日期'], 'type': '卖出', 'price': sell_price, 'profit': profit})
                    active_shares = 0
                    active_holding = False
        
        # 最终资产
        base_value = base_capital * (data[-1]['收盘'] / data[0]['收盘'])  # 基准收益
        
        if active_shares > 0:
            active_value = active_capital + active_shares * data[-1]['收盘'] * 0.9997
        else:
            active_value = active_capital
        
        final_value = base_value + active_value
        total_return = ((final_value / initial_capital) - 1) * 100
        
        # 基准收益 (简化)
        benchmark_return = ((data[-1]['收盘'] - data[0]['收盘']) / data[0]['收盘']) * 100
        alpha = total_return - benchmark_return
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'benchmark_return': benchmark_return,
            'alpha': alpha,
            'trade_count': len(active_trades),
            'trades': active_trades,
        }
    
    # ==================== 策略 3: 日内回转交易 (T+0) ====================
    
    def backtest_intraday_t0(self, data: List[Dict]) -> Dict:
        """
        日内回转交易策略 (简化版)
        
        思路:
        1. 底仓持有
        2. 日内低买高卖
        3. 利用波动获利
        
        注意：A 股是 T+1，这里模拟理想 T+0 环境
        """
        if len(data) < 100:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        capital = initial_capital
        base_shares = 0
        trades = []
        daily_profit = []
        
        # 建仓
        base_shares = int(capital * 0.5 / data[0]['收盘'] / 100) * 100
        cost = base_shares * data[0]['收盘'] * 1.0003
        capital -= cost
        
        # 日内交易
        for i in range(1, len(data)):
            high = data[i]['高'] if '高' in data[i] else data[i]['最高']
            low = data[i]['低'] if '低' in data[i] else data[i]['最低']
            open_price = data[i]['开盘']
            close_price = data[i]['收盘']
            
            # 简化：如果日内波动>3%，进行交易
            intraday_range = (high - low) / open_price
            
            if intraday_range > 0.03:
                # 低买高卖
                trade_shares = base_shares // 2
                buy_price = low
                sell_price = high
                
                # 买入
                buy_cost = trade_shares * buy_price * 1.0003
                capital -= buy_cost
                
                # 卖出
                sell_revenue = trade_shares * sell_price * 0.9997
                capital += sell_revenue
                
                profit = ((sell_price - buy_price) / buy_price) * 100
                trades.append({'date': data[i]['日期'], 'profit': profit, 'range': intraday_range})
                daily_profit.append(profit * trade_shares * buy_price / 10000)  # 万元
        
        # 最终资产
        final_value = capital + base_shares * data[-1]['收盘'] * 0.9997
        total_return = ((final_value / initial_capital) - 1) * 100
        
        avg_daily_profit = statistics.mean(daily_profit) if daily_profit else 0
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_count': len(trades),
            'avg_daily_profit': avg_daily_profit,
            'trades': trades,
        }
    
    # ==================== 策略 4: 海龟交易法 ====================
    
    def backtest_turtle(self, data: List[Dict]) -> Dict:
        """
        海龟交易法则
        
        规则:
        1. 突破 20 日高点买入
        2. 跌破 10 日低点卖出
        3. ATR 计算仓位
        4. 加仓：每上涨 0.5ATR 加仓一次
        """
        if len(data) < 100:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        capital = initial_capital
        shares = 0
        trades = []
        holding = False
        buy_price = 0
        highest = 0
        
        for i in range(60, len(data)):
            # 计算 20 日高点和 10 日低点
            high_20 = max(data[j]['高'] if '高' in data[j] else data[j]['最高'] for j in range(i-20, i))
            low_10 = min(data[j]['低'] if '低' in data[j] else data[j]['最低'] for j in range(i-10, i))
            
            # 计算 ATR
            atr = self.calc_atr(data, 14, i)
            if not atr:
                atr = data[i]['收盘'] * 0.02  # 简化：假设 ATR 为 2%
            
            current_price = data[i]['收盘']
            
            # 突破买入
            if not holding and current_price > high_20:
                # 计算仓位 (1% 风险)
                risk = capital * 0.01
                unit = int(risk / (atr * 100)) * 100
                shares = max(unit, 100)
                
                buy_price = current_price
                cost = shares * buy_price * 1.0003
                capital -= cost
                holding = True
                highest = buy_price
                trades.append({'date': data[i]['日期'], 'type': '买入', 'price': buy_price, 'atr': atr})
            
            # 持有中
            elif holding:
                # 更新最高点
                if current_price > highest:
                    highest = current_price
                
                # 止损：跌破买入价 -2ATR
                if current_price < buy_price - 2 * atr:
                    sell_price = current_price
                    revenue = shares * sell_price * 0.9997
                    capital += revenue
                    profit = ((sell_price - buy_price) / buy_price) * 100
                    trades.append({'date': data[i]['日期'], 'type': '卖出', 'price': sell_price, 'profit': profit, 'reason': '止损'})
                    shares = 0
                    holding = False
                
                # 止盈：跌破 10 日低点
                elif current_price < low_10:
                    sell_price = current_price
                    revenue = shares * sell_price * 0.9997
                    capital += revenue
                    profit = ((sell_price - buy_price) / buy_price) * 100
                    trades.append({'date': data[i]['日期'], 'type': '卖出', 'price': sell_price, 'profit': profit, 'reason': '趋势反转'})
                    shares = 0
                    holding = False
        
        # 最终资产
        if shares > 0:
            final_value = capital + shares * data[-1]['收盘'] * 0.9997
        else:
            final_value = capital
        
        total_return = ((final_value / initial_capital) - 1) * 100
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_count': len(trades),
            'trades': trades,
        }
    
    # ==================== 策略 5: 行业轮动 ====================
    
    def backtest_sector_rotation(self, all_stock_data: Dict[str, List[Dict]]) -> Dict:
        """
        行业轮动策略
        
        思路:
        1. 按行业分组
        2. 选择强势行业 (近 20 日涨幅前 3)
        3. 行业内选择龙头股
        4. 每月调仓
        
        简化版：使用板块代表股
        """
        # 简化版：使用全市场动量排序
        initial_capital = 100000
        capital = initial_capital
        trades = []
        holdings = []
        
        # 简化：每月调仓
        rebalance_days = 20
        
        for i in range(60, len(list(all_stock_data.values())[0]), rebalance_days):
            # 计算所有股票动量
            stock_momentum = []
            for symbol, data in all_stock_data.items():
                if i < len(data) and i-20 >= 0:
                    momentum = (data[i]['收盘'] - data[i-20]['收盘']) / data[i-20]['收盘']
                    stock_momentum.append({'symbol': symbol, 'momentum': momentum, 'data': data})
            
            # 选择前 10 只
            stock_momentum.sort(key=lambda x: x['momentum'], reverse=True)
            top_stocks = stock_momentum[:10]
            
            # 调仓
            if holdings:
                # 卖出旧持仓
                for h in holdings:
                    sell_price = h['data'][i]['收盘']
                    revenue = h['shares'] * sell_price * 0.9997
                    capital += revenue
                    profit = ((sell_price - h['buy_price']) / h['buy_price']) * 100
                    trades.append({'date': data[i]['日期'], 'type': '卖出', 'symbol': h['symbol'], 'profit': profit})
                holdings = []
            
            # 买入新持仓
            position_size = capital / len(top_stocks)
            for stock in top_stocks:
                buy_price = stock['data'][i]['收盘']
                shares = int(position_size * 0.95 / buy_price / 100) * 100
                if shares > 0:
                    cost = shares * buy_price * 1.0003
                    capital -= cost
                    holdings.append({
                        'symbol': stock['symbol'],
                        'shares': shares,
                        'buy_price': buy_price,
                        'data': stock['data'],
                    })
                    trades.append({'date': stock['data'][i]['日期'], 'type': '买入', 'symbol': stock['symbol'], 'price': buy_price})
        
        # 最终资产
        final_value = capital
        for h in holdings:
            if len(h['data']) > 0:
                final_value += h['shares'] * h['data'][-1]['收盘'] * 0.9997
        
        total_return = ((final_value / initial_capital) - 1) * 100
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_count': len(trades),
            'trades': trades,
        }
    
    # ==================== 策略 6: 机器学习 ====================
    
    def backtest_ml_strategy(self, data: List[Dict]) -> Dict:
        """
        机器学习策略 (简化版)
        
        使用技术指标作为特征:
        1. MA5/MA20 比值
        2. RSI
        3. 成交量变化
        4. 价格动量
        
        简化：使用规则模拟 ML 模型
        """
        if len(data) < 100:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        capital = initial_capital
        shares = 0
        trades = []
        holding = False
        buy_price = 0
        
        for i in range(60, len(data)):
            # 特征计算
            ma5 = self.calc_ma(data, 5, i)
            ma20 = self.calc_ma(data, 20, i)
            rsi = self.calc_rsi(data, 14, i)
            
            if ma5 and ma20:
                ma_ratio = ma5 / ma20
            else:
                ma_ratio = 1
            
            volume_change = data[i]['成交量'] / (sum(data[j]['成交量'] for j in range(i-20, i)) / 20) if i >= 20 else 1
            
            # 简化 ML 模型 (规则模拟)
            # 买入信号：MA5>MA20 and RSI>50 and 成交量放大
            buy_signal = (ma_ratio > 1.02) and (rsi and rsi > 50) and (volume_change > 1.2)
            
            # 卖出信号：MA5<MA20 or RSI<40 or 亏损>10%
            sell_signal = (ma_ratio < 0.98) or (rsi and rsi < 40) or (holding and (data[i]['收盘'] - buy_price) / buy_price < -0.10)
            
            if not holding and buy_signal:
                buy_price = data[i]['收盘']
                shares = int(capital * 0.95 / buy_price / 100) * 100
                if shares > 0:
                    cost = shares * buy_price * 1.0003
                    capital -= cost
                    holding = True
                    trades.append({'date': data[i]['日期'], 'type': '买入', 'price': buy_price, 'ma_ratio': ma_ratio, 'rsi': rsi})
            
            elif holding and sell_signal:
                sell_price = data[i]['收盘']
                revenue = shares * sell_price * 0.9997
                capital += revenue
                profit = ((sell_price - buy_price) / buy_price) * 100
                trades.append({'date': data[i]['日期'], 'type': '卖出', 'price': sell_price, 'profit': profit})
                shares = 0
                holding = False
        
        # 最终资产
        if shares > 0:
            final_value = capital + shares * data[-1]['收盘'] * 0.9997
        else:
            final_value = capital
        
        total_return = ((final_value / initial_capital) - 1) * 100
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_count': len(trades),
            'trades': trades,
        }
    
    # ==================== 批量回测 ====================
    
    def backtest_all_strategies(self, sample_size: int = 100) -> Dict:
        """
        批量回测所有策略
        
        Args:
            sample_size: 抽样股票数量
        """
        print('='*70)
        print('多策略批量回测系统')
        print('='*70)
        print()
        
        # 获取股票列表
        stock_files = []
        month_dirs = sorted([d for d in self.cache_dir.iterdir() if d.is_dir()], reverse=True)
        
        if month_dirs:
            latest_dir = month_dirs[0]
            stock_files = [f.stem for f in latest_dir.glob('*.json') if f.is_file()]
        
        # 抽样
        if sample_size and len(stock_files) > sample_size:
            import random
            stock_files = random.sample(stock_files, sample_size)
        
        print(f'回测股票数：{len(stock_files)}')
        print()
        
        # 回测结果
        results = {strategy: [] for strategy in self.strategies.keys()}
        
        start_time = time.time()
        
        for i, symbol in enumerate(stock_files):
            try:
                data = self.load_stock_data(symbol)
                if not data or len(data) < 100:
                    continue
                
                # 策略 1: 多因子选股
                result = self.backtest_multi_factor(data)
                if 'error' not in result:
                    results['multi_factor'].append({'symbol': symbol, **result})
                
                # 策略 2: 指数增强
                result = self.backtest_index_enhance(data)
                if 'error' not in result:
                    results['index_enhance'].append({'symbol': symbol, **result})
                
                # 策略 3: 日内回转
                result = self.backtest_intraday_t0(data)
                if 'error' not in result:
                    results['intraday_t0'].append({'symbol': symbol, **result})
                
                # 策略 4: 海龟交易
                result = self.backtest_turtle(data)
                if 'error' not in result:
                    results['turtle'].append({'symbol': symbol, **result})
                
                # 策略 5: 行业轮动 (需要全量数据，跳过单只股票)
                # 策略 6: 机器学习
                result = self.backtest_ml_strategy(data)
                if 'error' not in result:
                    results['ml_strategy'].append({'symbol': symbol, **result})
                
                # 进度
                if (i + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    print(f'进度：{i+1}/{len(stock_files)} (耗时：{elapsed:.1f}秒)')
                    
            except Exception as e:
                continue
        
        elapsed = time.time() - start_time
        
        # 统计分析
        summary = {}
        for strategy, strategy_results in results.items():
            if strategy_results:
                returns = [r['total_return'] for r in strategy_results]
                summary[strategy] = {
                    'name': self.strategies[strategy],
                    'stock_count': len(strategy_results),
                    'avg_return': statistics.mean(returns),
                    'median_return': statistics.median(returns),
                    'max_return': max(returns),
                    'min_return': min(returns),
                    'profitable_count': len([r for r in strategy_results if r['total_return'] > 0]),
                }
        
        # 打印结果
        print()
        print('='*70)
        print('回测结果汇总')
        print('='*70)
        print()
        print(f'总耗时：{elapsed:.1f}秒')
        print()
        print(f'{"策略":<20} {"股票数":>8} {"平均收益":>12} {"中位收益":>12} {"盈利":>8}')
        print('-'*70)
        
        for strategy, stats in summary.items():
            print(f"{stats['name']:<20} {stats['stock_count']:>8} {stats['avg_return']:>+11.2f}% {stats['median_return']:>+11.2f}% {stats['profitable_count']:>6}/{stats['stock_count']}")
        
        print('='*70)
        
        # 保存结果
        output_file = self.results_dir / f'multi_strategy_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f'\n结果已保存：{output_file}')
        
        return summary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='多策略批量回测')
    parser.add_argument('--all', action='store_true', help='回测所有策略')
    parser.add_argument('--strategy', type=str, help='回测特定策略')
    parser.add_argument('--sample', type=int, default=100, help='抽样股票数量')
    
    args = parser.parse_args()
    
    backtester = MultiStrategyBacktester()
    
    if args.all:
        backtester.backtest_all_strategies(sample_size=args.sample)
    else:
        print('请使用 --all 参数回测所有策略')


if __name__ == '__main__':
    main()
