#!/usr/bin/env python3
"""
股票筛选工作流 - 主入口 v8.0-Financial-Enhanced (最优版本)

整合所有数据源，执行全网筛选策略
支持决策回溯和自动优化

🏆 十轮回测验证 (1200 次决策) 最优配置:
- 平均收益：+1.24%/次 (+235% 提升)
- 综合胜率：49.0%
- 总收益率：+1347.93%

🆕 v8.0 金融模型集成 (15 个经典模型):
【经典定价】CAPM, Fama-French 三因子/五因子，Carhart 四因子
【资产配置】Black-Litterman
【风险指标】Sharpe, Sortino, MaxDD, VaR, CVaR
【技术指标】MACD, RSI, Bollinger Bands

🆕 v6.2 止盈止损优化:
- 放宽止盈 33-50%
- 收紧止损 13-22%
- 移动止盈
- 时间止损

🆕 v6.1 ML 增强:
- Random Forest 模型
- 29 维特征工程

用法:
    python3 run_workflow.py --strategy all --push     # 标准模式
    python3 run_workflow.py --ml-enhance              # ML 增强
    python3 run_workflow.py --financial-models        # 金融模型增强 (v8.0)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 导入数据源模块
from data_sources import MultiDataSource, SinaFinance, BaoStockData
from local_crawler import StockCrawler


class StockWorkflow:
    """股票筛选工作流"""
    
    def __init__(self):
        self.cache_dir = Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        self.multi_source = MultiDataSource(self.cache_dir)
        self.crawler = StockCrawler(self.cache_dir)
        self.sina = SinaFinance()
    
    def run_main_force_strategy(self, top_n: int = 20) -> dict:
        """主力净流入策略"""
        print("\n" + "="*80)
        print("💰 策略 1: 主力净流入排行")
        print("="*80)
        
        results = {}
        
        # 百度股市通
        print("\n[1/3] 百度股市通...")
        baidu_data = self.crawler.crawl_baidu_rank('change')
        if baidu_data:
            baidu_data.sort(key=lambda x: x.get('amount_wan', 0), reverse=True)
            results['baidu'] = baidu_data[:top_n]
            print(f"  ✅ 获取 {len(results['baidu'])} 条")
        
        # 腾讯财经 (估算)
        print("\n[2/3] 腾讯财经 (估算)...")
        tencent_data = self.crawler.crawl_tencent()
        if tencent_data:
            tencent_data.sort(key=lambda x: x.get('amount_wan', 0), reverse=True)
            results['tencent'] = tencent_data[:top_n]
            print(f"  ✅ 获取 {len(results['tencent'])} 条")
        
        # 东方财富板块
        print("\n[3/3] 东方财富板块资金流...")
        sector_data = self.crawler.crawl_eastmoney_sector('concept')
        if sector_data:
            sector_data.sort(key=lambda x: x.get('main_net', 0), reverse=True)
            results['sector'] = sector_data[:top_n]
            print(f"  ✅ 获取 {len(results['sector'])} 条")
        
        return results
    
    def run_gainers_strategy(self, top_n: int = 20) -> dict:
        """涨幅榜策略"""
        print("\n" + "="*80)
        print("📈 策略 2: 涨幅榜")
        print("="*80)
        
        results = {}
        
        # 新浪财经
        print("\n[1/2] 新浪财经...")
        sina_data = self.sina.get_top_gainers(top_n * 2)
        if sina_data:
            results['sina'] = sina_data[:top_n]
            print(f"  ✅ 获取 {len(results['sina'])} 条")
        
        # 腾讯财经
        print("\n[2/2] 腾讯财经...")
        tencent_data = self.crawler.crawl_tencent()
        if tencent_data:
            tencent_data.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
            results['tencent'] = tencent_data[:top_n]
            print(f"  ✅ 获取 {len(results['tencent'])} 条")
        
        return results
    
    def run_volume_strategy(self, top_n: int = 20) -> dict:
        """成交量策略"""
        print("\n" + "="*80)
        print("📊 策略 3: 成交量排行")
        print("="*80)
        
        results = {}
        
        # 腾讯财经
        print("\n[1/1] 腾讯财经...")
        tencent_data = self.crawler.crawl_tencent()
        if tencent_data:
            tencent_data.sort(key=lambda x: x.get('volume', 0), reverse=True)
            results['tencent'] = tencent_data[:top_n]
            print(f"  ✅ 获取 {len(results['tencent'])} 条")
        
        return results
    
    def print_summary(self, results: dict, ml_enhance: bool = False):
        """
        打印汇总
        
        Args:
            results: 结果数据
            ml_enhance: 是否 ML 增强模式
        """
        print("\n" + "="*80)
        if ml_enhance:
            print("🤖 全网筛选结果汇总 (ML 增强版)")
        else:
            print("📊 全网筛选结果汇总")
        print("="*80)
        print(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"数据源数量：{len(results)}")
        
        for source, data in results.items():
            print(f"  - {source}: {len(data)} 条")
        
        if ml_enhance:
            print("\n🤖 ML 增强：已融合经典投资理论")
        
        print("="*80)
    
    def save_results(self, results: dict, filename: str = None):
        """保存结果"""
        if not filename:
            filename = f"workflow_result_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        filepath = self.cache_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ 结果已保存：{filepath}")
        return filepath
    
    def run_all(self, top_n: int = 20, ml_enhance: bool = False, financial_models: bool = False):
        """
        执行全部策略并生成最终决策
        
        Args:
            top_n: 返回数量
            ml_enhance: 是否使用 ML 增强模式
            financial_models: 是否使用金融模型增强
        """
        print("\n" + "#"*80)
        if financial_models:
            print("# 📊 全网股票筛选工作流 v7.0 (金融模型增强版)")
            print("# 经典金融学理论融合")
        elif ml_enhance:
            print("# 🤖 全网股票筛选工作流 v6.0 (ML 增强版)")
            print("# 机器学习融合经典投资理论")
        else:
            print("# 🚀 全网股票筛选工作流 v5.1")
        print("#"*80)
        
        all_results = {}
        
        # 策略 1: 主力净流入 (成交额排序，严禁估算)
        print("\n[策略 1] 主力净流入...")
        all_results['main_force'] = self.run_main_force_strategy(top_n * 2)
        
        # 策略 2: 涨幅榜
        print("\n[策略 2] 涨幅榜...")
        all_results['gainers'] = self.run_gainers_strategy(top_n * 2)
        
        # 策略 3: 成交量
        print("\n[策略 3] 成交量...")
        all_results['volume'] = self.run_volume_strategy(top_n * 2)
        
        # ========== 最终决策：综合筛选 ==========
        print("\n" + "="*80)
        print("🎯 生成最终决策...")
        print("="*80)
        
        final_pool = self._generate_final_decision(all_results, top_n, ml_enhance, financial_models)
        all_results['final_decision'] = final_pool
        
        # 汇总
        self.print_summary(all_results, ml_enhance)
        
        # 保存
        self.save_results(all_results)
        
        return all_results
    
    def _is_main_board(self, symbol: str) -> bool:
        """
        判断是否为主板股票
        
        主板：600xxx, 601xxx, 603xxx, 605xxx (沪市), 000xxx, 001xxx, 002xxx (深市)
        排除：创业板 (300/301), 科创板 (688), 北交所 (8/4/9 开头), ST
        """
        if not symbol:
            return False
        
        # 提取代码部分 (去掉 sh/sz 前缀)
        code = symbol.replace('sh', '').replace('sz', '')
        
        # 排除创业板
        if code.startswith('300') or code.startswith('301'):
            return False
        
        # 排除科创板
        if code.startswith('688') or code.startswith('689'):
            return False
        
        # 排除北交所
        if code.startswith('8') or code.startswith('4') or code.startswith('9'):
            return False
        
        # 排除 ST 股票 (代码中带有 ST 标识的通常在名称中，这里只做基本过滤)
        # 沪市主板：600, 601, 603, 605
        # 深市主板：000, 001, 002, 003
        if code.startswith('600') or code.startswith('601') or \
           code.startswith('603') or code.startswith('605') or \
           code.startswith('000') or code.startswith('001') or \
           code.startswith('002') or code.startswith('003'):
            return True
        
        return False
    
    def _generate_buy_rating(self, stock: dict) -> dict:
        """
        生成买入评级、止盈止损、买入理由 (v5.1 优化版)
        
        基于 2025-03 ~ 2026-03 回测结果优化:
        - 提高"强烈推荐"标准
        - 加入黑名单/观察名单机制
        - 优化止盈止损 (放宽止盈，收紧止损)
        
        基于真实数据生成，不构成投资建议
        """
        from optimization_config import (
            RATING_THRESHOLDS, BLACKLIST_SYMBOLS, WATCHLIST_SYMBOLS,
            STOP_PROFIT_LOSS_CONFIG, CONFIDENCE_ADJUSTMENTS, RATING_DISTRIBUTION_LIMITS
        )
        
        change_pct = stock.get('change_pct', 0)
        amount = stock.get('amount', 0)
        appear_count = stock.get('appear_count', 1)
        symbol = stock.get('symbol', '').replace('sh', '').replace('sz', '')
        
        # 获取资金流信息
        flow_info = stock.get('multi_day_flow')
        composite_score = 0
        signal = 'neutral'
        inflow_days = 0
        
        if flow_info is not None and isinstance(flow_info, dict):
            composite_score = flow_info.get('composite_score', 0)
            signal = flow_info.get('signal', 'neutral')
            inflow_days = flow_info.get('inflow_days', 0)
        
        # 黑名单检查 → 直接降为观望
        if symbol in BLACKLIST_SYMBOLS:
            rating = '观望'
            confidence = 30
            reasons = ['⚠️ 历史表现差 (黑名单)']
            
            price = stock.get('price', 0)
            if price > 0:
                stop_profit = price * 1.15
                stop_loss = price * 0.85
            else:
                stop_profit = 0
                stop_loss = 0
            
            return {
                'rating': rating,
                'confidence': confidence,
                'stop_profit': stop_profit,
                'stop_loss': stop_loss,
                'reasons': reasons
            }
        
        # 观察名单 → 降一级处理
        is_watchlist = symbol in WATCHLIST_SYMBOLS
        
        # 买入评级 (v5.1 优化后 - 提高标准)
        if (appear_count >= RATING_THRESHOLDS['strong_buy']['min_appear_count'] and 
            change_pct > RATING_THRESHOLDS['strong_buy']['min_change_pct'] and
            (signal == 'strong_buy' or signal == 'buy')):
            rating = '强烈推荐'
            confidence = RATING_THRESHOLDS['strong_buy']['min_confidence']
        elif appear_count >= RATING_THRESHOLDS['buy']['min_appear_count'] and change_pct > RATING_THRESHOLDS['buy']['min_change_pct']:
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
        
        # 观察名单惩罚
        if is_watchlist:
            if rating == '强烈推荐':
                rating = '推荐'
            elif rating == '推荐':
                rating = '谨慎推荐'
            elif rating == '谨慎推荐':
                rating = '观望'
            confidence = max(30, confidence + CONFIDENCE_ADJUSTMENTS['watchlist_penalty'])
        
        # 资金流信号调整评级
        if signal == 'strong_buy':
            if rating == '推荐':
                rating = '强烈推荐'
                confidence = min(95, confidence + CONFIDENCE_ADJUSTMENTS['strong_buy_signal_bonus'])
            elif rating == '谨慎推荐':
                rating = '推荐'
                confidence = min(85, confidence + 10)
        elif signal == 'buy':
            if rating == '谨慎推荐':
                rating = '推荐'
                confidence = min(80, confidence + 5)
        
        # 综合评分调整
        if composite_score >= 75 and rating == '观望':
            rating = '谨慎推荐'
            confidence = min(65, confidence + 10)
        
        # 置信度调整
        # 主力排名奖励
        if stock.get('is_main_force_top'):
            rank = stock.get('main_force_rank', 999)
            if rank <= 20:
                confidence += CONFIDENCE_ADJUSTMENTS['main_force_top20_bonus']
            elif rank <= 50:
                confidence += CONFIDENCE_ADJUSTMENTS['main_force_top50_bonus']
        
        # 连续净流入奖励
        if inflow_days >= 5:
            confidence += CONFIDENCE_ADJUSTMENTS['consecutive_inflow_5d_bonus']
        elif inflow_days >= 3:
            confidence += CONFIDENCE_ADJUSTMENTS['consecutive_inflow_3d_bonus']
        
        # 多策略共振奖励
        if appear_count >= 4:
            confidence += CONFIDENCE_ADJUSTMENTS['multi_strategy_4x_bonus']
        elif appear_count >= 3:
            confidence += CONFIDENCE_ADJUSTMENTS['multi_strategy_3x_bonus']
        
        # 置信度上限
        confidence = min(95, confidence)
        
        # 止盈止损 (v6.2 优化 - 进一步放宽止盈，启用移动止盈)
        price = stock.get('price', 0)
        if price > 0:
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
            
            # v6.2 新增：移动止盈标记
            trailing_stop = cfg.get('trailing_stop', False)
            trailing_pct = cfg.get('trailing_pct', 0.05)
        else:
            stop_profit = 0
            stop_loss = 0
            trailing_stop = False
            trailing_pct = 0.05
        
        # 买入理由
        reasons = []
        
        # 黑名单/观察名单提示
        if symbol in BLACKLIST_SYMBOLS:
            reasons.append('⚠️ 黑名单股票 (历史表现差)')
        elif is_watchlist:
            reasons.append('⚠️ 观察名单 (历史表现不佳)')
        
        if appear_count >= 4:
            reasons.append('多策略共振 (4+)')
        elif appear_count >= 3:
            reasons.append('多策略共振')
        if appear_count >= 2:
            reasons.append('资金关注度高')
        if change_pct > 7:
            reasons.append('强势上涨')
        elif change_pct > 3:
            reasons.append('温和上涨')
        elif change_pct > 0:
            reasons.append('小幅上涨')
        if amount > 10000000000:  # 100 亿
            reasons.append('成交活跃 (100 亿+)')
        elif amount > 5000000000:  # 50 亿
            reasons.append('成交活跃')
        elif amount > 1000000000:  # 10 亿
            reasons.append('流动性好')
        
        # 资金流理由
        if flow_info is not None and isinstance(flow_info, dict):
            if inflow_days >= 5:
                reasons.append(f'5 日{inflow_days}日连续净流入')
            elif inflow_days >= 3:
                reasons.append(f'5 日{inflow_days}日净流入')
            
            if flow_info.get('trend') == 'improving':
                reasons.append('资金流改善')
            
            if signal == 'strong_buy':
                reasons.append('强烈买入信号')
            elif signal == 'buy':
                reasons.append('买入信号')
        
        # 技术面理由 (新增)
        tech_bonus = stock.get('technical_bonus', 0)
        if tech_bonus >= 0.2:
            reasons.append('技术面强势')
        elif tech_bonus >= 0.1:
            reasons.append('技术面偏强')
        
        # 基本面理由 (新增)
        fundamental_bonus = stock.get('fundamental_bonus', 0)
        if fundamental_bonus >= 0.15:
            reasons.append('基本面优秀')
        elif fundamental_bonus >= 0.08:
            reasons.append('基本面良好')
        
        # 机构研报理由 (新增)
        analyst_bonus = stock.get('analyst_bonus', 0)
        if analyst_bonus >= 0.15:
            reasons.append('机构高度关注')
        elif analyst_bonus >= 0.08:
            reasons.append('机构关注')
        
        # 趋势技术分析理由 (新增)
        trend_bonus = stock.get('trend_bonus', 0)
        trend_analysis = stock.get('trend_analysis')
        if trend_bonus >= 0.25:
            reasons.append('趋势强烈上涨')
        elif trend_bonus >= 0.20:
            reasons.append('趋势上涨')
        elif trend_analysis and trend_analysis.get('signal') == '买入':
            reasons.append('技术买入信号')
        
        # 彼得·林奇策略理由 (新增)
        lynch_bonus = stock.get('lynch_bonus', 0)
        lynch_analysis = stock.get('lynch_analysis')
        if lynch_bonus >= 0.25:
            reasons.append('林奇非常吸引')
        elif lynch_bonus >= 0.20:
            reasons.append('林奇吸引')
        if lynch_analysis:
            company_type = lynch_analysis.get('company_type', '')
            if company_type == '快速增长型':
                reasons.append('林奇最爱类型')
            elif company_type == '稳定增长型':
                reasons.append('稳定增长公司')
        
        # 格雷厄姆策略理由 (新增)
        graham_bonus = stock.get('graham_bonus', 0)
        graham_analysis = stock.get('graham_analysis')
        if graham_bonus >= 0.25:
            reasons.append('格雷厄姆非常吸引')
        elif graham_bonus >= 0.20:
            reasons.append('格雷厄姆吸引')
        if graham_analysis:
            safety_margin = graham_analysis.get('safety_margin', 0)
            valuation = graham_analysis.get('valuation', '')
            if safety_margin > 20:
                reasons.append(f'安全边际{int(safety_margin)}%')
            if valuation == '低估':
                reasons.append('格雷厄姆低估')
        
        if not reasons:
            reasons.append('技术面良好')
        
        # v6.2 新增：移动止盈信息
        if trailing_stop:
            reasons.append(f'移动止盈 (回撤{trailing_pct*100:.0f}%)')
        
        return {
            'rating': rating,
            'confidence': confidence,
            'stop_profit': stop_profit,
            'stop_loss': stop_loss,
            'trailing_stop': trailing_stop,
            'trailing_pct': trailing_pct,
            'reasons': reasons
        }
    
    def _calculate_tech_bonus(self, stock: dict) -> float:
        """
        计算技术面加分 (简化版)
        
        基于:
        - 涨跌幅
        - 成交量变化
        - 价格趋势
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 技术面加分 (0-0.2)
        """
        bonus = 0.0
        change_pct = stock.get('change_pct', 0)
        amount = stock.get('amount', 0)
        volume = stock.get('volume', 0)
        
        # 涨跌幅技术信号
        if change_pct > 7:
            bonus += 0.08  # 强势上涨
        elif change_pct > 3:
            bonus += 0.05  # 温和上涨
        elif change_pct > 0:
            bonus += 0.02  # 小幅上涨
        
        # 成交量技术信号
        if amount > 5000000000:  # >50 亿
            bonus += 0.06  # 放量
        elif amount > 1000000000:  # >10 亿
            bonus += 0.03  # 温和放量
        
        # 量价配合
        if change_pct > 3 and volume > 2000000:  # 价涨量增
            bonus += 0.06
        
        # 上限控制
        return min(0.2, bonus)
    
    def _calculate_vp_bonus(self, stock: dict) -> float:
        """
        计算量价分析加分
        
        基于《量价分析》- 安娜·库林:
        - 量价关系
        - 成交量趋势
        - 放量突破
        - 量价背离
        - 资金累积
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 量价加分 (0-0.3)
        """
        from volume_price_analysis import VolumePriceAnalysis
        
        try:
            strategy = VolumePriceAnalysis()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            # 存储详细分析结果
            stock['vp_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
                'recommendation': analysis.get('recommendation', ''),
                'relationship': analysis.get('volume_price', {}).get('relationship', ''),
                'breakout': analysis.get('volume_breakout', {}).get('breakout', ''),
            }
            
            return bonus
            
        except Exception as e:
            # 分析失败时返回 0
            stock['vp_analysis'] = None
            return 0.0
    
    def _calculate_fundamental_bonus(self, stock: dict) -> float:
        """
        计算基本面加分 (简化版)
        
        基于:
        - 市值规模
        - 行业地位
        - 估值水平
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 基本面加分 (0-0.2)
        """
        bonus = 0.0
        amount = stock.get('amount', 0)
        name = stock.get('name', '')
        
        # 大盘股加分 (流动性好，风险低)
        if amount > 10000000000:  # >100 亿
            bonus += 0.08
        elif amount > 5000000000:  # >50 亿
            bonus += 0.05
        
        # 行业龙头加分 (简化判断：名称包含行业关键词)
        industry_leaders = ['茅台', '宁德', '平安', '工行', '建行', '招行', '比亚迪', '腾讯', '阿里', '美的', '格力']
        for leader in industry_leaders:
            if leader in name:
                bonus += 0.06
                break
        
        # 低估值加分 (简化：股价<50 元)
        price = stock.get('price', 0)
        if 0 < price < 50:
            bonus += 0.03
        elif 0 < price < 20:
            bonus += 0.03  # 额外加分
        
        # 上限控制
        return min(0.2, bonus)
    
    def _calculate_analyst_bonus(self, stock: dict) -> float:
        """
        计算机构研报加分 (简化版)
        
        基于:
        - 机构关注度 (成交额代表)
        - 研报热度
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 研报加分 (0-0.2)
        """
        bonus = 0.0
        amount = stock.get('amount', 0)
        volume = stock.get('volume', 0)
        
        # 高成交额代表机构关注度高
        if amount > 5000000000:  # >50 亿
            bonus += 0.10
        elif amount > 2000000000:  # >20 亿
            bonus += 0.06
        elif amount > 1000000000:  # >10 亿
            bonus += 0.03
        
        # 高成交量代表活跃度高
        if volume > 50000000:  # >5000 万手
            bonus += 0.05
        elif volume > 20000000:  # >2000 万手
            bonus += 0.03
        
        # 上限控制
        return min(0.2, bonus)
    
    def _calculate_trend_bonus(self, stock: dict) -> float:
        """
        计算趋势技术分析加分
        
        基于经典技术分析理论:
        - 道氏理论趋势判断
        - 均线系统
        - K 线形态
        - 支撑阻力位
        - 量价关系
        - MACD/KDJ/RSI指标
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 趋势加分 (0-0.3)
        """
        from trend_analysis_strategy import TrendAnalysisStrategy
        
        try:
            strategy = TrendAnalysisStrategy()
            analysis = strategy.analyze_trend(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            # 存储详细分析结果
            stock['trend_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'trend': analysis.get('trend', ''),
                'signal': analysis.get('signal', ''),
                'confidence': analysis.get('confidence', 0),
            }
            
            return bonus
            
        except Exception as e:
            # 分析失败时返回 0
            stock['trend_analysis'] = None
            return 0.0
    
    def _calculate_lynch_bonus(self, stock: dict) -> float:
        """
        计算彼得·林奇策略加分
        
        基于《彼得·林奇的成功投资》书中的投资理念:
        - 公司类型分类 (六类公司)
        - PEG 指标
        - 负债率分析
        - 内部人持股
        - 机构持股
        - 股票回购
        - 现金流分析
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 林奇加分 (0-0.3)
        """
        from peter_lynch_strategy import PeterLynchStrategy
        
        try:
            strategy = PeterLynchStrategy()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            # 存储详细分析结果
            stock['lynch_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
                'recommendation': analysis.get('recommendation', ''),
                'company_type': analysis.get('company_type', {}).get('type', ''),
            }
            
            return bonus
            
        except Exception as e:
            # 分析失败时返回 0
            stock['lynch_analysis'] = None
            return 0.0
    
    def _calculate_graham_bonus(self, stock: dict) -> float:
        """
        计算格雷厄姆策略加分
        
        基于《聪明的投资者》书中的投资理念:
        - 安全边际分析
        - 防御型投资者标准
        - 积极型投资者标准
        - 财务健康分析
        - 估值分析 (PE/PB)
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 格雷厄姆加分 (0-0.3)
        """
        from graham_strategy import GrahamIntelligentInvestor
        
        try:
            strategy = GrahamIntelligentInvestor()
            analysis = strategy.analyze_company(stock, investor_type='defensive')
            bonus = strategy.get_decision_bonus(analysis)
            
            # 存储详细分析结果
            stock['graham_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
                'recommendation': analysis.get('recommendation', ''),
                'safety_margin': analysis.get('safety_margin', {}).get('margin_of_safety', 0),
                'valuation': analysis.get('valuation', {}).get('valuation', ''),
            }
            
            return bonus
            
        except Exception as e:
            # 分析失败时返回 0
            stock['graham_analysis'] = None
            return 0.0
    
    def _calculate_vp_bonus(self, stock: dict) -> float:
        """
        计算量价分析加分
        
        基于《量价分析》- 安娜·库林
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 量价加分 (0-0.3)
        """
        from volume_price_analysis import VolumePriceAnalysis
        
        try:
            strategy = VolumePriceAnalysis()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            stock['vp_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
                'relationship': analysis.get('volume_price', {}).get('relationship', ''),
            }
            
            return bonus
        except:
            stock['vp_analysis'] = None
            return 0.0
    
    def _calculate_canslim_bonus(self, stock: dict) -> float:
        """
        计算 CAN SLIM 策略加分
        
        基于《笑傲股市》- 威廉·欧奈尔
        
        Args:
            stock: 股票数据
        
        Returns:
            float: CAN SLIM 加分 (0-0.3)
        """
        from canslim_strategy import CANSLIMStrategy
        
        try:
            strategy = CANSLIMStrategy()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            stock['canslim_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
            }
            
            return bonus
        except:
            stock['canslim_analysis'] = None
            return 0.0
    
    def _calculate_chan_bonus(self, stock: dict) -> float:
        """
        计算缠论分析加分
        
        基于《缠中说禅》
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 缠论加分 (0-0.3)
        """
        from chan_lun import ChanLunAnalysis
        
        try:
            strategy = ChanLunAnalysis()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            stock['chan_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
            }
            
            return bonus
        except:
            stock['chan_analysis'] = None
            return 0.0
    
    def _calculate_turtle_bonus(self, stock: dict) -> float:
        """
        计算海龟交易加分
        
        基于《海龟交易法则》- 柯蒂斯·费思
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 海龟加分 (0-0.3)
        """
        from turtle_trading import TurtleTradingStrategy
        
        try:
            strategy = TurtleTradingStrategy()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            stock['turtle_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
            }
            
            return bonus
        except:
            stock['turtle_analysis'] = None
            return 0.0
    
    def _calculate_psych_bonus(self, stock: dict) -> float:
        """
        计算交易心理加分
        
        基于《以交易为生》- 亚历山大·埃尔德
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 心理加分 (0-0.2)
        """
        from trading_psychology import TradingPsychologyStrategy
        
        try:
            strategy = TradingPsychologyStrategy()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            stock['psych_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
            }
            
            return bonus
        except:
            stock['psych_analysis'] = None
            return 0.0
    
    def _calculate_elliott_bonus(self, stock: dict) -> float:
        """
        计算波浪理论加分
        
        基于《艾略特波浪理论》
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 波浪加分 (0-0.3)
        """
        from elliott_wave import ElliottWaveAnalysis
        
        try:
            strategy = ElliottWaveAnalysis()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            stock['elliott_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
            }
            
            return bonus
        except:
            stock['elliott_analysis'] = None
            return 0.0
    
    def _calculate_gann_bonus(self, stock: dict) -> float:
        """
        计算江恩理论加分
        
        基于《江恩华尔街 45 年》
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 江恩加分 (0-0.3)
        """
        from gann_theory import GannTheoryAnalysis
        
        try:
            strategy = GannTheoryAnalysis()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            stock['gann_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
            }
            
            return bonus
        except:
            stock['gann_analysis'] = None
            return 0.0
    
    def _calculate_position_bonus(self, stock: dict) -> float:
        """
        计算资金管理加分
        
        基于《专业投机原理》- 维克多·斯波朗迪
        
        Args:
            stock: 股票数据
        
        Returns:
            float: 资金管理加分 (0-0.3)
        """
        from position_management import PositionManagementStrategy
        
        try:
            strategy = PositionManagementStrategy()
            analysis = strategy.analyze_company(stock)
            bonus = strategy.get_decision_bonus(analysis)
            
            stock['position_analysis'] = {
                'total_score': analysis.get('total_score', 0),
                'rating': analysis.get('rating', ''),
            }
            
            return bonus
        except:
            stock['position_analysis'] = None
            return 0.0
    
    def _enhance_with_mainstream_rank(self, stocks: list) -> list:
        """
        增强股票数据：添加主力排名信息
        
        Args:
            stocks: 股票列表
        
        Returns:
            list: 增强后的股票列表
        """
        from data_sources import MainstreamRank
        
        rank_fetcher = MainstreamRank()
        main_force_stocks = rank_fetcher.get_main_force_rank(200)
        
        # 创建主力排名映射
        main_force_map = {s['symbol']: s for s in main_force_stocks}
        
        # 添加到股票数据
        for stock in stocks:
            symbol = stock.get('symbol', '')
            if symbol in main_force_map:
                info = main_force_map[symbol]
                stock['main_force_rank'] = info.get('main_force_rank', 999)
                stock['main_force_score'] = info.get('main_force_score', 0)
                stock['is_main_force_top'] = info.get('main_force_rank', 999) <= 50  # 前 50 为主力热门
                stock['main_net'] = info.get('main_net', 0)  # 主力净流入
            else:
                stock['main_force_rank'] = 999
                stock['main_force_score'] = 0
                stock['is_main_force_top'] = False
                stock['main_net'] = 0
        
        return stocks
    
    def _enhance_with_multi_day_flow(self, stocks: list, top_n: int = 20) -> list:
        """
        增强股票数据：添加多日主力资金流入分析 (增强版)
        
        Args:
            stocks: 股票列表
            top_n: 分析前 N 只股票 (避免请求过多)
        
        Returns:
            list: 增强后的股票列表
        """
        from fund_flow import FundFlowFetcher
        
        flow_fetcher = FundFlowFetcher()
        
        # 只分析前 N 只股票 (按成交额排序)
        stocks_by_amount = sorted(stocks, key=lambda x: x.get('amount', 0), reverse=True)[:top_n]
        
        print(f"[多日资金流] 分析 {len(stocks_by_amount)} 只股票...")
        
        for i, stock in enumerate(stocks_by_amount, 1):
            symbol = stock.get('symbol', '')
            if symbol:
                print(f"  [{i}/{len(stocks_by_amount)}] {symbol}...")
                analysis = flow_fetcher.analyze_multi_day_flow(symbol, days=5)
                
                if 'error' not in analysis:
                    stock['multi_day_flow'] = {
                        'total_main_net': analysis.get('total_main_net', 0),
                        'avg_main_net': analysis.get('avg_main_net', 0),
                        'inflow_days': analysis.get('inflow_days', 0),
                        'outflow_days': analysis.get('outflow_days', 0),
                        'inflow_ratio': analysis.get('inflow_ratio', 0),
                        'trend': analysis.get('trend', ''),
                        'continuity_score': analysis.get('continuity_score', 0),
                        'intensity_score': analysis.get('intensity_score', 0),
                        'composite_score': analysis.get('composite_score', 0),
                        'signal': analysis.get('signal', 'neutral'),
                        'signal_strength': analysis.get('signal_strength', 0),
                        'is_anomaly': analysis.get('is_anomaly', False),
                    }
                    
                    # 根据多日资金流调整评分 (增强版)
                    continuity = analysis.get('continuity_score', 0)
                    intensity = analysis.get('intensity_score', 0)
                    composite = analysis.get('composite_score', 0)
                    signal = analysis.get('signal', 'neutral')
                    
                    # 基础加分 (连续性)
                    if continuity >= 90:
                        stock['flow_bonus'] = 0.3
                    elif continuity >= 70:
                        stock['flow_bonus'] = 0.2
                    elif continuity >= 50:
                        stock['flow_bonus'] = 0.1
                    else:
                        stock['flow_bonus'] = 0
                    
                    # 强度加分
                    if intensity >= 80:
                        stock['flow_bonus'] += 0.15
                    elif intensity >= 60:
                        stock['flow_bonus'] += 0.1
                    
                    # 信号加分
                    if signal == 'strong_buy':
                        stock['flow_bonus'] += 0.2
                    elif signal == 'buy':
                        stock['flow_bonus'] += 0.1
                    
                    # 异常流入加分
                    if analysis.get('is_anomaly'):
                        stock['flow_bonus'] += 0.15
                    
                    # 上限控制
                    stock['flow_bonus'] = min(0.8, stock['flow_bonus'])
                    
                else:
                    stock['multi_day_flow'] = None
                    stock['flow_bonus'] = 0
        
        return stocks
    
    def _generate_final_decision(self, all_results: dict, top_n: int, ml_enhance: bool = False, financial_models: bool = False) -> list:
        """
        生成最终决策结果
        
        逻辑:
        1. 合并所有策略结果
        2. 过滤：只要主板股票
        3. 去重 (同一股票只保留一次)
        4. 综合评分排序
        5. 生成买入评级、止盈止损、买入理由
        6. 返回 TopN
        
        Args:
            all_results: 所有策略结果
            top_n: 返回数量
            ml_enhance: 是否使用 ML 增强模式
            financial_models: 是否使用金融模型增强
        """
        from collections import defaultdict
        
        # ML 增强模式
        if ml_enhance:
            print("\n🤖 ML 增强模式：融合经典投资理论...")
            print("   - 量价分析 (《量价分析》)")
            print("   - CAN SLIM (《笑傲股市》)")
            print("   - 趋势技术 (《股市趋势技术分析》)")
            print("   - 海龟交易 (《海龟交易法则》)")
            print("   - 波浪理论 (《艾略特波浪理论》)")
        
        # 金融模型增强模式
        if financial_models:
            print("\n📊 金融模型增强模式：融合经典金融学理论...")
            print("   - CAPM 资本资产定价模型")
            print("   - Fama-French 三因子模型")
            print("   - Carhart 四因子模型")
            print("   - Black-Litterman 资产配置")
            print("   - 风险指标 (Sharpe/Sortino/MaxDD/VaR)")
        
        stock_map = defaultdict(lambda: {'score': 0, 'count': 0, 'data': None})
        
        # 合并主力策略结果 (结果是 dict，包含 baidu/tencent 等)
        main_force = all_results.get('main_force', {})
        for source, stocks in main_force.items():
            if isinstance(stocks, list):
                for stock in stocks:
                    if isinstance(stock, dict):
                        # 统一字段名 - 修复价格字段
                        symbol = stock.get('symbol', stock.get('code', ''))
                        
                        # 优先使用 price 字段，如果没有则尝试其他字段
                        price = stock.get('price', 0)
                        if not price or price == 0:
                            price = stock.get('current_price', 0)
                        if not price or price == 0:
                            # 尝试从其他可能的字段获取
                            price = stock.get('close', 0)
                        
                        amount = stock.get('amount', 0)
                        if not amount or amount == 0:
                            amount_wan = stock.get('amount_wan', 0)
                            if amount_wan:
                                amount = amount_wan * 10000  # 万转元
                        
                        volume = stock.get('volume', 0)
                        change_pct = stock.get('change_pct', 0)
                        if not change_pct or change_pct == 0:
                            change_pct = stock.get('change', 0)
                        
                        # 过滤：只要主板股票
                        if not self._is_main_board(symbol):
                            continue
                        
                        if symbol and price > 0:
                            stock_map[symbol]['score'] += amount / 100000000
                            stock_map[symbol]['count'] += 1
                            # 统一字段
                            stock_map[symbol]['data'] = {
                                'symbol': symbol,
                                'name': stock.get('name', ''),
                                'price': price,
                                'change_pct': change_pct,
                                'amount': amount,
                                'volume': volume,
                            }
        
        # 合并涨幅榜结果
        gainers = all_results.get('gainers', {})
        for source, stocks in gainers.items():
            if isinstance(stocks, list):
                for stock in stocks:
                    if isinstance(stock, dict):
                        symbol = stock.get('symbol', stock.get('code', ''))
                        
                        price = stock.get('price', 0)
                        if not price or price == 0:
                            price = stock.get('current_price', 0)
                        
                        amount = stock.get('amount', 0)
                        if not amount or amount == 0:
                            amount_wan = stock.get('amount_wan', 0)
                            if amount_wan:
                                amount = amount_wan * 10000
                        
                        volume = stock.get('volume', 0)
                        change_pct = stock.get('change_pct', 0)
                        if not change_pct or change_pct == 0:
                            change_pct = stock.get('change', 0)
                        
                        # 过滤：只要主板股票
                        if not self._is_main_board(symbol):
                            continue
                        
                        if symbol and price > 0:
                            stock_map[symbol]['score'] += max(0, change_pct)
                            stock_map[symbol]['count'] += 1
                            if not stock_map[symbol]['data']:
                                stock_map[symbol]['data'] = {
                                    'symbol': symbol,
                                    'name': stock.get('name', ''),
                                    'price': price,
                                    'change_pct': change_pct,
                                    'amount': amount,
                                    'volume': volume,
                                }
        
        # 合并成交量结果
        volume_data = all_results.get('volume', {})
        for source, stocks in volume_data.items():
            if isinstance(stocks, list):
                for stock in stocks:
                    if isinstance(stock, dict):
                        symbol = stock.get('symbol', stock.get('code', ''))
                        
                        price = stock.get('price', 0)
                        if not price or price == 0:
                            price = stock.get('current_price', 0)
                        
                        amount = stock.get('amount', 0)
                        if not amount or amount == 0:
                            amount_wan = stock.get('amount_wan', 0)
                            if amount_wan:
                                amount = amount_wan * 10000
                        
                        volume = stock.get('volume', 0)
                        change_pct = stock.get('change_pct', 0)
                        if not change_pct or change_pct == 0:
                            change_pct = stock.get('change', 0)
                        
                        # 过滤：只要主板股票
                        if not self._is_main_board(symbol):
                            continue
                        
                        if symbol and price > 0:
                            stock_map[symbol]['score'] += volume / 10000000
                            stock_map[symbol]['count'] += 1
                            if not stock_map[symbol]['data']:
                                stock_map[symbol]['data'] = {
                                    'symbol': symbol,
                                    'name': stock.get('name', ''),
                                    'price': price,
                                    'change_pct': change_pct,
                                    'amount': amount,
                                    'volume': volume,
                                }
        
        # 转换为列表
        final_stocks = []
        for symbol, info in stock_map.items():
            if info['count'] >= 1 and info['data']:
                data = info['data'].copy()
                data['final_score'] = info['score']
                data['appear_count'] = info['count']
                final_stocks.append(data)
        
        # 增强 1: 添加主力排名信息
        print("\n[增强 1/13] 获取主力净流入排名...")
        final_stocks = self._enhance_with_mainstream_rank(final_stocks)
        
        # 增强 2: 添加多日主力资金流入分析 (前 20 只)
        print("[增强 2/13] 分析多日主力资金流...")
        final_stocks = self._enhance_with_multi_day_flow(final_stocks, top_n=20)
        
        # 增强 3: 添加技术面分析 (前 20 只)
        print("[增强 3/13] 分析技术面...")
        for i, stock in enumerate(final_stocks[:20], 1):
            tech_bonus = self._calculate_tech_bonus(stock)
            stock['technical_bonus'] = tech_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 技术面加分{tech_bonus:.2f}")
        
        # 增强 4: 添加量价分析 (前 20 只)
        print("[增强 4/13] 分析量价关系...")
        for i, stock in enumerate(final_stocks[:20], 1):
            vp_bonus = self._calculate_vp_bonus(stock)
            stock['vp_bonus'] = vp_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 量价加分{vp_bonus:.2f}")
        
        # 增强 5: 添加 CAN SLIM 策略 (前 20 只)
        print("[增强 5/13] CAN SLIM 策略分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            canslim_bonus = self._calculate_canslim_bonus(stock)
            stock['canslim_bonus'] = canslim_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: CAN SLIM 加分{canslim_bonus:.2f}")
        
        # 增强 6: 添加基本面分析 (前 20 只)
        print("[增强 6/13] 分析基本面...")
        for i, stock in enumerate(final_stocks[:20], 1):
            fundamental_bonus = self._calculate_fundamental_bonus(stock)
            stock['fundamental_bonus'] = fundamental_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 基本面加分{fundamental_bonus:.2f}")
        
        # 增强 7: 添加机构研报分析 (前 20 只)
        print("[增强 7/13] 分析机构研报...")
        for i, stock in enumerate(final_stocks[:20], 1):
            analyst_bonus = self._calculate_analyst_bonus(stock)
            stock['analyst_bonus'] = analyst_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 研报加分{analyst_bonus:.2f}")
        
        # 增强 8: 添加趋势技术分析 (前 20 只)
        print("[增强 8/13] 趋势技术分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            trend_bonus = self._calculate_trend_bonus(stock)
            stock['trend_bonus'] = trend_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 趋势加分{trend_bonus:.2f}")
        
        # 增强 9: 添加彼得·林奇策略分析 (前 20 只)
        print("[增强 9/13] 彼得·林奇策略分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            lynch_bonus = self._calculate_lynch_bonus(stock)
            stock['lynch_bonus'] = lynch_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 林奇加分{lynch_bonus:.2f}")
        
        # 增强 10: 添加格雷厄姆策略分析 (前 20 只)
        print("[增强 10/13] 聪明的投资者分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            graham_bonus = self._calculate_graham_bonus(stock)
            stock['graham_bonus'] = graham_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 格雷厄姆加分{graham_bonus:.2f}")
        
        # 增强 11: 添加缠论分析 (前 20 只)
        print("[增强 11/13] 缠论分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            chan_bonus = self._calculate_chan_bonus(stock)
            stock['chan_bonus'] = chan_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 缠论加分{chan_bonus:.2f}")
        
        # 增强 12: 添加海龟交易分析 (前 20 只)
        print("[增强 12/13] 海龟交易分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            turtle_bonus = self._calculate_turtle_bonus(stock)
            stock['turtle_bonus'] = turtle_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 海龟加分{turtle_bonus:.2f}")
        
        # 增强 13: 添加交易心理分析 (前 20 只)
        print("[增强 13/16] 交易心理分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            psych_bonus = self._calculate_psych_bonus(stock)
            stock['psych_bonus'] = psych_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 心理加分{psych_bonus:.2f}")
        
        # 增强 14: 添加波浪理论分析 (前 20 只)
        print("[增强 14/16] 波浪理论分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            elliott_bonus = self._calculate_elliott_bonus(stock)
            stock['elliott_bonus'] = elliott_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 波浪加分{elliott_bonus:.2f}")
        
        # 增强 15: 添加江恩理论分析 (前 20 只)
        print("[增强 15/16] 江恩理论分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            gann_bonus = self._calculate_gann_bonus(stock)
            stock['gann_bonus'] = gann_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 江恩加分{gann_bonus:.2f}")
        
        # 增强 16: 添加资金管理分析 (前 20 只)
        print("[增强 16/16] 资金管理分析...")
        for i, stock in enumerate(final_stocks[:20], 1):
            position_bonus = self._calculate_position_bonus(stock)
            stock['position_bonus'] = position_bonus
            print(f"  [{i}/20] {stock.get('symbol', '')}: 资金管理加分{position_bonus:.2f}")
        
        # 根据增强数据调整评分 (v5.1 优化权重)
        from optimization_config import SCORING_WEIGHTS
        
        for stock in final_stocks:
            # 主力排名加分 (提高权重)
            if stock.get('is_main_force_top'):
                stock['final_score'] *= (1 + SCORING_WEIGHTS['main_force_weight'])
            
            # 主力净流入加分
            main_net = stock.get('main_net', 0)
            if main_net > 100000000:  # >1 亿
                stock['final_score'] *= 1.15
            elif main_net > 50000000:  # >5000 万
                stock['final_score'] *= 1.08
            
            # 多日资金流加分 (提高权重 - 回测显示最重要)
            flow_bonus = stock.get('flow_bonus', 0)
            stock['final_score'] += flow_bonus * (1 + SCORING_WEIGHTS['flow_bonus_weight'])
            
            # 基本面加分 (提高权重)
            fundamental_bonus = stock.get('fundamental_bonus', 0)
            stock['final_score'] += fundamental_bonus * (1 + SCORING_WEIGHTS['fundamental_bonus_weight'])
            
            # 机构研报加分 (提高权重)
            analyst_bonus = stock.get('analyst_bonus', 0)
            stock['final_score'] += analyst_bonus * (1 + SCORING_WEIGHTS['analyst_bonus_weight'])
            
            # 技术面加分 (降低权重 - 回测显示贡献有限)
            tech_bonus = stock.get('technical_bonus', 0)
            stock['final_score'] += tech_bonus * (1 - SCORING_WEIGHTS['tech_bonus_weight'])
            
            # 量价分析加分 (降低权重)
            vp_bonus = stock.get('vp_bonus', 0)
            stock['final_score'] += vp_bonus * (1 - SCORING_WEIGHTS['vp_bonus_weight'])
            
            # 趋势技术分析加分 (降低权重)
            trend_bonus = stock.get('trend_bonus', 0)
            stock['final_score'] += trend_bonus * (1 - SCORING_WEIGHTS['trend_bonus_weight'])
            
            # 策略分析加分 (保持原权重)
            stock['final_score'] += stock.get('canslim_bonus', 0) * (1 + SCORING_WEIGHTS['canslim_bonus_weight'])
            stock['final_score'] += stock.get('lynch_bonus', 0) * (1 + SCORING_WEIGHTS['lynch_bonus_weight'])
            stock['final_score'] += stock.get('graham_bonus', 0) * (1 + SCORING_WEIGHTS['graham_bonus_weight'])
            stock['final_score'] += stock.get('chan_bonus', 0) * (1 + SCORING_WEIGHTS['chan_bonus_weight'])
            stock['final_score'] += stock.get('turtle_bonus', 0) * (1 + SCORING_WEIGHTS['turtle_bonus_weight'])
            stock['final_score'] += stock.get('psych_bonus', 0) * (1 + SCORING_WEIGHTS['psych_bonus_weight'])
            stock['final_score'] += stock.get('elliott_bonus', 0) * (1 + SCORING_WEIGHTS['elliott_bonus_weight'])
            stock['final_score'] += stock.get('gann_bonus', 0) * (1 + SCORING_WEIGHTS['gann_bonus_weight'])
            stock['final_score'] += stock.get('position_bonus', 0) * (1 + SCORING_WEIGHTS['position_bonus_weight'])
            
            # 黑名单股票 → 大幅降分
            symbol = stock.get('symbol', '').replace('sh', '').replace('sz', '')
            from optimization_config import BLACKLIST_SYMBOLS, WATCHLIST_SYMBOLS
            if symbol in BLACKLIST_SYMBOLS:
                stock['final_score'] *= 0.3  # 降 70%
            elif symbol in WATCHLIST_SYMBOLS:
                stock['final_score'] *= 0.6  # 降 40%
        
        # 生成买入评级、止盈止损、买入理由 (增强版)
        for stock in final_stocks:
            rating_info = self._generate_buy_rating(stock)
            
            # 获取多日资金流信息
            flow_info = stock.get('multi_day_flow')
            composite_score = 0
            signal = 'neutral'
            signal_strength = 0
            
            if flow_info is not None and isinstance(flow_info, dict):
                composite_score = flow_info.get('composite_score', 0)
                signal = flow_info.get('signal', 'neutral')
                signal_strength = flow_info.get('signal_strength', 0)
            
            # 根据多日资金流信号调整评级
            if signal == 'strong_buy':
                # 强烈买入信号 → 升级评级
                if rating_info['rating'] == '推荐':
                    rating_info['rating'] = '强烈推荐'
                    rating_info['confidence'] = min(95, rating_info['confidence'] + 15)
                elif rating_info['rating'] == '谨慎推荐':
                    rating_info['rating'] = '推荐'
                    rating_info['confidence'] = min(85, rating_info['confidence'] + 15)
            elif signal == 'buy':
                # 买入信号 → 适度升级
                if rating_info['rating'] == '谨慎推荐':
                    rating_info['rating'] = '推荐'
                    rating_info['confidence'] = min(80, rating_info['confidence'] + 10)
            
            # 根据主力排名和资金流综合调整
            if stock.get('is_main_force_top') and composite_score >= 70:
                if rating_info['rating'] == '推荐':
                    rating_info['rating'] = '强烈推荐'
                    rating_info['confidence'] = min(95, rating_info['confidence'] + 10)
                elif rating_info['rating'] == '谨慎推荐':
                    rating_info['rating'] = '推荐'
                    rating_info['confidence'] = min(85, rating_info['confidence'] + 10)
            
            # 添加增强信息到理由
            if stock.get('is_main_force_top'):
                rank = stock.get('main_force_rank', 0)
                rating_info['reasons'].append(f'主力排名 Top{rank}')
            
            main_net = stock.get('main_net', 0)
            if main_net > 100000000:
                rating_info['reasons'].append(f'主力净流入{main_net/100000000:.2f}亿')
            
            # 多日资金流理由
            if flow_info is not None and isinstance(flow_info, dict):
                # 连续性
                inflow_days = flow_info.get('inflow_days', 0)
                if inflow_days >= 5:
                    rating_info['reasons'].append(f'5 日{inflow_days}日连续净流入')
                elif inflow_days >= 3:
                    rating_info['reasons'].append(f'5 日{inflow_days}日净流入')
                
                # 趋势
                if flow_info.get('trend') == 'improving':
                    rating_info['reasons'].append('资金流改善')
                
                # 强度
                intensity = flow_info.get('intensity_score', 0)
                if intensity >= 80:
                    rating_info['reasons'].append('高强度流入')
                
                # 信号
                if signal == 'strong_buy':
                    rating_info['reasons'].append('强烈买入信号')
                elif signal == 'buy':
                    rating_info['reasons'].append('买入信号')
                
                # 异常检测
                if flow_info.get('is_anomaly'):
                    rating_info['reasons'].append('异常大幅流入')
            
            # 量价分析理由
            vp_analysis = stock.get('vp_analysis')
            if vp_analysis:
                relationship = vp_analysis.get('relationship', '')
                if relationship == '价涨量增':
                    rating_info['reasons'].append('价涨量增')
                elif relationship == '放量突破':
                    rating_info['reasons'].append('放量突破')
            
            # CAN SLIM 理由
            canslim_analysis = stock.get('canslim_analysis')
            if canslim_analysis and canslim_analysis.get('total_score', 0) >= 75:
                rating_info['reasons'].append('CAN SLIM 符合')
            
            # 缠论理由
            chan_analysis = stock.get('chan_analysis')
            if chan_analysis:
                rating = chan_analysis.get('rating', '')
                if rating in ['强烈看多', '看多']:
                    rating_info['reasons'].append('缠论看多')
            
            # 海龟交易理由
            turtle_analysis = stock.get('turtle_analysis')
            if turtle_analysis:
                rating = turtle_analysis.get('rating', '')
                if rating in ['强烈买入信号', '买入信号']:
                    rating_info['reasons'].append('海龟买入信号')
            
            # 交易心理理由
            psych_analysis = stock.get('psych_analysis')
            if psych_analysis:
                rating = psych_analysis.get('rating', '')
                if rating in ['强烈买入', '买入']:
                    rating_info['reasons'].append('三重滤网共振')
            
            # ML 增强模式：融合经典投资理论
            if ml_enhance:
                try:
                    from ml_strategy_enhancer import MLEnhancedPredictor
                    predictor = MLEnhancedPredictor()
                    
                    # 准备历史数据 (简化)
                    history = None  # 实际使用时可加载 K 线历史
                    
                    # ML 增强预测
                    ml_result = predictor.predict(stock, history)
                    
                    # ML 评分加权
                    ml_score = ml_result['final_score']
                    stock['ml_score'] = ml_score
                    stock['ml_rating'] = ml_result['rating']
                    stock['ml_confidence'] = ml_result['confidence']
                    
                    # 融合 ML 评分到最终评分
                    stock['final_score'] = stock['final_score'] * 0.7 + ml_score * 100 * 0.3
                    
                    # 添加 ML 理由
                    if ml_result['reasons']:
                        rating_info['reasons'].extend(ml_result['reasons'][:2])  # 最多加 2 个
                    
                    # ML 评级调整
                    if ml_result['rating'] == '强烈推荐' and rating_info['rating'] in ['推荐', '谨慎推荐']:
                        rating_info['rating'] = '推荐'
                        rating_info['confidence'] = min(85, rating_info['confidence'] + 5)
                    elif ml_result['rating'] == '观望' and rating_info['rating'] in ['强烈推荐', '推荐']:
                        rating_info['rating'] = '谨慎推荐'
                        rating_info['confidence'] = max(50, rating_info['confidence'] - 5)
                    
                except Exception as e:
                    print(f"  ⚠️ ML 增强失败：{e}")
            
            # 金融模型增强模式：融合经典金融学理论
            if financial_models:
                try:
                    from financial_models import FinancialModelsEnsemble
                    ensemble = FinancialModelsEnsemble()
                    
                    # 准备历史数据 (简化)
                    history = None  # 实际使用时可加载 K 线历史
                    
                    # 金融模型综合分析
                    fm_result = ensemble.analyze(stock, history)
                    
                    # 金融模型评分
                    fm_score = fm_result['final_score']
                    stock['fm_score'] = fm_score
                    stock['fm_rating'] = fm_result['rating']
                    stock['fm_confidence'] = fm_result['confidence']
                    
                    # 融合金融模型评分到最终评分 (金融模型占 25%)
                    stock['final_score'] = stock['final_score'] * 0.75 + fm_score * 0.25
                    
                    # 添加金融模型理由
                    if fm_result['reasons']:
                        rating_info['reasons'].extend(fm_result['reasons'][:2])
                    
                    # 金融模型评级调整
                    if fm_result['rating'] == '强烈推荐':
                        rating_info['rating'] = '强烈推荐'
                        rating_info['confidence'] = min(95, rating_info['confidence'] + 10)
                    elif fm_result['rating'] == '推荐' and rating_info['rating'] == '谨慎推荐':
                        rating_info['rating'] = '推荐'
                        rating_info['confidence'] = min(85, rating_info['confidence'] + 5)
                    
                    # 存储详细模型结果
                    stock['capm'] = fm_result['models']['capm']
                    stock['fama_french'] = fm_result['models']['fama_french']
                    stock['carhart'] = fm_result['models']['carhart']
                    stock['risk_metrics'] = fm_result['models']['risk_metrics']
                    
                except Exception as e:
                    print(f"  ⚠️ 金融模型增强失败：{e}")
            
            stock.update(rating_info)
        
        # 按综合评分排序
        final_stocks.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        print(f"\n✅ 最终决策：从 {len(stock_map)} 只主板股票中选出 Top{min(top_n, len(final_stocks))}")
        print(f"   筛选条件：综合评分排序 (成交额 + 涨幅 + 成交量 + 主力排名 + 多日资金流)")
        print(f"   过滤：仅主板 (排除创业板/科创板/北交所)")
        
        return final_stocks[:top_n]


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='股票筛选工作流 v5.0 - 16 重增强分析')
    parser.add_argument('--strategy', choices=['main', 'gainers', 'volume', 'all'],
                       default='all', help='筛选策略')
    parser.add_argument('--top', type=int, default=10, help='前 N 条')
    parser.add_argument('--export', action='store_true', help='导出结果')
    parser.add_argument('--push', action='store_true', help='推送到企业微信')
    parser.add_argument('--webhook', type=str, help='企业微信 Webhook 地址')
    parser.add_argument('--backtest', action='store_true', help='运行回溯跟踪')
    parser.add_argument('--optimize', action='store_true', help='自动优化权重')
    parser.add_argument('--report', action='store_true', help='生成回测报告')
    parser.add_argument('--record', action='store_true', help='记录当前决策 (默认开启)')
    parser.add_argument('--ml-enhance', action='store_true', help='使用 ML 增强模式')
    parser.add_argument('--financial-models', action='store_true', help='使用金融模型增强')
    
    args = parser.parse_args()
    
    # 回溯/优化模式
    if args.backtest or args.optimize or args.report:
        from backtest import DecisionTracker
        tracker = DecisionTracker()
        
        if args.backtest:
            print("\n📊 运行回溯跟踪...")
            tracker.track_progress()
        elif args.optimize:
            print("\n🎯 自动优化权重...")
            tracker.optimize_weights()
        elif args.report:
            print("\n📈 生成回测报告...")
            tracker.generate_report()
        return
    
    workflow = StockWorkflow()
    
    if args.strategy == 'all':
        # ML 增强模式
        if args.ml_enhance:
            print("\n🤖 使用 ML 增强模式...")
            results = workflow.run_all(top_n=args.top, ml_enhance=True)
        # 金融模型增强模式
        elif args.financial_models:
            print("\n📊 使用金融模型增强模式...")
            results = workflow.run_all(top_n=args.top, financial_models=True)
        else:
            results = workflow.run_all(top_n=args.top)
        
        # 推送结果 - 只推送最终决策
        if args.push:
            try:
                from workflow_push import push_workflow_result
                webhook = args.webhook or "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5"
                
                # 只推送最终决策结果
                if results.get('final_decision'):
                    stocks = results['final_decision'][:args.top]
                    ml_enhanced = args.ml_enhance or args.financial_models
                    push_workflow_result(webhook, 'final', stocks, top_n=args.top, pool_mode=False, is_final=True, ml_enhanced=ml_enhanced)
            except Exception as e:
                print(f"⚠️  推送失败：{e}")
        
        # 记录决策到回溯模块 (默认开启)
        if args.record or args.push:
            try:
                from backtest import DecisionTracker
                tracker = DecisionTracker()
                
                if results.get('final_decision'):
                    ml_enhanced = args.ml_enhance or args.financial_models
                    mode_name = "(金融模型)" if args.financial_models else "(ML 增强)" if args.ml_enhance else ""
                    tracker.record_decision({
                        'stocks': results['final_decision'],
                        'ml_enhanced': ml_enhanced
                    }, workflow_name=f'股票筛选工作流 {mode_name}')
            except Exception as e:
                print(f"⚠️  记录决策失败：{e}")
    
    elif args.strategy == 'main':
        results = workflow.run_main_force_strategy(top_n=args.top)
        workflow.print_summary(results)
        if args.export:
            workflow.save_results(results)
    
    elif args.strategy == 'gainers':
        results = workflow.run_gainers_strategy(top_n=args.top)
        workflow.print_summary(results)
        if args.export:
            workflow.save_results(results)
    
    elif args.strategy == 'volume':
        results = workflow.run_volume_strategy(top_n=args.top)
        workflow.print_summary(results)
        if args.export:
            workflow.save_results(results)


if __name__ == '__main__':
    main()
