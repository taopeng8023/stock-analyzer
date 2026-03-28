#!/usr/bin/env python3
"""
双均线选股器 v2.0 - 集成多数据源 + 限频保护

功能:
- 多数据源支持 (雪球/东财/新浪/腾讯)
- 自动限频 (避免反爬)
- 数据缓存 (减少请求)
- 五重过滤 (避免伪金叉)
- 批量扫描

用法:
    python3 stock_selector_v2.py --scan          # 扫描全市场
    python3 stock_selector_v2.py --check 600152  # 检查单只股票
"""

import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 导入数据源管理器
from data_source_manager import DataSourceManager, get_data_source_manager

# 导入技术分析模块
try:
    from elliott_wave import ElliottWaveAnalyzer, elliott_wave_score
    from gann_theory import GannAnalyzer, gann_score
    from position_management import PositionManager, position_management_score
    HAS_MODULES = True
except ImportError:
    HAS_MODULES = False
    print('⚠️ 部分分析模块未找到，使用简化模式')


class EnhancedStockSelector:
    """增强版选股器"""
    
    # 五重过滤配置
    FILTER_CONFIG = {
        'volume_multiplier': 1.5,
        'rsi_min': 50,
        'rsi_max': 75,
        'ma_slope_days': 3,
        'strict_mode': 'medium',
    }
    
    def __init__(self, cache_dir: str = None):
        """
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        # 数据源管理器
        self.data_source = get_data_source_manager()
        
        # 分析器
        if HAS_MODULES:
            self.wave_analyzer = ElliottWaveAnalyzer()
            self.gann_analyzer = GannAnalyzer()
            self.position_manager = PositionManager()
    
    def calc_ma(self, data: List[Dict], period: int, idx: int = -1) -> Optional[float]:
        """计算移动平均线"""
        if idx < 0:
            idx = len(data) + idx
        if idx < period - 1:
            return None
        
        # 兼容不同数据源的字段名
        close_key = 'close' if 'close' in data[0] else '收盘'
        return sum(d.get(close_key, 0) for d in data[idx-period+1:idx+1]) / period
    
    def calc_rsi(self, data: List[Dict], period: int = 14, idx: int = -1) -> Optional[float]:
        """计算 RSI"""
        if idx < 0:
            idx = len(data) + idx
        if idx < period:
            return None
        
        # 兼容不同数据源的字段名
        close_key = 'close' if 'close' in data[0] else '收盘'
        
        gains, losses = [], []
        for i in range(idx-period+1, idx+1):
            change = data[i].get(close_key, 0) - data[i-1].get(close_key, 0)
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def check_golden_cross(self, data: List[Dict]) -> Dict:
        """
        检查五重过滤金叉信号
        
        Returns:
            {
                'golden_cross': bool,
                'volume_ok': bool,
                'trend_ok': bool,
                'rsi_ok': bool,
                'macd_ok': bool,
                'slope_ok': bool,
                'score': int,
                'max_score': 5,
            }
        """
        if len(data) < 200:
            return {'error': '数据不足'}
        
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
        }
        
        # 1. 基础金叉
        ma5 = self.calc_ma(data, 5, idx)
        ma20 = self.calc_ma(data, 20, idx)
        ma5_prev = self.calc_ma(data, 5, idx-1)
        ma20_prev = self.calc_ma(data, 20, idx-1)
        
        if ma5_prev <= ma20_prev and ma5 > ma20:
            details['golden_cross'] = True
        
        if not details['golden_cross']:
            return details
        
        # 2. 成交量过滤
        volume_key = 'volume' if 'volume' in data[0] else '成交量'
        volume = data[idx].get(volume_key, 0)
        avg_volume = sum(d.get(volume_key, 0) for d in data[idx-20:idx]) / 20
        if avg_volume > 0 and volume > avg_volume * self.FILTER_CONFIG['volume_multiplier']:
            details['volume_ok'] = True
            details['score'] += 1
        
        # 3. 趋势过滤
        ma200 = self.calc_ma(data, 200, idx)
        close_key = 'close' if 'close' in data[0] else '收盘'
        current_price = data[idx].get(close_key, 0)
        if ma200 and current_price > ma200:
            details['trend_ok'] = True
            details['score'] += 1
        
        # 4. RSI 过滤
        rsi = self.calc_rsi(data, 14, idx)
        if rsi and self.FILTER_CONFIG['rsi_min'] < rsi < self.FILTER_CONFIG['rsi_max']:
            details['rsi_ok'] = True
            details['score'] += 1
        
        # 5. MACD 确认 (简化版)
        ema12 = self.calc_ema(data, 12, idx)
        ema26 = self.calc_ema(data, 26, idx)
        if ema12 and ema26 and ema12 > ema26:
            details['macd_ok'] = True
            details['score'] += 1
        
        # 6. 均线斜率
        slope_days = self.FILTER_CONFIG['ma_slope_days']
        ma5_prev_n = self.calc_ma(data, 5, idx-slope_days)
        ma20_prev_n = self.calc_ma(data, 20, idx-slope_days)
        if ma5_prev_n and ma20_prev_n:
            if ma5 > ma5_prev_n and ma20 > ma20_prev_n:
                details['slope_ok'] = True
                details['score'] += 1
        
        # 判断是否通过
        threshold = {'loose': 0.4, 'medium': 0.6, 'strict': 0.8}
        details['passed'] = details['score'] >= 5 * threshold.get(
            self.FILTER_CONFIG['strict_mode'], 0.6
        )
        
        return details
    
    def calc_ema(self, data: List[Dict], period: int, idx: int = -1) -> Optional[float]:
        """计算指数均线"""
        if idx < 0:
            idx = len(data) + idx
        if idx < period - 1:
            return None
        
        multiplier = 2 / (period + 1)
        ema = data[idx-period+1]['收盘']
        for i in range(idx-period+2, idx+1):
            ema = (data[i]['收盘'] - ema) * multiplier + ema
        return ema
    
    def analyze_stock(self, symbol: str, fund_flow_data: Dict = None, cyq_data: Dict = None, hot_rank_data: Dict = None) -> Optional[Dict]:
        """
        分析单只股票
        
        Args:
            symbol: 股票代码
            fund_flow_data: 资金流数据 (可选)
            cyq_data: 筹码分布数据 (可选)
            hot_rank_data: 热度排名数据 (可选)
        
        Returns:
            {
                'symbol': str,
                'name': str,
                'price': float,
                'change': float,
                'score': int,
                'filters': dict,
                'fund_flow': dict,
                'cyq': dict,
                'hot_rank': dict,
                'recommendation': str,
            }
        """
        try:
            # 获取历史数据
            data = self.data_source.get_stock_history(
                symbol=symbol,
                source='auto',
                start_date='20250101',
                use_cache=True
            )
            
            if not data or len(data) < 200:
                return None
            
            # 检查金叉
            filters = self.check_golden_cross(data)
            
            if not filters.get('golden_cross'):
                return None
            
            # 计算综合评分
            score = filters['score']
            
            # 波浪理论评分
            if HAS_MODULES:
                try:
                    en_data = []
                    for d in data:
                        en_data.append({
                            'day': d.get('日期', d.get('day')),
                            'open': d.get('开盘', d.get('open')),
                            'close': d.get('收盘', d.get('close')),
                            'high': d.get('最高', d.get('high')),
                            'low': d.get('最低', d.get('low')),
                            'volume': d.get('成交量', d.get('volume')),
                        })
                    wave_data = self.wave_analyzer.identify_wave_pattern(en_data)
                    score += elliott_wave_score(wave_data) / 2
                except Exception as e:
                    pass
            
            # 江恩理论评分
            if HAS_MODULES:
                try:
                    gann_data = self.gann_analyzer.analyze(en_data)
                    score += gann_score(gann_data) / 2
                except Exception as e:
                    pass
            
            # 资金流评分
            fund_flow_score = 0
            if fund_flow_data:
                # 优先使用超大单 + 大单（更准确）
                super_large_raw = fund_flow_data.get('超大单净流入', '0')
                large_raw = fund_flow_data.get('大单净流入', '0')
                
                def parse_flow(raw):
                    if isinstance(raw, str):
                        if '亿' in raw:
                            return float(raw.replace('亿', '')) * 100000000
                        elif '万' in raw:
                            return float(raw.replace('万', '')) * 10000
                        else:
                            return float(raw or 0)
                    else:
                        return float(raw or 0)
                
                super_large = parse_flow(super_large_raw)
                large = parse_flow(large_raw)
                
                # 主力净流入 = 超大单 + 大单
                main_flow = super_large + large
                
                # 如果没有超大单/大单字段，使用净额
                if main_flow == 0:
                    net_raw = fund_flow_data.get('净额', '0')
                    main_flow = parse_flow(net_raw)
                
                # 优化：放宽资金流评分标准
                if main_flow > 100000000:  # >1 亿
                    fund_flow_score = 3
                elif main_flow > 30000000:  # >3000 万
                    fund_flow_score = 2
                elif main_flow > 5000000:  # >500 万
                    fund_flow_score = 1
                elif main_flow > 0:  # 净流入
                    fund_flow_score = 0.5
                score += fund_flow_score
            
            # 筹码分布评分 (新增)
            cyq_score_val = 0
            if cyq_data and 'data' in cyq_data:
                try:
                    chip_data = cyq_data['data']
                    prices = [item.get('筹码价', 0) for item in chip_data if item.get('筹码价')]
                    if prices:
                        prices.sort()
                        avg_price = sum(prices) / len(prices)
                        current_price = prices[-1] if prices else 0
                        
                        # 集中度
                        if len(prices) > 20:
                            p5 = prices[int(len(prices) * 0.05)]
                            p95 = prices[int(len(prices) * 0.95)]
                            concentration = (p95 - p5) / avg_price if avg_price > 0 else 1
                            
                            if concentration < 0.2:
                                cyq_score_val = 3
                            elif concentration < 0.4:
                                cyq_score_val = 2
                            else:
                                cyq_score_val = 1
                        
                        # 低位 + 集中 = 吸筹信号
                        if current_price < avg_price * 1.1 and cyq_score_val >= 2:
                            cyq_score_val += 1
                except Exception as e:
                    pass
            
            score += cyq_score_val
            
            # 股票热度评分 (新增)
            heat_score_val = 0
            if hot_rank_data and 'rank' in hot_rank_data:
                try:
                    rank = hot_rank_data['rank']
                    # 根据排名评分
                    if rank <= 55:  # 前 1%
                        heat_score_val = 1.0  # 极热，警惕
                    elif rank <= 275:  # 前 5%
                        heat_score_val = 2.0  # 高度关注
                    elif rank <= 825:  # 前 15%
                        heat_score_val = 1.5  # 适度关注 (最佳)
                    elif rank <= 2750:  # 前 50%
                        heat_score_val = 1.0  # 关注度一般
                    else:
                        heat_score_val = 0.5  # 关注度低
                except Exception as e:
                    pass
            
            score += heat_score_val
            
            # 获取最新数据
            latest = data[-1]
            
            # 兼容字段名
            close_key = 'close' if 'close' in data[0] else '收盘'
            change_key = 'change' if 'change' in data[0] else '涨跌幅'
            volume_key = 'volume' if 'volume' in data[0] else '成交量'
            
            # 生成建议 (总分 20 分)
            # 优化：降低标准，找到更多股票
            if score >= 13:
                recommendation = '强烈推荐'  # 65%
            elif score >= 10:
                recommendation = '推荐'  # 50%
            elif score >= 7:
                recommendation = '观望'  # 35%
            else:
                recommendation = '回避'  # <35%
            
            return {
                'symbol': symbol,
                'name': fund_flow_data.get('股票简称', symbol) if fund_flow_data else symbol,
                'price': latest.get(close_key, 0),
                'change': latest.get(change_key, 0),
                'volume': latest.get(volume_key, 0),
                'score': score,
                'filters': filters,
                'fund_flow': fund_flow_data,
                'cyq': cyq_data,
                'hot_rank': hot_rank_data,
                'recommendation': recommendation,
            }
            
        except Exception as e:
            print(f'分析 {symbol} 失败：{e}')
            return None
    
    def scan_market(self, symbols: List[str] = None, use_fund_flow: bool = True) -> List[Dict]:
        """
        扫描市场 (基于资金流排行)
        
        Args:
            symbols: 股票代码列表 (None 则使用资金流前 100)
            use_fund_flow: 是否使用资金流数据
        
        Returns:
            符合条件的股票列表
        """
        results = []
        
        # 1. 获取资金流排行
        if use_fund_flow:
            print('获取资金流排行...')
            fund_data = self.data_source.get_fund_flow_rank(period='即时')
            
            if not fund_data:
                print('❌ 获取资金流失败')
                return []
            
            # 取前 100 只
            top_stocks = fund_data[:100]
            print(f'✅ 获取到 {len(top_stocks)} 只股票')
            print()
            
            # 2. 分析每只股票 (仅主板)
            for i, stock in enumerate(top_stocks):
                symbol = str(stock.get('股票代码', ''))
                
                # 转换代码格式
                if symbol.startswith('SH') or symbol.startswith('SZ'):
                    symbol = symbol[2:]
                
                # 过滤非主板股票
                if symbol.startswith('688'):  # 科创板
                    continue
                if symbol.startswith('300') or symbol.startswith('301'):  # 创业板
                    continue
                if symbol.startswith('8') or symbol.startswith('4'):  # 北交所
                    continue
                
                try:
                    result = self.analyze_stock(symbol, fund_flow_data=stock)
                    
                    if result:
                        results.append(result)
                        # 修复字段名：净额 = 主力净流入
                        main_flow_raw = stock.get('净额', '0')
                        # 转换带单位的字符串为数字 (如'7.86 亿' -> 786000000)
                        if isinstance(main_flow_raw, str):
                            if '亿' in main_flow_raw:
                                main_flow = float(main_flow_raw.replace('亿', '')) * 100000000
                            elif '万' in main_flow_raw:
                                main_flow = float(main_flow_raw.replace('万', '')) * 10000
                            else:
                                main_flow = float(main_flow_raw or 0)
                        else:
                            main_flow = float(main_flow_raw or 0)
                        
                        if abs(main_flow) >= 100000000:
                            flow_str = f'{main_flow/100000000:.2f}亿'
                        else:
                            flow_str = f'{main_flow/10000:.0f}万'
                        
                        print(f"✅ {symbol} {result['name']} ¥{result['price']:.2f} "
                              f"{result['change']:+.2f}% 资金流:{flow_str} "
                              f"评分:{result['score']:.1f}/20 {result['recommendation']}")
                    
                    # 进度
                    if (i + 1) % 10 == 0:
                        print(f'进度：{i+1}/{len(top_stocks)} ...')
                        print(f'   当前找到：{len(results)} 只')
                    
                    # 限频 - 增加间隔避免东财限流
                    if (i + 1) % 3 == 0:
                        time.sleep(2)
                        
                except Exception as e:
                    continue
        
        else:
            # 使用指定股票列表
            if not symbols:
                print('❌ 未提供股票列表')
                return []
            
            for i, symbol in enumerate(symbols):
                try:
                    result = self.analyze_stock(symbol)
                    
                    if result:
                        results.append(result)
                        print(f"✅ {symbol} {result['name']} ¥{result['price']:.2f} "
                              f"评分:{result['score']:.1f}/20 {result['recommendation']}")
                    
                    # 限频
                    if (i + 1) % 5 == 0:
                        time.sleep(1)
                        
                except Exception as e:
                    continue
        
        return results


def generate_test_symbols() -> List[str]:
    """生成测试股票列表"""
    # 一些常见股票
    return [
        '600152',  # 维科技术
        '600089',  # 特变电工
        '002475',  # 立讯精密
        '000815',  # 美利云
        '600930',  # 华电新能
        '600000',  # 浦发银行
        '600036',  # 招商银行
        '000001',  # 平安银行
        '601318',  # 中国平安
        '600519',  # 贵州茅台
        '000858',  # 五粮液
        '600028',  # 中国石化
        '601857',  # 中国石油
        '601088',  # 中国神华
        '600019',  # 宝钢股份
    ]


def main():
    parser = argparse.ArgumentParser(description='双均线选股器 v2.0 - 多数据源+限频保护')
    parser.add_argument('--scan', action='store_true', help='扫描市场')
    parser.add_argument('--check', type=str, help='检查单只股票')
    parser.add_argument('--symbols', type=str, nargs='+', help='指定股票列表')
    parser.add_argument('--mode', choices=['loose', 'medium', 'strict'],
                       default='medium', help='过滤模式')
    parser.add_argument('--volume', type=float, default=1.5, help='成交量倍数')
    
    args = parser.parse_args()
    
    # 更新配置
    EnhancedStockSelector.FILTER_CONFIG['strict_mode'] = args.mode
    EnhancedStockSelector.FILTER_CONFIG['volume_multiplier'] = args.volume
    
    selector = EnhancedStockSelector()
    
    if args.check:
        # 检查单只股票
        symbol = args.check
        print(f'检查股票：{symbol}')
        print('='*70)
        
        result = selector.analyze_stock(symbol)
        
        if result:
            print(f"代码：{result['symbol']}")
            print(f"价格：¥{result['price']:.2f}")
            print(f"涨幅：{result['change']:+.2f}%")
            print(f"评分：{result['score']}/10")
            print(f"建议：{result['recommendation']}")
            print()
            print('过滤条件:')
            filters = result['filters']
            print(f"  基础金叉：{'✅' if filters['golden_cross'] else '❌'}")
            print(f"  成交量：{'✅' if filters['volume_ok'] else '❌'}")
            print(f"  趋势：{'✅' if filters['trend_ok'] else '❌'}")
            print(f"  RSI: {'✅' if filters['rsi_ok'] else '❌'}")
            print(f"  MACD: {'✅' if filters['macd_ok'] else '❌'}")
            print(f"  斜率：{'✅' if filters['slope_ok'] else '❌'}")
        else:
            print('❌ 不符合条件或获取数据失败')
        
        # 显示统计
        stats = selector.data_source.get_stats()
        print()
        print('统计:')
        print(f"  总请求：{stats['total_requests']}")
        print(f"  缓存命中：{stats['cache_hits']}")
        print(f"  缓存命中率：{stats['cache_hit_rate']:.1f}%")
        
    elif args.scan:
        # 扫描市场
        symbols = args.symbols if args.symbols else generate_test_symbols()
        results = selector.scan_market(symbols)
        
        print()
        print('='*70)
        print(f'扫描完成！找到 {len(results)} 只符合条件的股票')
        print('='*70)
        
        if results:
            # 按评分排序
            results.sort(key=lambda x: x['score'], reverse=True)
            
            print()
            print(f'{"排名":>4} {"代码":<8} {"名称":<12} {"价格":>8} {"涨幅":>8} {"评分":>8} {"建议":>10}')
            print('-'*70)
            
            for i, r in enumerate(results, 1):
                print(f'{i:>4} {r["symbol"]:<8} {r["name"]:<12} '
                      f'{r["price"]:>8.2f} {r["change"]:>+7.2f}% '
                      f'{r["score"]:>3}/10 {r["recommendation"]:>10}')
            
            # 保存结果
            output_file = selector.cache_dir / f'scan_result_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print()
            print(f'✅ 结果已保存：{output_file}')
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
