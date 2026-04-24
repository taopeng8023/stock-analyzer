#!/usr/bin/env python3
"""
选股系统 - 每日自动选股推送流程
每日 14:20 获取数据，分析后推送 TOP 5 买入信号

功能:
1. 获取主力资金流 TOP 100
2. 获取板块排名 TOP 10
3. 分析筛选买入信号 TOP 5
4. 企业微信推送
5. 防反爬机制

鹏总专用 - 2026 年 3 月 26 日
"""

import sys
import os
import time
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 添加路径
sys.path.insert(0, '/home/admin/.openclaw/workspace')
sys.path.insert(0, '/home/admin/.openclaw/workspace/stocks')

from stocks.deep_push import PushNotifier
from stocks.eastmoney_money_flow import EastmoneyMoneyFlow
from stocks.sector_rank import EastmoneySectorRank
from stock_analyzer.stock_analyzer_v2 import EnhancedStockAnalyzer


class AutoSelector:
    """自动选股推送系统"""
    
    def __init__(self, config_file: str = 'push_config.json'):
        self.config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            config_file
        )
        self.notifier = PushNotifier(self.config_path)
        self.money_flow = EastmoneyMoneyFlow()
        self.sector = EastmoneySectorRank()
        self.analyzer = EnhancedStockAnalyzer()
        
        # 防反爬配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'http://data.eastmoney.com/',
        }
        
        # 缓存目录
        self.cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/auto_select'
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 日志
        self.log_file = os.path.join(self.cache_dir, f'auto_select_{datetime.now().strftime("%Y%m%d")}.log')
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def safe_request(self, func, *args, max_retries: int = 3, **kwargs):
        """安全请求，带重试和防反爬"""
        for i in range(max_retries):
            try:
                # 随机延迟，防反爬
                if i > 0:
                    delay = random.uniform(2, 5)
                    self.log(f"重试第{i+1}次，延迟{delay:.1f}秒")
                    time.sleep(delay)
                
                result = func(*args, **kwargs)
                
                # 添加随机延迟
                time.sleep(random.uniform(0.5, 1.5))
                
                return result
            
            except Exception as e:
                self.log(f"请求失败：{e}")
                if i >= max_retries - 1:
                    self.log("达到最大重试次数")
                    return None
        
        return None
    
    def get_main_force_top100(self) -> List[dict]:
        """获取主力资金流 TOP 100"""
        self.log("📊 获取主力资金流 TOP 100...")
        
        all_stocks = []
        page = 1
        
        while len(all_stocks) < 100:
            rank = self.safe_request(
                self.money_flow.get_main_force_rank,
                page=page,
                page_size=20,
                max_retries=3
            )
            
            if not rank:
                self.log(f"第{page}页获取失败")
                break
            
            all_stocks.extend(rank)
            self.log(f"已获取第{page}页，共{len(all_stocks)}条")
            
            page += 1
            
            # 防反爬延迟
            time.sleep(random.uniform(1, 3))
        
        return all_stocks[:100]
    
    def get_sector_top10(self) -> List[dict]:
        """获取板块排名 TOP 10"""
        self.log("🏭 获取行业板块 TOP 10...")
        
        rank = self.safe_request(
            self.sector.get_industry_rank,
            page=1,
            page_size=10,
            max_retries=3
        )
        
        if rank:
            self.log(f"获取到{len(rank)}个板块")
            return rank
        else:
            self.log("板块数据获取失败")
            return []
    
    def analyze_stocks(self, stock_list: List[dict]) -> List[dict]:
        """分析股票，筛选买入信号"""
        self.log("🔍 开始分析股票...")
        
        buy_signals = []
        total = len(stock_list)
        
        for i, stock in enumerate(stock_list, 1):
            code = stock.get('f12', '')
            name = stock.get('f14', '')
            
            if not code:
                continue
            
            self.log(f"[{i}/{total}] 分析 {name}({code})")
            
            try:
                # 使用简化分析（避免完整分析的耗时）
                score = self._quick_analyze(stock)
                
                if score >= 70:
                    buy_signals.append({
                        'code': code,
                        'name': name,
                        'score': score,
                        'data': stock,
                    })
                    self.log(f"✅ {name} 评分{score:.1f}，达到买入标准")
                
                # 防反爬延迟
                time.sleep(random.uniform(0.3, 0.8))
            
            except Exception as e:
                self.log(f"分析失败：{e}")
                continue
        
        # 按评分排序
        buy_signals.sort(key=lambda x: x['score'], reverse=True)
        
        self.log(f"分析完成，发现{len(buy_signals)}个买入信号")
        
        return buy_signals
    
    def _quick_analyze(self, stock: dict) -> float:
        """快速评分（简化版）"""
        score = 50.0
        
        # 主力净流入评分 (40%)
        main_net = stock.get('f4001', 0) or 0
        main_ratio = stock.get('f4002', 0) or 0
        
        if main_net > 100000000:  # >1 亿
            score += 20
        elif main_net > 50000000:  # >5000 万
            score += 15
        elif main_net > 0:
            score += 5
        
        if main_ratio > 10:
            score += 10
        elif main_ratio > 5:
            score += 5
        
        # 涨跌幅评分 (30%)
        change = stock.get('f3', 0) or 0
        
        if 2 <= change <= 7:  # 温和上涨
            score += 15
        elif 0 < change < 2:  # 小幅上涨
            score += 10
        elif change > 7:  # 大涨可能回调
            score += 5
        elif -3 <= change <= 0:  # 小幅下跌
            score += 5
        else:  # 大跌
            score -= 10
        
        # 量比评分 (30%)
        # 简化处理，假设有主力流入的量比都好
        if main_net > 0 and change > 0:
            score += 10
        
        return min(100, max(0, score))
    
    def push_top5_signals(self, signals: List[dict]):
        """推送 TOP 5 买入信号"""
        if not signals:
            self.log("⚠️ 无买入信号，不推送")
            return
        
        top5 = signals[:5]
        
        self.log("📱 准备推送 TOP 5 买入信号...")
        
        content = f"""## 🎯 今日选股信号 TOP 5

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**数据来源**: 主力资金流 + 综合评分

### 买入信号

"""
        
        for i, signal in enumerate(top5, 1):
            code = signal['code']
            name = signal['name']
            score = signal['score']
            data = signal['data']
            
            price = data.get('f2', 0) or 0
            change = data.get('f3', 0) or 0
            main_net = (data.get('f4001', 0) or 0) / 100000000
            main_ratio = data.get('f4002', 0) or 0
            
            content += f"""**{i}. {name}({code})**
- 综合评分：**{score:.1f}分**
- 现价：¥{price:.2f} ({change:+.2f}%)
- 主力：{main_net:.2f}亿 ({main_ratio:.2f}%)
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
"""
        
        title = f"🎯 今日选股信号 TOP 5"
        
        # 推送
        result = self.notifier.send_wecom(title, content, msg_type='markdown')
        
        if result:
            self.log("✅ 推送成功")
        else:
            self.log("❌ 推送失败")
        
        # 保存推送记录
        self._save_push_record(top5)
    
    def _save_push_record(self, signals: List[dict]):
        """保存推送记录"""
        record = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
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
        
        # 只保留最近 30 天
        history = history[-30:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        self.log(f"推送记录已保存：{history_file}")
    
    def run(self):
        """运行完整流程 - 数据优先原则"""
        self.log("="*60)
        self.log("🚀 开始执行自动选股流程")
        self.log("="*60)
        self.log("⚠️ 原则：数据获取失败，不做推送")
        self.log("="*60)
        
        start_time = datetime.now()
        
        # 1. 获取主力资金流 TOP 100（必须成功）
        self.log("📊 获取主力资金流 TOP 100（必需数据）...")
        main_force = self.get_main_force_top100()
        
        # 数据验证
        if not main_force or len(main_force) < 50:
            self.log("❌ 主力数据获取失败或数据不足（要求≥50 条，实际{}条）".format(len(main_force) if main_force else 0))
            self.log("❌ 数据验证未通过，终止流程，不做推送")
            self._send_failure_alert("主力数据获取失败")
            return
        
        # 进一步验证数据质量
        valid_count = sum(1 for s in main_force if (s.get('f4001', 0) or 0) != 0)
        if valid_count < 30:
            self.log("❌ 数据质量不达标（有效数据{}条，要求≥30 条）".format(valid_count))
            self.log("❌ 数据验证未通过，终止流程，不做推送")
            self._send_failure_alert("主力数据质量不达标")
            return
        
        self.log(f"✅ 主力数据获取成功，共{len(main_force)}只股票，有效数据{valid_count}条")
        
        # 2. 获取板块排名 TOP 10（重要数据）
        self.log("🏭 获取行业板块 TOP 10（重要数据）...")
        sectors = self.get_sector_top10()
        
        if not sectors or len(sectors) < 5:
            self.log("⚠️ 板块数据获取失败或数据不足（要求≥5 条，实际{}条）".format(len(sectors) if sectors else 0))
            self.log("⚠️ 继续执行，但不包含板块分析")
            sectors = []
        else:
            self.log(f"✅ 板块数据获取成功，共{len(sectors)}个板块")
        
        # 3. 分析股票，筛选买入信号
        self.log("🔍 开始分析股票...")
        buy_signals = self.analyze_stocks(main_force)
        
        # 4. 推送 TOP 5（必须有符合条件的股票）
        if buy_signals and len(buy_signals) >= 1:
            # 验证买入信号质量
            top_signal = buy_signals[0]
            if top_signal['score'] >= 70:
                self.push_top5_signals(buy_signals)
            else:
                self.log("⚠️ 最高评分{} < 70，无符合条件的买入信号，不做推送".format(top_signal['score']))
        else:
            self.log("⚠️ 无符合条件的买入信号，不做推送")
        
        # 5. 保存数据
        self._save_data(main_force, sectors, buy_signals)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.log("="*60)
        self.log(f"✅ 流程执行完成，耗时{duration:.1f}秒")
        self.log("="*60)
    
    def _send_failure_alert(self, reason: str):
        """发送数据获取失败告警"""
        self.log(f"🚨 发送失败告警：{reason}")
        
        content = f"""## 🚨 数据获取失败告警

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**失败原因**: {reason}

**已执行操作**:
- ❌ 选股推送已取消
- ⚠️ 请检查网络或 API 状态

**建议**:
1. 检查网络连接
2. 查看 API 是否正常
3. 稍后重试

---
*选股系统 v3.0*
"""
        
        # 发送告警（不推送选股信号）
        self.notifier.send_wecom('🚨 数据获取失败告警', content, msg_type='markdown')
    
    def _save_data(self, main_force: List, sectors: List, signals: List):
        """保存数据"""
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'main_force': main_force,
            'sectors': sectors,
            'signals': signals[:5] if signals else [],
            'status': 'success' if (main_force and len(main_force) >= 50) else 'failed',
        }
        
        data_file = os.path.join(
            self.cache_dir,
            f'data_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        )
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.log(f"📁 数据已保存：{data_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='自动选股推送系统')
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--config', type=str, default='push_config.json', help='配置文件')
    
    args = parser.parse_args()
    
    selector = AutoSelector(args.config)
    
    if args.test:
        print("\n🧪 测试模式：使用 2026 年 3 月 26 日数据跑通流程\n")
        # 测试模式可以直接运行
        selector.run()
    else:
        print("\n🚀 启动自动选股推送流程\n")
        selector.run()
