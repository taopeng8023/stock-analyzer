#!/usr/bin/env python3
"""
A 股智能选股系统 - 快速版本
鹏总专用 v1.0

无需复杂依赖，直接运行
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional


class QuickStockAnalyzer:
    """
    快速股票分析器
    使用东方财富 API 获取数据
    """
    
    # 东方财富 API 端点
    API_QUOTE = "http://push2.eastmoney.com/api/qt/stock/get"
    API_KLINE = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    API_FINANCE = "http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://quote.eastmoney.com/',
        }
    
    def _fetch_json(self, url: str, params: dict = None) -> dict:
        """获取 JSON 数据"""
        try:
            if params:
                query = '&'.join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{query}"
            
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        except Exception as e:
            return {'error': str(e)}
    
    def get_stock_quote(self, stock_code: str) -> Optional[dict]:
        """获取实时行情 - 使用简化的东方财富 API"""
        # 判断市场
        if stock_code.startswith('6'):
            market = "1"  # 沪市
        else:
            market = "0"  # 深市
        
        # 使用更简单的 API
        url = f"http://27.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:{market}&fields=f12,f14,f43,f44,f45,f46,f47,f48,f49,f169,f170,f167,f164"
        
        data = self._fetch_json(url)
        
        if data and 'data' in data and data['data'] and 'diff' in data['data']:
            stocks = data['data']['diff']
            for stock in stocks:
                if stock.get('f12') == stock_code:
                    return {
                        'code': stock_code,
                        'name': stock.get('f14', ''),
                        'price': stock.get('f43', 0) / 100,
                        'open': stock.get('f46', 0) / 100,
                        'high': stock.get('f44', 0) / 100,
                        'low': stock.get('f45', 0) / 100,
                        'pre_close': stock.get('f48', 0) / 100,
                        'change_pct': stock.get('f170', 0),
                        'change': stock.get('f169', 0) / 100,
                        'volume': stock.get('f47', 0),
                        'turnover': stock.get('f48', 0),
                        'pe_ttm': stock.get('f164', 0) / 10 if stock.get('f164') else 0,
                        'pb': stock.get('f167', 0) / 100 if stock.get('f167') else 0,
                    }
        
        # 备用方案：直接获取个股
        params = {
            'secid': f"{market}.{stock_code}",
            'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f169,f170,f164,f167',
        }
        
        data = self._fetch_json(self.API_QUOTE, params)
        
        if data and 'data' in data and data['data']:
            d = data['data']
            return {
                'code': stock_code,
                'name': d.get('f58', ''),
                'price': d.get('f43', 0) / 100,
                'open': d.get('f46', 0) / 100,
                'high': d.get('f44', 0) / 100,
                'low': d.get('f45', 0) / 100,
                'pre_close': d.get('f48', 0) / 100,
                'change_pct': d.get('f170', 0),
                'change': d.get('f169', 0) / 100,
                'volume': d.get('f47', 0),
                'turnover': d.get('f48', 0),
                'pe_ttm': d.get('f164', 0) / 10 if d.get('f164') else 0,
                'pb': d.get('f167', 0) / 100 if d.get('f167') else 0,
            }
        
        return None
    
    def get_kline(self, stock_code: str, days: int = 60) -> List[dict]:
        """获取 K 线数据"""
        if stock_code.startswith('6'):
            market = "1"
        else:
            market = "0"
        
        params = {
            'secid': f"{market}.{stock_code}",
            'klt': '101',  # 日线
            'fqt': '1',    # 前复权
            'end': '20500101',
            'lmt': str(days),
        }
        
        data = self._fetch_json(self.API_KLINE, params)
        
        if not data:
            return []
        
        if data and 'data' in data and data['data'] and 'klines' in data['data']:
            klines = data['data']['klines']
            result = []
            for line in klines:
                parts = line.split(',')
                if len(parts) >= 7:
                    result.append({
                        'date': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': float(parts[5]),
                        'turnover': float(parts[6]),
                    })
            return result
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
    
    def analyze_technical(self, klines: List[dict]) -> dict:
        """技术分析"""
        if len(klines) < 30:
            return {'score': 50, 'signals': ['数据不足']}
        
        closes = [k['close'] for k in klines]
        current_price = closes[-1]
        
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
            signals.append(f'✓ 趋势向上 (5 日{change_5d:.1f}%, 10 日{change_10d:.1f}%)')
        elif change_5d < 0 and change_10d < 0:
            score -= 10
            signals.append(f'✗ 趋势向下 (5 日{change_5d:.1f}%, 10 日{change_10d:.1f}%)')
        else:
            signals.append(f'~ 趋势震荡 (5 日{change_5d:.1f}%)')
        
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
            'indicators': {
                'rsi': rsi,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'ma60': ma60,
                'vol_ratio': vol_ratio,
                'change_5d': change_5d,
                'change_10d': change_10d,
            }
        }
    
    def analyze_fundamental(self, quote: dict) -> dict:
        """基本面分析 (简化版)"""
        score = 50
        signals = []
        
        pe = quote.get('pe_ttm', 0)
        pb = quote.get('pb', 0)
        
        # PE 分析
        if pe > 0:
            if pe <= 15:
                score += 15
                signals.append(f'✓ PE 低估 ({pe:.1f})')
            elif pe <= 25:
                score += 5
                signals.append(f'✓ PE 合理 ({pe:.1f})')
            elif pe <= 40:
                score -= 5
                signals.append(f'✗ PE 偏高 ({pe:.1f})')
            else:
                score -= 15
                signals.append(f'✗ PE 高估 ({pe:.1f})')
        else:
            signals.append('~ PE 无数据')
        
        # PB 分析
        if pb > 0:
            if pb <= 2:
                score += 10
                signals.append(f'✓ PB 合理 ({pb:.1f})')
            elif pb <= 4:
                score -= 5
                signals.append(f'✗ PB 偏高 ({pb:.1f})')
            else:
                score -= 10
                signals.append(f'✗ PB 过高 ({pb:.1f})')
        else:
            signals.append('~ PB 无数据')
        
        score = max(0, min(100, score))
        
        return {
            'score': score,
            'signals': signals,
        }
    
    def predict_return(self, tech_score: int, fund_score: int) -> dict:
        """预测 10 日收益"""
        total_score = tech_score * 0.6 + fund_score * 0.4
        
        # 基础收益 + 评分加成
        base = 3.5
        bonus = (total_score - 50) * 0.3
        
        expected = base + bonus
        
        # 情景分析
        volatility = max(5, abs(expected) * 0.6)
        optimistic = expected + volatility
        pessimistic = expected - volatility * 1.5
        
        # 置信度
        confidence = max(40, min(85, 60 + (total_score - 50) * 0.4))
        
        return {
            'expected_return': round(expected, 1),
            'optimistic': round(optimistic, 1),
            'pessimistic': round(pessimistic, 1),
            'confidence': round(confidence, 1),
        }
    
    def calculate_probability(self, tech_score: int, fund_score: int, vol_ratio: float) -> dict:
        """计算成功概率"""
        base = 50
        total_score = tech_score * 0.6 + fund_score * 0.4
        
        score_bonus = (total_score - 50) * 0.6
        
        vol_bonus = 0
        if vol_ratio > 1.5:
            vol_bonus = 8
        elif vol_ratio > 1.2:
            vol_bonus = 5
        elif vol_ratio < 0.7:
            vol_bonus = -5
        
        prob = base + score_bonus + vol_bonus
        prob = max(20, min(85, prob))
        
        # 等级
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
    
    def generate_advice(self, total_score: float, prob: float) -> dict:
        """生成买入建议"""
        if total_score >= 85 and prob >= 70:
            action = '强烈推荐买入'
            code = 'STRONG_BUY'
            icon = '🟢'
            position = '30-50%'
        elif total_score >= 70 and prob >= 60:
            action = '推荐买入'
            code = 'BUY'
            icon = '🟢'
            position = '20-30%'
        elif total_score >= 50 and prob >= 50:
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
        }
    
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
        quote = self.get_stock_quote(stock_code)
        if not quote:
            print("❌ 无法获取股票信息，请检查代码是否正确")
            return {'error': '无法获取股票信息'}
        
        print(f"  ✓ 股票名称：{quote['name']}")
        print(f"  ✓ 当前价格：¥{quote['price']}")
        print(f"  ✓ 涨跌幅：{quote['change_pct']}%")
        
        # 获取 K 线
        print("\n📈 获取 K 线数据...")
        klines = self.get_kline(stock_code, 60)
        if not klines:
            print("❌ 无法获取 K 线数据")
            return {'error': '无法获取 K 线数据'}
        
        print(f"  ✓ K 线数据：{len(klines)} 天")
        
        # 技术分析
        print("\n📊 技术分析...")
        tech = self.analyze_technical(klines)
        print(f"  技术评分：{tech['score']}")
        
        # 基本面分析
        print("\n📋 基本面分析...")
        fund = self.analyze_fundamental(quote)
        print(f"  基本面评分：{fund['score']}")
        
        # 综合评分
        total_score = tech['score'] * 0.6 + fund['score'] * 0.4
        print(f"\n🎯 综合评分：{total_score:.1f}")
        
        # 收益预测
        print("\n📈 10 日收益预测...")
        prediction = self.predict_return(tech['score'], fund['score'])
        print(f"  预期收益：{prediction['expected_return']}%")
        print(f"  乐观：{prediction['optimistic']}%, 悲观：{prediction['pessimistic']}%")
        
        # 成功概率
        print("\n🎲 成功概率...")
        vol_ratio = tech['indicators'].get('vol_ratio', 1)
        prob = self.calculate_probability(tech['score'], fund['score'], vol_ratio)
        print(f"  {prob['icon']} {prob['probability']}% ({prob['level']})")
        
        # 目标价位
        target_price = quote['price'] * (1 + prediction['expected_return'] / 100)
        stop_loss = quote['price'] * 0.92
        
        print(f"\n💰 目标价位...")
        print(f"  目标价：¥{target_price:.2f} ({prediction['expected_return']}%)")
        print(f"  止损价：¥{stop_loss:.2f} (-8%)")
        
        # 买入建议
        print(f"\n💡 操作建议...")
        advice = self.generate_advice(total_score, prob['probability'])
        print(f"  {advice['icon']} {advice['action']}")
        print(f"  建议仓位：{advice['position']}")
        print(f"  策略:")
        for s in advice['strategies']:
            print(f"    • {s}")
        
        # 详细信号
        print(f"\n📋 详细信号...")
        print(f"  技术面:")
        for sig in tech['signals'][:5]:
            print(f"    {sig}")
        print(f"  基本面:")
        for sig in fund['signals'][:3]:
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
            'change_pct': quote['change_pct'],
            'scores': {
                'technical': tech['score'],
                'fundamental': fund['score'],
                'total': round(total_score, 1),
            },
            'prediction': prediction,
            'success_probability': prob,
            'target_prices': {
                'target': round(target_price, 2),
                'stop_loss': round(stop_loss, 2),
            },
            'buy_advice': advice,
            'signals': {
                'technical': tech['signals'],
                'fundamental': fund['signals'],
            },
        }


# 命令行入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法：python quick_analyzer.py <股票代码>")
        print("示例：python quick_analyzer.py 603659")
        sys.exit(1)
    
    stock_code = sys.argv[1]
    analyzer = QuickStockAnalyzer()
    report = analyzer.analyze(stock_code)
