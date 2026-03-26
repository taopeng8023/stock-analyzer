#!/usr/bin/env python3
"""
A 股智能选股系统 - 新浪财经版
鹏总专用 v1.0

使用新浪财经 API，更稳定可靠
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional


class StockAnalyzer:
    """
    股票分析器 - 鹏总专用
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        }
    
    def _fetch(self, url: str) -> str:
        """获取网页内容"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode('gbk', errors='ignore')
        except Exception as e:
            return ""
    
    def get_stock_data(self, stock_code: str) -> Optional[dict]:
        """获取股票数据（新浪财经）"""
        # 判断市场
        if stock_code.startswith('6'):
            symbol = f"sh{stock_code}"
        else:
            symbol = f"sz{stock_code}"
        
        url = f"http://hq.sinajs.cn/list={symbol}"
        text = self._fetch(url)
        
        if not text or '=' not in text:
            return None
        
        # 解析数据
        # var hq_str_sh603659="璞泰来，31.43,31.48,31.98,31.30,31.28,31.35,31.36,23856789,752847320,..."
        try:
            content = text.split('=')[1].strip('"').strip('"')
            parts = content.split(',')
            
            if len(parts) < 30:
                return None
            
            return {
                'code': stock_code,
                'name': parts[0],
                'open': float(parts[1]),
                'high': float(parts[2]),
                'low': float(parts[3]),
                'price': float(parts[4]),  # 当前价
                'pre_close': float(parts[2]),  # 昨收
                'volume': float(parts[8]) if parts[8] else 0,
                'turnover': float(parts[9]) if parts[9] else 0,
            }
        except Exception as e:
            print(f"解析失败：{e}")
            return None
    
    def get_kline_data(self, stock_code: str, days: int = 60) -> List[dict]:
        """获取 K 线数据（新浪财经）"""
        if stock_code.startswith('6'):
            symbol = f"sh{stock_code}"
        else:
            symbol = f"sz{stock_code}"
        
        # 新浪财经日 K 线 API
        url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={days}"
        
        text = self._fetch(url)
        
        if not text:
            return []
        
        try:
            data = json.loads(text)
            if not data:
                return []
            
            result = []
            for item in data:
                result.append({
                    'date': item.get('day', ''),
                    'open': float(item.get('open', 0)),
                    'high': float(item.get('high', 0)),
                    'low': float(item.get('low', 0)),
                    'close': float(item.get('close', 0)),
                    'volume': float(item.get('volume', 0)),
                })
            return result
        except Exception as e:
            print(f"获取 K 线失败：{e}")
            return []
    
    def calculate_ma(self, prices: List[float], period: int) -> float:
        """计算移动平均"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """计算 RSI"""
        if len(prices) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def analyze(self, stock_code: str) -> dict:
        """完整分析"""
        print(f"\n{'='*60}")
        print(f"  鹏总选股系统 - 股票分析报告")
        print(f"{'='*60}")
        print(f"  分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  股票代码：{stock_code}")
        print(f"{'='*60}\n")
        
        # 获取行情
        print("📊 获取行情数据...")
        quote = self.get_stock_data(stock_code)
        if not quote:
            print("❌ 无法获取股票信息，请检查代码是否正确")
            return {'error': '无法获取股票信息'}
        
        print(f"  ✓ 股票名称：{quote['name']}")
        print(f"  ✓ 当前价格：¥{quote['price']}")
        
        # 计算涨跌幅
        change_pct = (quote['price'] - quote['pre_close']) / quote['pre_close'] * 100
        print(f"  ✓ 涨跌幅：{change_pct:+.2f}%")
        
        # 获取 K 线
        print("\n📈 获取 K 线数据...")
        klines = self.get_kline_data(stock_code, 60)
        if not klines:
            print("❌ 无法获取 K 线数据")
            return {'error': '无法获取 K 线数据'}
        
        print(f"  ✓ K 线数据：{len(klines)} 天")
        
        # 技术分析
        print("\n📊 技术分析...")
        tech_result = self._analyze_technical(klines, quote['price'])
        print(f"  技术评分：{tech_result['score']}")
        
        # 综合评分（简化版，主要看技术面）
        total_score = tech_result['score']
        
        # 收益预测
        print("\n📈 10 日收益预测...")
        prediction = self._predict_return(total_score)
        print(f"  预期收益：{prediction['expected_return']}%")
        print(f"  乐观：{prediction['optimistic']}%, 悲观：{prediction['pessimistic']}%")
        
        # 成功概率
        print("\n🎲 成功概率...")
        prob = self._calculate_probability(total_score, tech_result['vol_ratio'])
        print(f"  {prob['icon']} {prob['probability']}% ({prob['level']})")
        
        # 目标价位
        target_price = quote['price'] * (1 + prediction['expected_return'] / 100)
        stop_loss = quote['price'] * 0.92
        
        print(f"\n💰 目标价位...")
        print(f"  目标价：¥{target_price:.2f} ({prediction['expected_return']}%)")
        print(f"  止损价：¥{stop_loss:.2f} (-8%)")
        
        # 买入建议
        print(f"\n💡 操作建议...")
        advice = self._generate_advice(total_score, prob['probability'])
        print(f"  {advice['icon']} {advice['action']}")
        print(f"  建议仓位：{advice['position']}")
        print(f"  策略:")
        for s in advice['strategies']:
            print(f"    • {s}")
        
        # 详细信号
        print(f"\n📋 详细信号...")
        print(f"  技术面:")
        for sig in tech_result['signals'][:6]:
            print(f"    {sig}")
        
        print(f"\n{'='*60}")
        print(f"  ⚠️ 风险提示：股市有风险，投资需谨慎")
        print(f"  本报告仅供参考，不构成投资建议")
        print(f"{'='*60}\n")
        
        # 返回报告
        return {
            'stock_code': stock_code,
            'stock_name': quote['name'],
            'current_price': quote['price'],
            'change_pct': round(change_pct, 2),
            'scores': {
                'technical': tech_result['score'],
                'total': total_score,
            },
            'prediction': prediction,
            'success_probability': prob,
            'target_prices': {
                'target': round(target_price, 2),
                'stop_loss': round(stop_loss, 2),
            },
            'buy_advice': advice,
            'signals': tech_result['signals'],
        }
    
    def _analyze_technical(self, klines: List[dict], current_price: float) -> dict:
        """技术分析"""
        if len(klines) < 30:
            return {'score': 50, 'signals': ['数据不足'], 'vol_ratio': 1}
        
        closes = [k['close'] for k in klines]
        
        score = 50
        signals = []
        
        # MA 分析
        ma5 = self.calculate_ma(closes, 5)
        ma10 = self.calculate_ma(closes, 10)
        ma20 = self.calculate_ma(closes, 20)
        ma60 = self.calculate_ma(closes, 60)
        
        if current_price > ma60:
            score += 10
            signals.append('✓ 股价在 60 日均线上方')
        else:
            score -= 10
            signals.append('✗ 股价在 60 日均线下方')
        
        if ma5 > ma10 > ma20:
            score += 5
            signals.append('✓ 均线多头排列')
        
        # RSI 分析
        rsi = self.calculate_rsi(closes)
        if 40 <= rsi <= 70:
            score += 5
            signals.append(f'✓ RSI 中性 ({rsi:.1f})')
        elif rsi < 30:
            score += 10
            signals.append(f'✓ RSI 超卖 ({rsi:.1f})')
        elif rsi > 80:
            score -= 10
            signals.append(f'✗ RSI 超买 ({rsi:.1f})')
        
        # 趋势分析
        change_5d = (closes[-1] - closes[-5]) / closes[-5] * 100 if len(closes) >= 5 else 0
        change_10d = (closes[-1] - closes[-10]) / closes[-10] * 100 if len(closes) >= 10 else 0
        
        if change_5d > 0 and change_10d > 0:
            score += 10
            signals.append(f'✓ 趋势向上 (5 日{change_5d:+.1f}%)')
        elif change_5d < 0 and change_10d < 0:
            score -= 10
            signals.append(f'✗ 趋势向下 (5 日{change_5d:+.1f}%)')
        else:
            signals.append(f'~ 趋势震荡 (5 日{change_5d:+.1f}%)')
        
        # 成交量分析
        volumes = [k['volume'] for k in klines]
        avg_vol_5 = sum(volumes[-5:]) / 5
        avg_vol_20 = sum(volumes[-20:]) / 20
        vol_ratio = avg_vol_5 / avg_vol_20 if avg_vol_20 > 0 else 1
        
        if vol_ratio > 1.5:
            score += 10
            signals.append(f'✓ 成交量放大 ({vol_ratio:.2f}倍)')
        elif vol_ratio > 1.2:
            score += 5
            signals.append(f'✓ 成交量温和放大 ({vol_ratio:.2f}倍)')
        elif vol_ratio < 0.7:
            score -= 5
            signals.append(f'✗ 成交量萎缩 ({vol_ratio:.2f}倍)')
        
        score = max(0, min(100, score))
        
        return {
            'score': score,
            'signals': signals,
            'vol_ratio': vol_ratio,
            'indicators': {
                'rsi': rsi,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'ma60': ma60,
                'change_5d': change_5d,
                'change_10d': change_10d,
            }
        }
    
    def _predict_return(self, score: int) -> dict:
        """预测 10 日收益"""
        base = 3.5
        bonus = (score - 50) * 0.3
        expected = base + bonus
        
        volatility = max(5, abs(expected) * 0.6)
        optimistic = expected + volatility
        pessimistic = expected - volatility * 1.5
        
        confidence = max(40, min(85, 60 + (score - 50) * 0.4))
        
        return {
            'expected_return': round(expected, 1),
            'optimistic': round(optimistic, 1),
            'pessimistic': round(pessimistic, 1),
            'confidence': round(confidence, 1),
        }
    
    def _calculate_probability(self, score: int, vol_ratio: float) -> dict:
        """计算成功概率"""
        base = 50
        score_bonus = (score - 50) * 0.6
        
        vol_bonus = 0
        if vol_ratio > 1.5:
            vol_bonus = 8
        elif vol_ratio > 1.2:
            vol_bonus = 5
        elif vol_ratio < 0.7:
            vol_bonus = -5
        
        prob = base + score_bonus + vol_bonus
        prob = max(20, min(85, prob))
        
        if prob >= 75:
            level = '很高'
            icon = '✓✓✓'
        elif prob >= 65:
            level = '较高'
            icon = '✓✓'
        elif prob >= 55:
            level = '中等'
            icon = '✓'
        elif prob >= 45:
            level = '偏低'
            icon = '✗'
        else:
            level = '很低'
            icon = '✗✗'
        
        return {
            'probability': round(prob, 1),
            'level': level,
            'icon': icon,
        }
    
    def _generate_advice(self, score: float, prob: float) -> dict:
        """生成买入建议"""
        if score >= 85 and prob >= 70:
            action = '强烈推荐买入'
            code = 'STRONG_BUY'
            icon = '🟢'
            position = '30-50%'
        elif score >= 70 and prob >= 60:
            action = '推荐买入'
            code = 'BUY'
            icon = '🟢'
            position = '20-30%'
        elif score >= 50 and prob >= 50:
            action = '观望'
            code = 'HOLD'
            icon = '🟡'
            position = '0-10%'
        else:
            action = '不建议买入'
            code = 'SELL'
            icon = '🔴'
            position = '0%'
        
        strategies = []
        if code in ['STRONG_BUY', 'BUY']:
            strategies = [
                '分批建仓，首笔 30%',
                '止损位：-8%',
                '止盈位：+25%',
                '持有周期：5-10 天',
            ]
        elif code == 'HOLD':
            strategies = ['等待更好机会', '关注突破信号']
        else:
            strategies = ['规避风险', '等待企稳信号']
        
        return {
            'action': action,
            'code': code,
            'icon': icon,
            'position': position,
            'strategies': strategies,
            'reason': f"综合评分{score:.1f}, 成功概率{prob:.1f}%",
        }


# 命令行入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法：python stock_analyzer.py <股票代码>")
        print("示例：python stock_analyzer.py 603659")
        print("\n鹏总专用选股系统 v1.0")
        sys.exit(1)
    
    stock_code = sys.argv[1]
    analyzer = StockAnalyzer()
    report = analyzer.analyze(stock_code)
    
    # 保存报告
    output_file = f"/home/admin/.openclaw/workspace/stock_analyzer/reports/{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📁 报告已保存：{output_file}")
