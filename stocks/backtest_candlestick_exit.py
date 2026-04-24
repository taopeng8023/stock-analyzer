#!/usr/bin/env python3
"""
选股策略回测 - MA15/MA20 + 蜡烛图卖出

买入信号:
1. MA15 > MA20 (趋势向上)
2. 五重过滤 (成交量 + 趋势+RSI+MACD+ 斜率)

卖出信号:
1. 看跌吞没
2. 黄昏之星
3. 乌云盖顶
4. 锤子线 (高位)
5. MA15 < MA20 (死叉止损)

用法:
    python3 backtest_candlestick_exit.py --full     # 全市场回测
    python3 backtest_candlestick_exit.py --sample 500  # 抽样回测
"""

import json
import sys
import time
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


class CandlestickPattern:
    """蜡烛图形态识别"""
    
    @staticmethod
    def is_bearish_engulfing(data: List[Dict], idx: int) -> bool:
        """
        看跌吞没形态
        
        条件:
        1. 前一天阳线，今天阴线
        2. 今天实体完全包住前一天实体
        """
        if idx < 1:
            return False
        
        today = data[idx]
        yesterday = data[idx-1]
        
        today_open = today.get('开盘', today.get('open'))
        today_close = today.get('收盘', today.get('close'))
        yesterday_open = yesterday.get('开盘', yesterday.get('open'))
        yesterday_close = yesterday.get('收盘', yesterday.get('close'))
        
        # 今天阴线
        if today_close >= today_open:
            return False
        
        # 昨天阳线
        if yesterday_close <= yesterday_open:
            return False
        
        # 今天实体包住昨天实体
        if today_open > yesterday_close and today_close < yesterday_open:
            return True
        
        return False
    
    @staticmethod
    def is_evening_star(data: List[Dict], idx: int) -> bool:
        """
        黄昏之星形态
        
        条件:
        1. 第一天大阳线
        2. 第二天小实体 (星)
        3. 第三天大阴线
        """
        if idx < 2:
            return False
        
        day1 = data[idx-2]
        day2 = data[idx-1]
        day3 = data[idx]
        
        day1_open = day1.get('开盘', day1.get('open'))
        day1_close = day1.get('收盘', day1.get('close'))
        day2_open = day2.get('开盘', day2.get('open'))
        day2_close = day2.get('收盘', day2.get('close'))
        day3_open = day3.get('开盘', day3.get('open'))
        day3_close = day3.get('收盘', day3.get('close'))
        
        # 第一天阳线
        if day1_close <= day1_open:
            return False
        
        # 第三天阴线
        if day3_close >= day3_open:
            return False
        
        # 第二天小实体
        day2_body = abs(day2_close - day2_open)
        day1_body = abs(day1_close - day1_open)
        day3_body = abs(day3_close - day3_open)
        
        if day2_body > min(day1_body, day3_body) * 0.5:
            return False
        
        # 第二天跳空
        if day2_close > day1_close and day2_open > day1_close:
            if day3_close < day2_open and day3_close < day1_close:
                return True
        
        return False
    
    @staticmethod
    def is_dark_cloud_cover(data: List[Dict], idx: int) -> bool:
        """
        乌云盖顶形态
        
        条件:
        1. 第一天阳线
        2. 第二天高开低走
        3. 第二天收盘价深入第一天实体中部
        """
        if idx < 1:
            return False
        
        today = data[idx]
        yesterday = data[idx-1]
        
        today_open = today.get('开盘', today.get('open'))
        today_close = today.get('收盘', today.get('close'))
        yesterday_open = yesterday.get('开盘', yesterday.get('open'))
        yesterday_close = yesterday.get('收盘', yesterday.get('close'))
        
        # 昨天阳线
        if yesterday_close <= yesterday_open:
            return False
        
        # 今天阴线
        if today_close >= today_open:
            return False
        
        # 今天高开
        if today_open <= yesterday_close:
            return False
        
        # 今天收盘深入昨天实体中部
        midpoint = (yesterday_open + yesterday_close) / 2
        if today_close < midpoint:
            return True
        
        return False
    
    @staticmethod
    def is_hanging_man(data: List[Dict], idx: int) -> bool:
        """
        吊颈线 (高位锤子线)
        
        条件:
        1. 小实体在顶部
        2. 下影线至少是实体 2 倍
        3. 几乎没有上影线
        4. 在上涨趋势后
        """
        if idx < 1:
            return False
        
        today = data[idx]
        today_open = today.get('开盘', today.get('open'))
        today_close = today.get('收盘', today.get('close'))
        today_high = today.get('最高', today.get('high'))
        today_low = today.get('最低', today.get('low'))
        
        # 实体
        body = abs(today_close - today_open)
        # 下影线
        lower_shadow = min(today_open, today_close) - today_low
        # 上影线
        upper_shadow = today_high - max(today_open, today_close)
        
        # 小实体
        if body > (today_high - today_low) * 0.3:
            return False
        
        # 下影线至少是实体 2 倍
        if lower_shadow < body * 2:
            return False
        
        # 几乎没有上影线
        if upper_shadow > body:
            return False
        
        # 在上涨趋势后 (简化：昨天上涨)
        yesterday = data[idx-1]
        yesterday_close = yesterday.get('收盘', yesterday.get('close'))
        yesterday_open = yesterday.get('开盘', yesterday.get('open'))
        if yesterday_close <= yesterday_open:
            return False
        
        return True
    
    @staticmethod
    def check_sell_signal(data: List[Dict], idx: int, ma15: float, ma20: float) -> tuple:
        """
        综合蜡烛图卖出信号
        
        Returns:
            (是否卖出，原因)
        """
        # 1. 死叉止损 (最高优先级)
        if idx >= 21:
            ma15_prev = sum(data[i].get('收盘', data[i].get('close')) for i in range(idx-16, idx)) / 15
            ma20_prev = sum(data[i].get('收盘', data[i].get('close')) for i in range(idx-21, idx)) / 20
            if ma15_prev >= ma20_prev and ma15 < ma20:
                return True, '死叉'
        
        # 2. 看跌吞没
        if CandlestickPattern.is_bearish_engulfing(data, idx):
            return True, '看跌吞没'
        
        # 3. 黄昏之星
        if CandlestickPattern.is_evening_star(data, idx):
            return True, '黄昏之星'
        
        # 4. 乌云盖顶
        if CandlestickPattern.is_dark_cloud_cover(data, idx):
            return True, '乌云盖顶'
        
        # 5. 吊颈线
        if CandlestickPattern.is_hanging_man(data, idx):
            return True, '吊颈线'
        
        return False, None


class MA15CandlestickBacktester:
    """MA15/MA20 + 蜡烛图卖出回测器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache' / 'history'
        self.results_dir = Path(__file__).parent / 'backtest_results'
        self.results_dir.mkdir(exist_ok=True)
        
        self.candlestick = CandlestickPattern()
    
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
    
    def calc_ma(self, data: List[Dict], period: int, idx: int) -> Optional[float]:
        """计算移动平均线"""
        if idx < period - 1:
            return None
        return sum(data[i].get('收盘', data[i].get('close')) for i in range(idx-period+1, idx+1)) / period
    
    def check_buy_conditions(self, data: List[Dict], idx: int) -> tuple:
        """
        检查买入条件
        
        Returns:
            (是否买入，评分)
        """
        if idx < 200:
            return False, 0
        
        # 1. MA15 > MA20 (基础条件)
        ma15 = self.calc_ma(data, 15, idx)
        ma20 = self.calc_ma(data, 20, idx)
        ma15_prev = self.calc_ma(data, 15, idx-1)
        ma20_prev = self.calc_ma(data, 20, idx-1)
        
        if ma15 is None or ma20 is None:
            return False, 0
        
        # MA15 在 MA20 上
        if ma15 <= ma20:
            return False, 0
        
        score = 0
        
        # 2. 成交量过滤
        volume = data[idx].get('成交量', data[idx].get('volume'))
        avg_volume = sum(data[i].get('成交量', data[i].get('volume')) for i in range(idx-20, idx)) / 20
        if volume > avg_volume * 1.5:
            score += 1
        
        # 3. 趋势过滤 (股价>MA200)
        ma200 = self.calc_ma(data, 200, idx)
        current_price = data[idx].get('收盘', data[idx].get('close'))
        if ma200 and current_price > ma200:
            score += 1
        
        # 4. RSI 过滤
        rsi = self.calc_rsi(data, 14, idx)
        if rsi and 50 < rsi < 75:
            score += 1
        
        # 5. MACD 过滤
        ema12 = self.calc_ema(data, 12, idx)
        ema26 = self.calc_ema(data, 26, idx)
        if ema12 and ema26 and ema12 > ema26:
            score += 1
        
        # 6. 均线斜率
        ma15_prev_3 = self.calc_ma(data, 15, idx-3)
        ma20_prev_3 = self.calc_ma(data, 20, idx-3)
        if ma15_prev_3 and ma20_prev_3:
            if ma15 > ma15_prev_3 and ma20 > ma20_prev_3:
                score += 1
        
        # 通过条件：至少 3 分
        if score >= 3:
            return True, score
        
        return False, score
    
    def calc_rsi(self, data: List[Dict], period: int, idx: int) -> Optional[float]:
        """计算 RSI"""
        if idx < period:
            return None
        
        gains, losses = [], []
        for i in range(idx-period+1, idx+1):
            change = data[i].get('收盘', data[i].get('close')) - data[i-1].get('收盘', data[i-1].get('close'))
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calc_ema(self, data: List[Dict], period: int, idx: int) -> Optional[float]:
        """计算 EMA"""
        if idx < period - 1:
            return None
        
        multiplier = 2 / (period + 1)
        ema = data[idx-period+1].get('收盘', data[idx-period+1].get('close'))
        for i in range(idx-period+2, idx+1):
            ema = (data[i].get('收盘', data[i].get('close')) - ema) * multiplier + ema
        return ema
    
    def backtest(self, data: List[Dict]) -> Dict:
        """
        回测策略
        
        Returns:
            回测结果
        """
        if len(data) < 200:
            return {'error': '数据不足'}
        
        initial_capital = 100000
        capital = initial_capital
        shares = 0
        trades = []
        holding = False
        buy_price = 0
        buy_date_idx = 0
        
        close_key = '收盘' if '收盘' in data[0] else 'close'
        
        for i in range(200, len(data)):
            current_price = data[i].get(close_key, 0)
            
            if not holding:
                # 检查买入条件
                buy_signal, score = self.check_buy_conditions(data, i)
                
                if buy_signal:
                    ma15 = self.calc_ma(data, 15, i)
                    ma20 = self.calc_ma(data, 20, i)
                    
                    # 确保 MA15 在 MA20 上
                    if ma15 and ma20 and ma15 > ma20:
                        buy_price = current_price
                        shares = int(capital * 0.95 / buy_price / 100) * 100
                        if shares > 0:
                            cost = shares * buy_price * 1.0003
                            capital -= cost
                            holding = True
                            buy_date_idx = i
                            trades.append({
                                'date': data[i].get('日期', data[i].get('day', '')),
                                'type': '买入',
                                'price': buy_price,
                                'score': score,
                            })
            else:
                # 检查卖出信号 (蜡烛图)
                ma15 = self.calc_ma(data, 15, i)
                ma20 = self.calc_ma(data, 20, i)
                
                sell_signal, reason = self.candlestick.check_sell_signal(data, i, ma15, ma20)
                
                if sell_signal:
                    sell_price = current_price
                    revenue = shares * sell_price * 0.9997
                    capital += revenue
                    profit = ((sell_price - buy_price) / buy_price) * 100
                    trades.append({
                        'date': data[i].get('日期', data[i].get('day', '')),
                        'type': '卖出',
                        'price': sell_price,
                        'profit': profit,
                        'reason': reason,
                    })
                    shares = 0
                    holding = False
        
        # 最终资产
        if shares > 0:
            final_value = capital + shares * data[-1].get(close_key, 0) * 0.9997
        else:
            final_value = capital
        
        total_return = ((final_value / initial_capital) - 1) * 100
        
        # 统计
        sell_trades = [t for t in trades if t['type'] == '卖出']
        winning_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(winning_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        # 计算最大回撤
        peak = initial_capital
        max_drawdown = 0
        current_capital = initial_capital
        for t in trades:
            if t['type'] == '卖出' and 'shares' in t:
                current_capital = current_capital + t['shares'] * t['price'] * 0.9997
                if current_capital > peak:
                    peak = current_capital
                drawdown = (peak - current_capital) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_count': len(trades),
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'trades': trades,
        }
    
    def validate_all_stocks(self, sample_size: int = None) -> Dict:
        """
        全市场回测验证
        
        Args:
            sample_size: 抽样数量 (None=全量)
        """
        print('='*70)
        print('MA15/MA20 + 蜡烛图卖出 全市场回测')
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
            print(f'抽样回测：{sample_size} 只股票')
        else:
            print(f'全量回测：{len(stock_files)} 只股票')
        
        print()
        
        # 回测结果
        results = []
        
        start_time = time.time()
        
        for i, symbol in enumerate(stock_files):
            try:
                data = self.load_stock_data(symbol)
                if not data or len(data) < 200:
                    continue
                
                result = self.backtest(data)
                if 'error' not in result:
                    results.append({'symbol': symbol, **result})
                
                # 进度
                if (i + 1) % 500 == 0:
                    elapsed = time.time() - start_time
                    print(f'进度：{i+1}/{len(stock_files)} (有效:{len(results)} 耗时:{elapsed:.1f}秒)')
                    
            except Exception as e:
                continue
        
        elapsed = time.time() - start_time
        
        # 统计分析
        print()
        print('='*70)
        print('回测结果汇总')
        print('='*70)
        print()
        
        if results:
            returns = [r['total_return'] for r in results]
            win_rates = [r['win_rate'] for r in results]
            drawdowns = [r['max_drawdown'] for r in results]
            
            summary = {
                'stock_count': len(results),
                'avg_return': statistics.mean(returns),
                'median_return': statistics.median(returns),
                'max_return': max(returns),
                'min_return': min(returns),
                'avg_win_rate': statistics.mean(win_rates),
                'avg_max_drawdown': statistics.mean(drawdowns),
                'profitable_count': len([r for r in results if r['total_return'] > 0]),
                'elapsed_time': elapsed,
                'timestamp': datetime.now().isoformat(),
            }
            
            # 打印结果
            print(f'回测股票数：{len(results)}')
            print(f'总耗时：{elapsed:.1f}秒')
            print()
            print(f'平均收益率：{summary["avg_return"]:+.2f}%')
            print(f'中位收益率：{summary["median_return"]:+.2f}%')
            print(f'最高收益率：{summary["max_return"]:+.2f}%')
            print(f'最低收益率：{summary["min_return"]:+.2f}%')
            print(f'平均胜率：{summary["avg_win_rate"]:.1f}%')
            print(f'平均最大回撤：{summary["avg_max_drawdown"]:.1f}%')
            print(f'盈利股票：{summary["profitable_count"]} ({summary["profitable_count"]/len(results)*100:.1f}%)')
            print()
            print('='*70)
            
            # 保存结果
            output_file = self.results_dir / f'ma15_candlestick_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f'\n结果已保存：{output_file}')
            
            return summary
        else:
            print('❌ 无有效回测结果')
            return {}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='MA15/MA20 + 蜡烛图卖出 回测')
    parser.add_argument('--sample', type=int, help='抽样数量')
    parser.add_argument('--full', action='store_true', help='全量回测')
    
    args = parser.parse_args()
    
    backtester = MA15CandlestickBacktester()
    
    if args.full:
        # 全量回测
        backtester.validate_all_stocks(sample_size=None)
    elif args.sample:
        # 抽样回测
        backtester.validate_all_stocks(sample_size=args.sample)
    else:
        # 默认抽样 500 只
        print('使用默认抽样 500 只股票 (使用 --full 全量回测 或 --sample 指定数量)')
        backtester.validate_all_stocks(sample_size=500)


if __name__ == '__main__':
    main()
