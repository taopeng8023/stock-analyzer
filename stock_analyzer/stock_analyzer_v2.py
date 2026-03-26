#!/usr/bin/env python3
"""
鹏总选股系统 v2.0 - 第一阶段优化版
优化内容:
1. 多数据源支持（东方财富 + 新浪财经 + 同花顺）
2. 主力资金分析集成
3. 评分系统优化

鹏总专用 - 2026 年 3 月 26 日
"""

import urllib.request
import urllib.error
import json
from datetime import datetime
from typing import Dict, List, Optional


class MultiSourceDataFetcher:
    """多数据源采集器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
        }
        self.timeout = 10
    
    def _fetch_json(self, url: str, retry: int = 3) -> dict:
        """带重试的 JSON 获取"""
        for i in range(retry):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    data = response.read().decode('utf-8', errors='ignore')
                    return json.loads(data)
            except Exception as e:
                if i < retry - 1:
                    import time
                    time.sleep(0.5)
                else:
                    return {}
        return {}
    
    def fetch_from_eastmoney(self, stock_code: str) -> dict:
        """东方财富数据源"""
        if stock_code.startswith('6'):
            symbol = f"1.{stock_code}"
        else:
            symbol = f"0.{stock_code}"
        
        url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={symbol}&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f169,f170,f164,f167"
        
        data = self._fetch_json(url)
        if data.get('data'):
            d = data['data']
            return {
                'source': 'eastmoney',
                'code': stock_code,
                'name': d.get('f58', ''),
                'price': d.get('f43', 0) / 100,
                'open': d.get('f46', 0) / 100,
                'high': d.get('f44', 0) / 100,
                'low': d.get('f45', 0) / 100,
                'pre_close': d.get('f48', 0) / 100,
                'change_pct': d.get('f170', 0),
                'volume': d.get('f47', 0),
                'turnover': d.get('f48', 0),
                'pe_ttm': d.get('f164', 0) / 10 if d.get('f164') else 0,
                'pb': d.get('f167', 0) / 100 if d.get('f167') else 0,
            }
        return {}
    
    def fetch_from_sina(self, stock_code: str) -> dict:
        """新浪财经数据源"""
        if stock_code.startswith('6'):
            symbol = f"sh{stock_code}"
        else:
            symbol = f"sz{stock_code}"
        
        url = f"http://hq.sinajs.cn/list={symbol}"
        
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                text = response.read().decode('gbk', errors='ignore')
                
            if '=' in text:
                content = text.split('=')[1].strip('"').strip('"')
                parts = content.split(',')
                
                if len(parts) >= 32:
                    return {
                        'source': 'sina',
                        'code': stock_code,
                        'name': parts[0],
                        'open': float(parts[1]),
                        'high': float(parts[2]),
                        'low': float(parts[3]),
                        'price': float(parts[4]),
                        'pre_close': float(parts[2]),
                        'change_pct': ((float(parts[4]) - float(parts[2])) / float(parts[2]) * 100) if float(parts[2]) > 0 else 0,
                        'volume': float(parts[8]) if parts[8] else 0,
                        'turnover': float(parts[9]) if parts[9] else 0,
                    }
        except Exception as e:
            pass
        
        return {}
    
    def fetch_with_fallback(self, stock_code: str) -> dict:
        """多源fallback 获取"""
        # 优先东方财富
        data = self.fetch_from_eastmoney(stock_code)
        if data and data.get('price', 0) > 0:
            return data
        
        # 备用新浪
        data = self.fetch_from_sina(stock_code)
        if data and data.get('price', 0) > 0:
            return data
        
        return {}


class MoneyFlowAnalyzer:
    """主力资金分析器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'http://data.eastmoney.com/zjlx/',
        }
    
    def get_stock_money_flow(self, stock_code: str) -> dict:
        """获取个股资金流向"""
        if stock_code.startswith('6'):
            symbol = f"1.{stock_code}"
        else:
            symbol = f"0.{stock_code}"
        
        url = f"http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get?secid={symbol}&lmt=0&klt=1&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
        
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            if data.get('data') and data['data'].get('klines'):
                latest = data['data']['klines'][-1].split(',')
                if len(latest) >= 11:
                    return {
                        'date': latest[0],
                        'main_force_net': float(latest[5]) if latest[5] else 0,  # 主力净流入 (万)
                        'main_force_ratio': float(latest[8]) if latest[8] else 0,  # 主力占比 (%)
                        'super_net': float(latest[6]) if latest[6] else 0,  # 超大单 (万)
                        'big_net': float(latest[7]) if latest[7] else 0,  # 大单 (万)
                        'mid_net': float(latest[9]) if latest[9] else 0,  # 中单 (万)
                        'small_net': float(latest[10]) if latest[10] else 0,  # 小单 (万)
                    }
        except:
            pass
        
        return {}
    
    def get_main_force_rank(self, top_n: int = 20) -> list:
        """获取主力净流入排名"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': '1',
            'pz': str(top_n),
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f4001',
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
            'fields': 'f12,f14,f2,f3,f4001,f4002,f4003,f4004',
            '_': str(int(datetime.now().timestamp() * 1000))
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        try:
            req = urllib.request.Request(full_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            if data.get('data') and data['data'].get('diff'):
                return data['data']['diff']
        except:
            pass
        
        return []
    
    def analyze_money_flow(self, stock_code: str) -> dict:
        """分析个股资金流向"""
        flow_data = self.get_stock_money_flow(stock_code)
        
        if not flow_data:
            return {
                'score': 50,
                'level': '未知',
                'signals': ['资金流向数据 unavailable']
            }
        
        main_net = flow_data.get('main_force_net', 0) / 10000  # 转亿
        main_ratio = flow_data.get('main_force_ratio', 0)
        
        score = 50
        signals = []
        
        # 主力净流入评分
        if main_net > 1:
            score += 20
            signals.append(f'✓ 主力大幅净流入 ({main_net:.2f}亿)')
        elif main_net > 0.5:
            score += 15
            signals.append(f'✓ 主力净流入 ({main_net:.2f}亿)')
        elif main_net > 0:
            score += 5
            signals.append(f'✓ 主力小幅净流入 ({main_net:.2f}亿)')
        elif main_net < -1:
            score -= 20
            signals.append(f'✗ 主力大幅净流出 ({main_net:.2f}亿)')
        elif main_net < -0.5:
            score -= 15
            signals.append(f'✗ 主力净流出 ({main_net:.2f}亿)')
        else:
            signals.append(f'~ 主力小幅净流出 ({main_net:.2f}亿)')
        
        # 主力占比评分
        if main_ratio > 10:
            score += 15
            signals.append(f'✓ 主力占比很高 ({main_ratio:.1f}%)')
        elif main_ratio > 5:
            score += 10
            signals.append(f'✓ 主力占比较高 ({main_ratio:.1f}%)')
        elif main_ratio > 0:
            score += 5
            signals.append(f'✓ 主力占比为正 ({main_ratio:.1f}%)')
        else:
            signals.append(f'~ 主力占比为负 ({main_ratio:.1f}%)')
        
        score = max(0, min(100, score))
        
        # 评级
        if score >= 80:
            level = '很强'
        elif score >= 70:
            level = '较强'
        elif score >= 60:
            level = '中等'
        elif score >= 40:
            level = '较弱'
        else:
            level = '很弱'
        
        return {
            'score': score,
            'level': level,
            'signals': signals,
            'data': flow_data,
        }


class EnhancedStockAnalyzer:
    """增强版股票分析器 - v2.0"""
    
    def __init__(self):
        self.fetcher = MultiSourceDataFetcher()
        self.money_flow = MoneyFlowAnalyzer()
    
    def analyze(self, stock_code: str) -> dict:
        """完整分析"""
        print(f"\n{'='*90}")
        print(f"  鹏总选股系统 v2.0 - 第一阶段优化版")
        print(f"{'='*90}")
        print(f"  分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  股票代码：{stock_code}")
        print(f"{'='*90}\n")
        
        # 1. 获取行情数据（多源）
        print("📊 获取行情数据 (多源 fallback)...")
        quote = self.fetcher.fetch_with_fallback(stock_code)
        if not quote or quote.get('price', 0) <= 0:
            print("❌ 无法获取行情数据")
            return {'error': '无法获取行情数据'}
        
        print(f"  ✓ 数据源：{quote.get('source', 'unknown')}")
        print(f"  ✓ 股票名称：{quote.get('name', 'N/A')}")
        print(f"  ✓ 当前价格：¥{quote.get('price', 0):.2f}")
        print(f"  ✓ 涨跌幅：{quote.get('change_pct', 0):.2f}%")
        
        # 2. 技术面分析
        print("\n📈 技术面分析...")
        tech_score = self._analyze_technical(quote)
        print(f"  技术评分：{tech_score['score']}")
        
        # 3. 基本面分析
        print("\n📋 基本面分析...")
        fund_score = self._analyze_fundamental(quote)
        print(f"  基本面评分：{fund_score['score']}")
        
        # 4. 资金面分析（新增）
        print("\n💰 资金面分析...")
        money_result = self.money_flow.analyze_money_flow(stock_code)
        money_score = money_result['score']
        print(f"  资金面评分：{money_score}")
        for sig in money_result['signals'][:3]:
            print(f"    {sig}")
        
        # 5. 综合评分（优化权重）
        print("\n🎯 综合评分...")
        # 新权重：技术面 35% + 基本面 35% + 资金面 30%
        total_score = tech_score['score'] * 0.35 + fund_score['score'] * 0.35 + money_score * 0.30
        print(f"  总评分：{total_score:.1f}")
        print(f"  (技术面 35% + 基本面 35% + 资金面 30%)")
        
        # 6. 收益预测
        print("\n📈 10 日收益预测...")
        prediction = self._predict_return(total_score)
        print(f"  预期收益：{prediction['expected_return']}%")
        print(f"  乐观：{prediction['optimistic']}%, 悲观：{prediction['pessimistic']}%")
        
        # 7. 成功概率
        print("\n🎲 成功概率...")
        prob = self._calculate_probability(total_score, money_score)
        print(f"  {prob['icon']} {prob['probability']}% ({prob['level']})")
        
        # 8. 目标价位
        target_price = quote['price'] * (1 + prediction['expected_return'] / 100)
        stop_loss = quote['price'] * 0.92
        
        print(f"\n💰 目标价位...")
        print(f"  目标价：¥{target_price:.2f} ({prediction['expected_return']}%)")
        print(f"  止损价：¥{stop_loss:.2f} (-8%)")
        
        # 9. 买入建议
        print(f"\n💡 操作建议...")
        advice = self._generate_advice(total_score, prob['probability'])
        print(f"  {advice['icon']} {advice['action']}")
        print(f"  建议仓位：{advice['position']}")
        print(f"  策略:")
        for s in advice['strategies']:
            print(f"    • {s}")
        
        print(f"\n{'='*90}")
        print(f"  ⚠️ 风险提示：股市有风险，投资需谨慎")
        print(f"  本报告仅供参考，不构成投资建议")
        print(f"{'='*90}\n")
        
        # 返回报告
        return {
            'version': '2.0',
            'stock_code': stock_code,
            'stock_name': quote['name'],
            'current_price': quote['price'],
            'change_pct': quote['change_pct'],
            'data_source': quote.get('source', 'unknown'),
            'scores': {
                'technical': tech_score['score'],
                'fundamental': fund_score['score'],
                'money_flow': money_score,
                'total': round(total_score, 1),
            },
            'prediction': prediction,
            'success_probability': prob,
            'target_prices': {
                'target': round(target_price, 2),
                'stop_loss': round(stop_loss, 2),
            },
            'buy_advice': advice,
            'money_flow_analysis': money_result,
        }
    
    def _analyze_technical(self, quote: dict) -> dict:
        """技术面分析"""
        score = 50
        signals = []
        
        # 涨跌幅评分
        change = quote.get('change_pct', 0)
        if change > 5:
            score += 15
            signals.append(f'✓ 强势上涨 (+{change:.2f}%)')
        elif change > 2:
            score += 10
            signals.append(f'✓ 上涨 (+{change:.2f}%)')
        elif change > 0:
            score += 5
            signals.append(f'✓ 小幅上涨 (+{change:.2f}%)')
        elif change < -5:
            score -= 15
            signals.append(f'✗ 大幅下跌 ({change:.2f}%)')
        elif change < -2:
            score -= 10
            signals.append(f'✗ 下跌 ({change:.2f}%)')
        else:
            signals.append(f'~ 小幅下跌 ({change:.2f}%)')
        
        score = max(0, min(100, score))
        
        return {'score': score, 'signals': signals}
    
    def _analyze_fundamental(self, quote: dict) -> dict:
        """基本面分析"""
        score = 50
        signals = []
        
        # PE 评分
        pe = quote.get('pe_ttm', 0)
        if pe > 0:
            if pe < 15:
                score += 15
                signals.append(f'✓ PE 低估 ({pe:.1f})')
            elif pe < 25:
                score += 5
                signals.append(f'✓ PE 合理 ({pe:.1f})')
            elif pe < 40:
                score -= 5
                signals.append(f'✗ PE 偏高 ({pe:.1f})')
            else:
                score -= 15
                signals.append(f'✗ PE 高估 ({pe:.1f})')
        else:
            signals.append('~ PE 无数据')
        
        # PB 评分
        pb = quote.get('pb', 0)
        if pb > 0:
            if pb < 2:
                score += 10
                signals.append(f'✓ PB 合理 ({pb:.1f})')
            elif pb < 4:
                score -= 5
                signals.append(f'✗ PB 偏高 ({pb:.1f})')
            else:
                score -= 10
                signals.append(f'✗ PB 过高 ({pb:.1f})')
        else:
            signals.append('~ PB 无数据')
        
        score = max(0, min(100, score))
        
        return {'score': score, 'signals': signals}
    
    def _predict_return(self, score: int) -> dict:
        """收益预测"""
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
    
    def _calculate_probability(self, total_score: int, money_score: int) -> dict:
        """成功概率计算"""
        base = 50
        score_bonus = (total_score - 50) * 0.5
        money_bonus = (money_score - 50) * 0.2
        
        prob = base + score_bonus + money_bonus
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
        if score >= 80 and prob >= 70:
            action = '强烈推荐买入'
            code = 'STRONG_BUY'
            icon = '🟢'
            position = '30-50%'
        elif score >= 70 and prob >= 60:
            action = '推荐买入'
            code = 'BUY'
            icon = '🟢'
            position = '25-35%'
        elif score >= 60 and prob >= 50:
            action = '观望'
            code = 'HOLD'
            icon = '🟡'
            position = '10-20%'
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
            strategies = ['等待更好机会', '关注突破信号', '可轻仓试水']
        else:
            strategies = ['规避风险', '等待企稳信号', '不要抄底']
        
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
        print("用法：python stock_analyzer_v2.py <股票代码>")
        print("示例：python stock_analyzer_v2.py 601899")
        print("\n鹏总选股系统 v2.0 - 第一阶段优化版")
        sys.exit(1)
    
    stock_code = sys.argv[1]
    analyzer = EnhancedStockAnalyzer()
    report = analyzer.analyze(stock_code)
    
    # 保存报告
    output_file = f"/home/admin/.openclaw/workspace/stock_analyzer/reports/{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v2.json"
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📁 报告已保存：{output_file}")
