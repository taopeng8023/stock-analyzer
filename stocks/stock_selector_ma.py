#!/usr/bin/env python3
"""
双均线策略选股器 - 五重过滤增强版

功能:
- 扫描全 A 股，筛选符合双均线金叉的股票
- 五重过滤条件避免伪金叉
- 输出符合条件的股票列表

五重过滤:
1. 成交量过滤 - 放量 1.5 倍以上
2. 趋势过滤 - 价格>MA200
3. RSI 过滤 - RSI 在 50-75 强势区
4. MACD 确认 - MACD 同步金叉
5. 均线斜率 - MA5 和 MA20 向上

用法:
    python3 stock_selector_ma.py --scan     # 扫描全市场
    python3 stock_selector_ma.py --check 600089  # 检查单只股票
"""

import requests
import json
import time
import math
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 配置
CACHE_DIR = Path(__file__).parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

# 五重过滤配置
FILTER_CONFIG = {
    'volume_multiplier': 1.5,    # 成交量倍数
    'rsi_min': 50,               # RSI 最小值
    'rsi_max': 75,               # RSI 最大值
    'ma_slope_days': 3,          # 均线斜率天数
    'strict_mode': 'medium',     # loose/medium/strict
}


class EnhancedMASelector:
    """增强版均线选股器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def fetch_kline(self, symbol: str, count: int = 250) -> Optional[List[Dict]]:
        """获取 K 线数据"""
        try:
            url = f'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={count}'
            resp = self.session.get(url, timeout=10)
            data = resp.json()
            
            if data and len(data) > 0:
                # 处理数据
                for k in data:
                    k['open'] = float(k['open'])
                    k['close'] = float(k['close'])
                    k['high'] = float(k['high'])
                    k['low'] = float(k['low'])
                    k['volume'] = int(k['volume'])
                
                # 计算涨跌幅
                for i in range(1, len(data)):
                    data[i]['change'] = ((data[i]['close'] - data[i-1]['close']) / data[i-1]['close']) * 100
                data[0]['change'] = 0.0
                
                return data
            return None
        except Exception as e:
            return None
    
    def calc_ma(self, data: List[Dict], period: int, idx: int = -1) -> Optional[float]:
        """计算移动平均线"""
        if idx < 0:
            idx = len(data) + idx
        if idx < period - 1:
            return None
        return sum(data[i]['close'] for i in range(idx-period+1, idx+1)) / period
    
    def calc_ma_volume(self, data: List[Dict], period: int, idx: int = -1) -> Optional[float]:
        """计算成交量均线"""
        if idx < 0:
            idx = len(data) + idx
        if idx < period - 1:
            return None
        return sum(data[i]['volume'] for i in range(idx-period+1, idx+1)) / period
    
    def calc_rsi(self, data: List[Dict], period: int = 14, idx: int = -1) -> Optional[float]:
        """计算 RSI"""
        if idx < 0:
            idx = len(data) + idx
        if idx < period:
            return None
        
        gains, losses = [], []
        for i in range(idx-period+1, idx+1):
            change = data[i]['close'] - data[i-1]['close']
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calc_ema(self, data: List[Dict], period: int, idx: int = -1) -> Optional[float]:
        """计算指数均线"""
        if idx < 0:
            idx = len(data) + idx
        if idx < period - 1:
            return None
        
        multiplier = 2 / (period + 1)
        ema = data[idx-period+1]['close']
        for i in range(idx-period+2, idx+1):
            ema = (data[i]['close'] - ema) * multiplier + ema
        return ema
    
    def calc_macd(self, data: List[Dict], fast: int = 12, slow: int = 26, signal: int = 9, idx: int = -1) -> Tuple:
        """计算 MACD"""
        if idx < 0:
            idx = len(data) + idx
        if idx < slow + signal - 1:
            return None, None, None
        
        ema_fast = self.calc_ema(data, fast, idx)
        ema_slow = self.calc_ema(data, slow, idx)
        
        if ema_fast is None or ema_slow is None:
            return None, None, None
        
        macd_line = ema_fast - ema_slow
        
        # 计算信号线
        macd_values = []
        for i in range(slow-1, idx+1):
            ef = self.calc_ema(data, fast, i)
            es = self.calc_ema(data, slow, i)
            if ef and es:
                macd_values.append(ef - es)
        
        if len(macd_values) < signal:
            return None, None, None
        
        signal_line = sum(macd_values[-signal:]) / signal
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def check_golden_cross(self, data: List[Dict], strict_mode: str = 'medium') -> Tuple[bool, Dict]:
        """
        检查五重过滤金叉信号
        
        Returns:
            (是否金叉，详细信息)
        """
        if len(data) < 200:
            return False, {'reason': '数据不足'}
        
        idx = len(data) - 1
        details = {
            'golden_cross': False,
            'volume_ok': False,
            'trend_ok': False,
            'rsi_ok': False,
            'macd_ok': False,
            'slope_ok': False,
            'score': 0,
            'max_score': 5,
            'threshold': 0.6,
            'passed': False,
        }
        
        # 基础金叉
        ma5 = self.calc_ma(data, 5, idx)
        ma20 = self.calc_ma(data, 20, idx)
        ma5_prev = self.calc_ma(data, 5, idx-1)
        ma20_prev = self.calc_ma(data, 20, idx-1)
        
        if ma5_prev > ma20_prev or ma5 <= ma20:
            return False, details
        
        details['golden_cross'] = True
        
        # 1. 成交量过滤
        volume = data[idx]['volume']
        volume_ma20 = self.calc_ma_volume(data, 20, idx)
        if volume_ma20 and volume > volume_ma20 * FILTER_CONFIG['volume_multiplier']:
            details['volume_ok'] = True
            details['score'] += 1
        
        # 2. 趋势过滤 (价格 > MA200)
        ma200 = self.calc_ma(data, 200, idx)
        if ma200 and data[idx]['close'] > ma200:
            details['trend_ok'] = True
            details['score'] += 1
        
        # 3. RSI 过滤
        rsi = self.calc_rsi(data, 14, idx)
        if rsi and FILTER_CONFIG['rsi_min'] < rsi < FILTER_CONFIG['rsi_max']:
            details['rsi_ok'] = True
            details['score'] += 1
        
        # 4. MACD 确认
        macd, signal, histogram = self.calc_macd(data, idx=idx)
        if macd and signal and macd > signal and histogram > 0:
            details['macd_ok'] = True
            details['score'] += 1
        
        # 5. 均线斜率
        slope_days = FILTER_CONFIG['ma_slope_days']
        ma5_prev_n = self.calc_ma(data, 5, idx-slope_days)
        ma20_prev_n = self.calc_ma(data, 20, idx-slope_days)
        if ma5_prev_n and ma20_prev_n:
            if ma5 > ma5_prev_n and ma20 > ma20_prev_n:
                details['slope_ok'] = True
                details['score'] += 1
        
        # 根据模式判断
        thresholds = {
            'loose': 0.4,    # 40% 条件
            'medium': 0.6,   # 60% 条件
            'strict': 0.8,   # 80% 条件
        }
        threshold = thresholds.get(strict_mode, 0.6)
        
        passed = details['score'] >= details['max_score'] * threshold
        details['passed'] = passed
        details['threshold'] = threshold
        
        return passed, details
    
    def scan_market(self, symbols: List[str], max_workers: int = 100) -> List[Dict]:
        """扫描市场"""
        print(f'开始扫描 {len(symbols)} 只股票...')
        print(f'过滤模式：{FILTER_CONFIG["strict_mode"]}')
        print(f'成交量倍数：{FILTER_CONFIG["volume_multiplier"]}x')
        print(f'RSI 区间：{FILTER_CONFIG["rsi_min"]}-{FILTER_CONFIG["rsi_max"]}')
        print()
        
        results = []
        
        for i, symbol in enumerate(symbols):
            try:
                # 获取 K 线
                data = self.fetch_kline(symbol)
                if not data or len(data) < 200:
                    continue
                
                # 检查金叉
                passed, details = self.check_golden_cross(data, FILTER_CONFIG['strict_mode'])
                
                if passed:
                    current = data[-1]
                    result = {
                        'symbol': symbol,
                        'name': self._get_name(symbol),
                        'price': current['close'],
                        'change': current['change'],
                        'volume': current['volume'],
                        'ma5': details.get('ma5', self.calc_ma(data, 5)),
                        'ma20': details.get('ma20', self.calc_ma(data, 20)),
                        'ma200': self.calc_ma(data, 200),
                        'rsi': self.calc_rsi(data, 14),
                        'score': details['score'],
                        'max_score': details['max_score'],
                        'filters': details,
                    }
                    results.append(result)
                    print(f"✅ {symbol} {result['name']} ¥{current['close']:.2f} {current['change']:+.2f}% "
                          f"评分:{details['score']}/{details['max_score']}")
                
                # 进度
                if (i + 1) % 50 == 0:
                    print(f'进度：{i+1}/{len(symbols)} ...')
                
                # 限速
                if (i + 1) % 10 == 0:
                    time.sleep(0.1)
                    
            except Exception as e:
                continue
        
        return results
    
    def _get_name(self, symbol: str) -> str:
        """获取股票名称（简化版）"""
        # 实际应用中可以从数据中获取
        return symbol


def generate_a_share_symbols() -> List[str]:
    """生成 A 股代码列表"""
    symbols = []
    
    # 深交所 (00, 30)
    for i in range(1, 10000):
        code = f'{i:06d}'
        if code.startswith('0') or code.startswith('3'):
            symbols.append(f'sz{code}')
    
    # 上交所 (60, 68)
    for i in range(1, 10000):
        code = f'{i:06d}'
        if code.startswith('6'):
            symbols.append(f'sh{code}')
    
    return symbols[:500]  # 限制数量用于测试


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='双均线选股器 - 五重过滤')
    parser.add_argument('--scan', action='store_true', help='扫描全市场')
    parser.add_argument('--check', type=str, help='检查单只股票')
    parser.add_argument('--mode', choices=['loose', 'medium', 'strict'], default='medium',
                       help='过滤模式')
    parser.add_argument('--volume', type=float, default=1.5, help='成交量倍数')
    
    args = parser.parse_args()
    
    # 更新配置
    FILTER_CONFIG['strict_mode'] = args.mode
    FILTER_CONFIG['volume_multiplier'] = args.volume
    
    selector = EnhancedMASelector()
    
    if args.check:
        # 检查单只股票
        symbol = args.check
        if not symbol.startswith('sh') and not symbol.startswith('sz'):
            if symbol.startswith('6'):
                symbol = f'sh{symbol}'
            else:
                symbol = f'sz{symbol}'
        
        print(f'检查股票：{symbol}')
        print('='*80)
        
        data = selector.fetch_kline(symbol)
        if not data:
            print('❌ 获取数据失败')
            return
        
        passed, details = selector.check_golden_cross(data, args.mode)
        
        print(f'数据条数：{len(data)}')
        print(f'当前价格：¥{data[-1]["close"]:.2f}')
        print(f'涨跌幅：{data[-1]["change"]:+.2f}%')
        print()
        print('五重过滤检查:')
        print(f'  1. 基础金叉：{"✅" if details["golden_cross"] else "❌"}')
        print(f'  2. 成交量：{"✅" if details["volume_ok"] else "❌"}')
        print(f'  3. 趋势 (MA200): {"✅" if details["trend_ok"] else "❌"}')
        print(f'  4. RSI: {"✅" if details["rsi_ok"] else "❌"}')
        print(f'  5. MACD: {"✅" if details["macd_ok"] else "❌"}')
        print(f'  6. 均线斜率：{"✅" if details["slope_ok"] else "❌"}')
        print()
        print(f'得分：{details["score"]}/{details["max_score"]}')
        print(f'阈值：{details["threshold"]*100:.0f}%')
        print()
        
        if passed:
            print('🎉 符合买入条件！')
        else:
            print('❌ 不符合买入条件')
        
        # 显示均线
        ma5 = selector.calc_ma(data, 5)
        ma20 = selector.calc_ma(data, 20)
        ma200 = selector.calc_ma(data, 200)
        print()
        print('均线系统:')
        print(f'  MA5:  ¥{ma5:.2f}')
        print(f'  MA20: ¥{ma20:.2f}')
        print(f'  MA200: ¥{ma200:.2f}')
        
    elif args.scan:
        # 扫描市场
        symbols = generate_a_share_symbols()
        results = selector.scan_market(symbols)
        
        print()
        print('='*80)
        print(f'扫描完成！找到 {len(results)} 只符合条件的股票')
        print('='*80)
        
        if results:
            # 按评分排序
            results.sort(key=lambda x: x['score'], reverse=True)
            
            print()
            print(f'{"排名":>4} {"代码":<8} {"名称":<12} {"价格":>8} {"涨幅":>8} {"评分":>8} {"成交量":>12}')
            print('-'*80)
            
            for i, r in enumerate(results[:50], 1):
                print(f'{i:>4} {r["symbol"]:<8} {r["name"]:<12} {r["price"]:>8.2f} '
                      f'{r["change"]:>+7.2f}% {r["score"]:>3}/{r["max_score"]} {r["volume"]:>12,}')
            
            # 保存结果
            output_file = CACHE_DIR / f'ma_golden_cross_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print()
            print(f'✅ 结果已保存：{output_file}')
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
