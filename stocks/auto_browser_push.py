#!/usr/bin/env python3
"""
选股系统 - 浏览器自动化版本
使用 Selenium 获取真实数据，集成到自动推送流程

依赖:
pip install selenium webdriver-manager

鹏总专用 - 2026 年 3 月 27 日
"""

import sys
import os
import time
import random
import json
from datetime import datetime

sys.path.insert(0, '/home/admin/.openclaw/workspace')
sys.path.insert(0, '/home/admin/.openclaw/workspace/stocks')

from stocks.browser_automation import EastmoneyBrowser
from stocks.deep_push import PushNotifier
from stock_analyzer.stock_analyzer_v2 import EnhancedStockAnalyzer


class AutoSelectorBrowser:
    """基于浏览器自动化的选股系统"""
    
    def __init__(self, config_file: str = 'push_config.json'):
        self.config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            config_file
        )
        self.notifier = PushNotifier(self.config_path)
        self.browser = EastmoneyBrowser(headless=True)
        self.analyzer = EnhancedStockAnalyzer()
        
        # 缓存目录
        self.cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/browser_auto'
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 日志
        self.log_file = os.path.join(self.cache_dir, f'browser_auto_{datetime.now().strftime("%Y%m%d")}.log')
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def get_data_with_browser(self) -> list:
        """使用浏览器获取数据"""
        self.log("🌐 启动浏览器获取数据...")
        
        try:
            # 获取主力排名
            stocks = self.browser.get_main_force_rank(page=1, page_size=100)
            
            if stocks:
                self.log(f"✅ 浏览器获取成功，共{len(stocks)}条")
                
                # 保存到缓存
                self.browser.save_to_cache(stocks, f'data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                
                return stocks
            else:
                self.log("❌ 浏览器获取失败，无数据")
                return []
        
        except Exception as e:
            self.log(f"❌ 浏览器获取异常：{e}")
            return []
        
        finally:
            # 关闭浏览器
            self.browser.close()
    
    def analyze_stocks(self, stock_list: list) -> list:
        """分析股票，筛选买入信号"""
        self.log("🔍 开始分析股票...")
        
        buy_signals = []
        
        for i, stock in enumerate(stock_list[:100], 1):
            code = stock.get('code', '')
            name = stock.get('name', '')
            
            if not code:
                continue
            
            self.log(f"[{i}/{len(stock_list[:100])}] 分析 {name}({code})")
            
            try:
                # 快速评分
                score = self._quick_score(stock)
                
                if score >= 70:
                    buy_signals.append({
                        'code': code,
                        'name': name,
                        'score': score,
                        'data': stock,
                    })
                    self.log(f"✅ {name} 评分{score:.1f}，达到买入标准")
                
                # 防反爬延迟
                time.sleep(random.uniform(0.2, 0.5))
            
            except Exception as e:
                self.log(f"分析失败：{e}")
                continue
        
        # 按评分排序
        buy_signals.sort(key=lambda x: x['score'], reverse=True)
        
        self.log(f"分析完成，发现{len(buy_signals)}个买入信号")
        
        return buy_signals
    
    def _quick_score(self, stock: dict) -> float:
        """快速评分"""
        score = 50.0
        
        # 主力净流入 (40%)
        try:
            main_net = float(stock.get('main_force_net', 0) or 0)
            main_ratio = float(stock.get('main_force_ratio', 0) or 0)
            
            if main_net > 100000000:  # >1 亿
                score += 20
            elif main_net > 50000000:
                score += 15
            elif main_net > 0:
                score += 5
            
            if main_ratio > 10:
                score += 10
            elif main_ratio > 5:
                score += 5
        
        except:
            pass
        
        # 涨跌幅 (30%)
        try:
            change = float(stock.get('change_pct', 0) or 0)
            
            if 2 <= change <= 7:
                score += 15
            elif 0 < change < 2:
                score += 10
            elif change > 7:
                score += 5
            elif -3 <= change <= 0:
                score += 5
            else:
                score -= 10
        
        except:
            pass
        
        return min(100, max(0, score))
    
    def push_top5(self, signals: list):
        """推送 TOP 5 买入信号"""
        if not signals:
            self.log("⚠️ 无买入信号，不推送")
            return
        
        top5 = signals[:5]
        
        self.log("📱 准备推送 TOP 5 买入信号...")
        
        content = f"""## 🎯 今日选股信号 TOP 5

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**数据来源**: 浏览器自动化获取（真实数据）

### 买入信号

"""
        
        for i, signal in enumerate(top5, 1):
            code = signal['code']
            name = signal['name']
            score = signal['score']
            data = signal['data']
            
            price = float(data.get('price', 0) or 0)
            change = float(data.get('change_pct', 0) or 0)
            
            # 主力净额可能是字符串，需要解析
            main_net_str = str(data.get('main_force_net', '0'))
            try:
                if '亿' in main_net_str:
                    main_net = float(main_net_str.replace('亿', '')) * 100000000
                elif '万' in main_net_str:
                    main_net = float(main_net_str.replace('万', '')) * 10000
                else:
                    main_net = float(main_net_str) if main_net_str else 0
            except:
                main_net = 0
            
            main_net_yi = main_net / 100000000
            
            try:
                main_ratio = float(data.get('main_force_ratio', 0) or 0)
            except:
                main_ratio = 0
            
            content += f"""**{i}. {name}({code})**
- 综合评分：**{score:.1f}分**
- 现价：¥{price:.2f} ({change:+.2f}%)
- 主力：{main_net_yi:.2f}亿 ({main_ratio:.2f}%)
- 建议：仓位 20-30%
- 止损：-8%
- 止盈：+25%

"""
        
        content += f"""---
### 💡 操作建议
- 分批建仓，首笔 30%
- 严格执行止损
- 持有周期：5-10 天

### ⚠️ 风险提示
股市有风险，投资需谨慎

---
*选股系统 v3.0*
*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*数据：浏览器自动化获取*
"""
        
        title = f"🎯 今日选股信号 TOP 5"
        
        # 推送
        result = self.notifier.send_wecom(title, content, msg_type='markdown')
        
        if result:
            self.log("✅ 推送成功")
        else:
            self.log("❌ 推送失败")
        
        # 保存记录
        self._save_record(top5)
    
    def _save_record(self, signals: list):
        """保存推送记录"""
        record = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'browser_auto',
            'signals': [
                {
                    'code': s['code'],
                    'name': s['name'],
                    'score': s['score'],
                }
                for s in signals
            ],
        }
        
        history_file = os.path.join(self.cache_dir, 'push_history.json')
        
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append(record)
        history = history[-30:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        self.log(f"📁 推送记录已保存")
    
    def run(self):
        """运行完整流程"""
        self.log("="*60)
        self.log("🚀 开始执行浏览器自动化选股流程")
        self.log("="*60)
        self.log("⚠️ 原则：数据获取失败，不做推送")
        self.log("="*60)
        
        start_time = datetime.now()
        
        # 1. 使用浏览器获取数据
        stock_list = self.get_data_with_browser()
        
        # 数据验证
        if not stock_list or len(stock_list) < 20:
            self.log("❌ 数据获取失败或数据不足（要求≥20 条，实际{}条）".format(len(stock_list) if stock_list else 0))
            self.log("❌ 数据验证未通过，终止流程，不做推送")
            self._send_failure_alert("浏览器数据获取失败")
            return
        
        self.log(f"✅ 数据验证通过，共{len(stock_list)}只股票")
        
        # 2. 分析股票
        buy_signals = self.analyze_stocks(stock_list)
        
        # 3. 推送 TOP 5
        if buy_signals:
            top_signal = buy_signals[0]
            if top_signal['score'] >= 70:
                self.push_top5(buy_signals)
            else:
                self.log("⚠️ 最高评分{} < 70，无符合条件的买入信号，不做推送".format(top_signal['score']))
        else:
            self.log("⚠️ 无符合条件的买入信号，不做推送")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.log("="*60)
        self.log(f"✅ 流程执行完成，耗时{duration:.1f}秒")
        self.log("="*60)
    
    def _send_failure_alert(self, reason: str):
        """发送失败告警"""
        self.log(f"🚨 发送失败告警：{reason}")
        
        content = f"""## 🚨 数据获取失败告警

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**失败原因**: {reason}

**已执行操作**:
- ❌ 选股推送已取消
- ⚠️ 请检查网络或浏览器状态

**建议**:
1. 检查网络连接
2. 检查 Chrome 浏览器
3. 稍后重试

---
*选股系统 v3.0*
"""
        
        self.notifier.send_wecom('🚨 数据获取失败告警', content, msg_type='markdown')


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='浏览器自动化选股系统')
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--config', type=str, default='push_config.json', help='配置文件')
    
    args = parser.parse_args()
    
    selector = AutoSelectorBrowser(args.config)
    
    if args.test:
        print("\n🧪 测试模式：使用浏览器获取真实数据\n")
        selector.run()
    else:
        print("\n🚀 启动浏览器自动化选股流程\n")
        selector.run()
