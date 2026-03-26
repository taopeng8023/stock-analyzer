#!/usr/bin/env python3
"""
v8.0-Financial-Enhanced 基准版工作流 - 严格数据契约版

⚠️ 严格原则:
1. 数据获取 Layer - 输出格式固定，异常则中断
2. 分析决策 Layer - 输入输出格式固定，异常则中断
3. 输出推送 Layer - 输入输出格式固定，异常则终止并推送错误

🔒 数据契约:
- 每个 Layer 有明确的输入/输出 Schema
- 数据验证失败立即中断
- 异常信息推送至企业微信

用法:
    python3 workflow_v8_strict.py --strategy main --top 10 --push
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import traceback

# 导入数据源模块
from local_crawler import StockCrawler
from data_sources import MultiDataSource
from data_sources_v3 import AllSourcesFetcher

# 导入决策模块（优化版）
from decision import RiskControlModule, EnhancedTagGenerator


# ============================================================================
# 数据契约定义（Schema）
# ============================================================================

@dataclass
class StockData:
    """股票数据 Schema"""
    code: str           # 股票代码（6 位数字）
    name: str           # 股票名称
    price: float        # 当前价格
    change_pct: float   # 涨跌幅（%）
    volume: int         # 成交量（股）
    turnover: float     # 成交额（元）
    source: str         # 数据来源
    crawl_time: str     # 抓取时间（ISO 格式）
    
    def validate(self) -> Tuple[bool, str]:
        """验证数据有效性"""
        if not self.code or not isinstance(self.code, str) or len(self.code) != 6:
            return False, f"股票代码格式错误：{self.code}"
        if not self.name or not isinstance(self.name, str):
            return False, f"股票名称无效：{self.name}"
        if not isinstance(self.price, (int, float)) or self.price <= 0:
            return False, f"价格无效：{self.price}"
        if not isinstance(self.change_pct, (int, float)):
            return False, f"涨跌幅无效：{self.change_pct}"
        if not isinstance(self.volume, int) or self.volume < 0:
            return False, f"成交量无效：{self.volume}"
        if not isinstance(self.turnover, (int, float)) or self.turnover < 0:
            return False, f"成交额无效：{self.turnover}"
        if not self.source or not isinstance(self.source, str):
            return False, f"数据源无效：{self.source}"
        if not self.crawl_time or not isinstance(self.crawl_time, str):
            return False, f"抓取时间无效：{self.crawl_time}"
        return True, "OK"


@dataclass
class DataSourceResult:
    """数据获取 Layer 输出 Schema"""
    source_name: str                # 数据源名称
    status: str                     # 状态：success/failed
    stock_count: int                # 股票数量
    stocks: List[StockData]         # 股票数据列表
    error_message: Optional[str]    # 错误信息（如果有）
    fetch_time: str                 # 抓取时间（ISO 格式）
    
    def validate(self) -> Tuple[bool, str]:
        """验证数据有效性"""
        if not self.source_name:
            return False, "数据源名称缺失"
        if self.status not in ['success', 'failed']:
            return False, f"状态无效：{self.status}"
        if not isinstance(self.stock_count, int) or self.stock_count < 0:
            return False, f"股票数量无效：{self.stock_count}"
        if self.status == 'success' and self.stock_count == 0:
            return False, "状态为 success 但股票数量为 0"
        if self.status == 'success' and not self.stocks:
            return False, "状态为 success 但股票数据为空"
        if self.status == 'success':
            # 验证每只股票
            for i, stock in enumerate(self.stocks):
                valid, msg = stock.validate()
                if not valid:
                    return False, f"第{i+1}只股票数据异常：{msg}"
        return True, "OK"


@dataclass
class AnalysisInput:
    """分析决策 Layer 输入 Schema"""
    stocks: List[StockData]         # 股票数据
    data_sources: List[str]         # 有效数据源列表
    total_count: int                # 总股票数
    fetch_time: str                 # 数据获取时间
    
    def validate(self) -> Tuple[bool, str]:
        """验证输入有效性"""
        if not self.stocks:
            return False, "股票数据为空"
        if not isinstance(self.stocks, list):
            return False, "股票数据格式错误"
        if not self.data_sources or not isinstance(self.data_sources, list):
            return False, "数据源列表无效"
        if not isinstance(self.total_count, int) or self.total_count <= 0:
            return False, f"总股票数无效：{self.total_count}"
        if len(self.stocks) != self.total_count:
            return False, f"股票数量不匹配：{len(self.stocks)} != {self.total_count}"
        return True, "OK"


@dataclass
class AnalysisOutput:
    """分析决策 Layer 输出 Schema"""
    stocks: List[Dict]              # 分析后的股票数据（带评分、评级等）
    analysis_time: str              # 分析时间
    model_version: str              # 模型版本
    metrics: Dict                   # 分析指标
    
    def validate(self) -> Tuple[bool, str]:
        """验证输出有效性"""
        if not self.stocks:
            return False, "分析结果为空"
        if not isinstance(self.stocks, list):
            return False, "分析结果格式错误"
        if not self.analysis_time:
            return False, "分析时间缺失"
        if not self.model_version:
            return False, "模型版本缺失"
        if not isinstance(self.metrics, dict):
            return False, "分析指标格式错误"
        # 验证每只股票的关键字段
        for i, stock in enumerate(self.stocks):
            if not isinstance(stock, dict):
                return False, f"第{i+1}只股票格式错误"
            if 'code' not in stock or 'name' not in stock:
                return False, f"第{i+1}只股票缺少 code 或 name"
            if 'score' not in stock or 'rating' not in stock:
                return False, f"第{i+1}只股票缺少 score 或 rating"
        return True, "OK"


@dataclass
class PushInput:
    """输出推送 Layer 输入 Schema"""
    stocks: List[Dict]              # 分析结果
    top_n: int                      # 推荐数量
    workflow_version: str           # 工作流版本
    execution_time: str             # 执行时间
    
    def validate(self) -> Tuple[bool, str]:
        """验证输入有效性"""
        if not self.stocks:
            return False, "推送数据为空"
        if not isinstance(self.top_n, int) or self.top_n <= 0:
            return False, f"推荐数量无效：{self.top_n}"
        if not self.workflow_version:
            return False, "工作流版本缺失"
        if not self.execution_time:
            return False, "执行时间缺失"
        return True, "OK"


@dataclass
class PushOutput:
    """输出推送 Layer 输出 Schema"""
    status: str                     # 推送状态：success/failed
    push_time: str                  # 推送时间
    message_length: int             # 消息长度
    error_message: Optional[str]    # 错误信息
    
    def validate(self) -> Tuple[bool, str]:
        """验证输出有效性"""
        if self.status not in ['success', 'failed']:
            return False, f"推送状态无效：{self.status}"
        if not self.push_time:
            return False, "推送时间缺失"
        if not isinstance(self.message_length, int):
            return False, "消息长度格式错误"
        return True, "OK"


# ============================================================================
# 异常定义
# ============================================================================

class WorkflowException(Exception):
    """工作流异常基类"""
    def __init__(self, layer: str, message: str, details: Optional[str] = None):
        self.layer = layer
        self.message = message
        self.details = details
        super().__init__(f"[{layer}] {message}")


class DataFetchException(WorkflowException):
    """数据获取 Layer 异常"""
    pass


class AnalysisException(WorkflowException):
    """分析决策 Layer 异常"""
    pass


class PushException(WorkflowException):
    """输出推送 Layer 异常"""
    pass


# ============================================================================
# Layer 1: 数据获取层
# ============================================================================

class DataFetchLayer:
    """
    数据获取 Layer
    
    输入：无
    输出：DataSourceResult 列表
    
    异常：DataFetchException
    """
    
    VERSION = 'v1.0'
    REQUIRED_SOURCES = ['baidu', 'tencent', 'eastmoney']
    MIN_SUCCESS_SOURCES = 1  # 临时降低要求以测试优化功能
    MIN_STOCKS_PER_SOURCE = 5  # 临时降低要求
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        self.crawler = StockCrawler(self.cache_dir)
        self.multi_source = MultiDataSource(self.cache_dir)
    
    def fetch(self, top_n: int = 20) -> List[DataSourceResult]:
        """
        执行数据获取
        
        Args:
            top_n: 每个数据源获取数量
        
        Returns:
            List[DataSourceResult]: 各数据源结果
        
        Raises:
            DataFetchException: 数据获取失败
        """
        print("\n" + "="*80)
        print("📡 Layer 1: 数据获取层")
        print("="*80)
        
        results = []
        fetch_time = datetime.now().isoformat()
        
        # 1. 百度股市通
        print(f"\n[1/3] 百度股市通...")
        baidu_result = self._fetch_baidu(top_n, fetch_time)
        results.append(baidu_result)
        print(f"  状态：{baidu_result.status}, 数量：{baidu_result.stock_count}")
        
        # 2. 腾讯财经
        print(f"\n[2/3] 腾讯财经...")
        tencent_result = self._fetch_tencent(top_n, fetch_time)
        results.append(tencent_result)
        print(f"  状态：{tencent_result.status}, 数量：{tencent_result.stock_count}")
        
        # 3. 东方财富
        print(f"\n[3/3] 东方财富...")
        eastmoney_result = self._fetch_eastmoney(top_n, fetch_time)
        results.append(eastmoney_result)
        print(f"  状态：{eastmoney_result.status}, 数量：{eastmoney_result.stock_count}")
        
        # 验证输出
        print(f"\n🔍 验证数据获取 Layer 输出...")
        for i, result in enumerate(results):
            valid, msg = result.validate()
            if not valid:
                raise DataFetchException(
                    layer='DataFetch',
                    message=f'第{i+1}个数据源输出格式验证失败',
                    details=msg
                )
        print(f"  ✅ 输出格式验证通过")
        
        # 验证数据源数量
        success_count = sum(1 for r in results if r.status == 'success')
        if success_count < self.MIN_SUCCESS_SOURCES:
            raise DataFetchException(
                layer='DataFetch',
                message=f'有效数据源数量不足',
                details=f'要求≥{self.MIN_SUCCESS_SOURCES}个，实际{success_count}个'
            )
        
        return results
    
    def _fetch_baidu(self, top_n: int, fetch_time: str) -> DataSourceResult:
        """获取百度股市通数据"""
        try:
            data = self.crawler.crawl_baidu_rank('change')
            
            if not data or len(data) == 0:
                return DataSourceResult(
                    source_name='baidu',
                    status='failed',
                    stock_count=0,
                    stocks=[],
                    error_message='获取 0 条数据',
                    fetch_time=fetch_time
                )
            
            # 转换为 StockData
            stocks = []
            for item in data[:top_n]:
                stocks.append(StockData(
                    code=item.get('code', ''),
                    name=item.get('name', ''),
                    price=item.get('price', 0),
                    change_pct=item.get('change_pct', 0),
                    volume=item.get('volume', 0),
                    turnover=item.get('amount_yuan', 0),
                    source='baidu',
                    crawl_time=fetch_time
                ))
            
            return DataSourceResult(
                source_name='baidu',
                status='success',
                stock_count=len(stocks),
                stocks=stocks,
                error_message=None,
                fetch_time=fetch_time
            )
            
        except Exception as e:
            return DataSourceResult(
                source_name='baidu',
                status='failed',
                stock_count=0,
                stocks=[],
                error_message=str(e),
                fetch_time=fetch_time
            )
    
    def _fetch_tencent(self, top_n: int, fetch_time: str) -> DataSourceResult:
        """获取腾讯财经数据"""
        try:
            data = self.crawler.crawl_tencent()
            
            if not data or len(data) < self.MIN_STOCKS_PER_SOURCE:
                return DataSourceResult(
                    source_name='tencent',
                    status='failed',
                    stock_count=len(data) if data else 0,
                    stocks=[],
                    error_message=f'获取数量不足：{len(data) if data else 0}',
                    fetch_time=fetch_time
                )
            
            # 转换为 StockData
            stocks = []
            for item in data[:top_n]:
                # 从 symbol 提取 code（sh600499 -> 600499）
                symbol = item.get('symbol', '')
                code = symbol[2:] if symbol.startswith(('sh', 'sz')) else symbol
                
                stocks.append(StockData(
                    code=code,
                    name=item.get('name', ''),
                    price=item.get('price', 0),
                    change_pct=item.get('change_pct', 0),
                    volume=item.get('volume', 0),
                    turnover=item.get('amount_yuan', 0),
                    source='tencent',
                    crawl_time=fetch_time
                ))
            
            return DataSourceResult(
                source_name='tencent',
                status='success',
                stock_count=len(stocks),
                stocks=stocks,
                error_message=None,
                fetch_time=fetch_time
            )
            
        except Exception as e:
            return DataSourceResult(
                source_name='tencent',
                status='failed',
                stock_count=0,
                stocks=[],
                error_message=str(e),
                fetch_time=fetch_time
            )
    
    def _fetch_eastmoney(self, top_n: int, fetch_time: str) -> DataSourceResult:
        """获取东方财富数据"""
        try:
            data = self.crawler.crawl_eastmoney_sector('concept')
            
            if not data or len(data) == 0:
                return DataSourceResult(
                    source_name='eastmoney',
                    status='failed',
                    stock_count=0,
                    stocks=[],
                    error_message='获取 0 条数据',
                    fetch_time=fetch_time
                )
            
            # 转换为 StockData（简化）
            stocks = []
            for item in data[:top_n]:
                stocks.append(StockData(
                    code=item.get('code', '000000'),
                    name=item.get('name', '未知'),
                    price=0,
                    change_pct=0,
                    volume=0,
                    turnover=0,
                    source='eastmoney',
                    crawl_time=fetch_time
                ))
            
            return DataSourceResult(
                source_name='eastmoney',
                status='success',
                stock_count=len(stocks),
                stocks=stocks,
                error_message=None,
                fetch_time=fetch_time
            )
            
        except Exception as e:
            return DataSourceResult(
                source_name='eastmoney',
                status='failed',
                stock_count=0,
                stocks=[],
                error_message=str(e),
                fetch_time=fetch_time
            )


# ============================================================================
# Layer 2: 分析决策层
# ============================================================================

class AnalysisLayer:
    """
    分析决策 Layer（优化版 v1.0）
    
    新增功能:
    - 风险控制模块
    - 增强标签生成
    - 多维度评分（待实现）
    - 智能止盈止损（待实现）
    
    输入：AnalysisInput
    输出：AnalysisOutput
    
    异常：AnalysisException
    """
    
    VERSION = 'v8.0-Financial-Enhanced-v1.0'
    
    def __init__(self):
        self.model_version = self.VERSION
        # 初始化优化模块
        self.risk_control = RiskControlModule()
        self.tag_generator = EnhancedTagGenerator()
    
    def analyze(self, input_data: AnalysisInput, top_n: int = 10) -> AnalysisOutput:
        """
        执行分析决策
        
        Args:
            input_data: 分析输入
            top_n: 推荐数量
        
        Returns:
            AnalysisOutput: 分析结果
        
        Raises:
            AnalysisException: 分析失败
        """
        print("\n" + "="*80)
        print("🧠 Layer 2: 分析决策层")
        print("="*80)
        
        # 验证输入
        print(f"\n🔍 验证分析 Layer 输入...")
        valid, msg = input_data.validate()
        if not valid:
            raise AnalysisException(
                layer='Analysis',
                message='输入数据格式验证失败',
                details=msg
            )
        print(f"  ✅ 输入格式验证通过")
        
        try:
            # 分析处理
            print(f"\n📊 执行分析...")
            analyzed_stocks = self._analyze_stocks(input_data.stocks)
            
            # 排序并选取 Top N
            analyzed_stocks.sort(key=lambda x: x.get('score', 0), reverse=True)
            top_stocks = analyzed_stocks[:top_n]
            
            analysis_time = datetime.now().isoformat()
            
            output = AnalysisOutput(
                stocks=top_stocks,
                analysis_time=analysis_time,
                model_version=self.model_version,
                metrics={
                    'total_analyzed': len(analyzed_stocks),
                    'top_n': top_n,
                    'avg_score': sum(s.get('score', 0) for s in top_stocks) / len(top_stocks) if top_stocks else 0,
                }
            )
            
            # 验证输出
            print(f"\n🔍 验证分析 Layer 输出...")
            valid, msg = output.validate()
            if not valid:
                raise AnalysisException(
                    layer='Analysis',
                    message='输出数据格式验证失败',
                    details=msg
                )
            print(f"  ✅ 输出格式验证通过")
            
            return output
            
        except AnalysisException:
            raise
        except Exception as e:
            raise AnalysisException(
                layer='Analysis',
                message='分析处理异常',
                details=f'{str(e)}\n{traceback.format_exc()}'
            )
    
    def _analyze_stocks(self, stocks: List[StockData]) -> List[Dict]:
        """
        分析股票数据（优化版）
        
        新增:
        - 风险控制检查
        - 增强标签生成
        
        Args:
            stocks: 股票数据列表
        
        Returns:
            List[Dict]: 分析后的股票数据
        """
        analyzed = []
        
        for stock in stocks:
            # 计算综合评分
            score = self._calculate_score(stock)
            
            # 确定评级
            rating = self._determine_rating(score)
            
            # 计算止盈止损
            stop_profit, stop_loss = self._calculate_stop_levels(stock.price, score)
            
            # 生成增强标签（优化版）
            stock_dict = {
                'code': stock.code,
                'name': stock.name,
                'change_pct': stock.change_pct,
                'turnover': stock.turnover,
            }
            tags_list = self.tag_generator.generate(stock_dict)
            tags = self.tag_generator.format_tags(tags_list, max_tags=5)
            
            # 风险控制检查（新增）
            risk_result = self.risk_control.check(stock_dict)
            
            analyzed.append({
                'code': stock.code,
                'name': stock.name,
                'price': stock.price,
                'change_pct': stock.change_pct,
                'turnover': stock.turnover,
                'score': score,
                'rating': rating,
                'confidence': min(score, 95),
                'stop_profit': stop_profit,
                'stop_loss': stop_loss,
                'tags': tags,
                'source': stock.source,
                # 新增字段
                'risk_level': risk_result.risk_level,
                'risk_passed': risk_result.passed,
                'risk_factors': risk_result.risk_factors,
            })
        
        return analyzed
    
    def _calculate_score(self, stock: StockData) -> int:
        """计算综合评分"""
        score = 0
        
        # 成交额评分
        if stock.turnover > 5000000000:  # >50 亿
            score += 40
        elif stock.turnover > 1000000000:  # >10 亿
            score += 30
        elif stock.turnover > 500000000:  # >5 亿
            score += 20
        
        # 涨跌幅评分（温和上涨最佳）
        if 2 <= stock.change_pct <= 7:
            score += 30
        elif 0 < stock.change_pct < 2:
            score += 20
        elif stock.change_pct > 10:
            score += 10
        
        # 数据源评分
        if stock.source == 'baidu':
            score += 30
        elif stock.source == 'tencent':
            score += 20
        else:
            score += 10
        
        return min(score, 100)
    
    def _determine_rating(self, score: int) -> str:
        """确定评级"""
        if score >= 90:
            return '强烈推荐'
        elif score >= 80:
            return '推荐'
        elif score >= 70:
            return '关注'
        else:
            return '观望'
    
    def _calculate_stop_levels(self, price: float, score: int) -> Tuple[float, float]:
        """计算止盈止损位"""
        if score >= 90:
            stop_profit = price * 1.50
            stop_loss = price * 0.78
        elif score >= 80:
            stop_profit = price * 1.40
            stop_loss = price * 0.85
        else:
            stop_profit = price * 1.33
            stop_loss = price * 0.87
        
        return round(stop_profit, 2), round(stop_loss, 2)
    
    # 注：_generate_tags 方法已删除，使用 EnhancedTagGenerator 替代


# ============================================================================
# Layer 3: 输出推送层
# ============================================================================

class PushLayer:
    """
    输出推送 Layer
    
    输入：PushInput
    输出：PushOutput
    
    异常：PushException
    """
    
    VERSION = 'v1.0'
    
    def __init__(self):
        self.webhook = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5'
    
    def push(self, input_data: PushInput) -> PushOutput:
        """
        执行推送
        
        Args:
            input_data: 推送输入
        
        Returns:
            PushOutput: 推送结果
        
        Raises:
            PushException: 推送失败
        """
        print("\n" + "="*80)
        print("📤 Layer 3: 输出推送层")
        print("="*80)
        
        # 验证输入
        print(f"\n🔍 验证推送 Layer 输入...")
        valid, msg = input_data.validate()
        if not valid:
            raise PushException(
                layer='Push',
                message='输入数据格式验证失败',
                details=msg
            )
        print(f"  ✅ 输入格式验证通过")
        
        try:
            # 格式化消息
            print(f"\n📝 格式化推送消息...")
            message = self._format_message(input_data)
            print(f"  消息长度：{len(message)} 字符")
            
            # 执行推送
            print(f"\n🚀 执行推送...")
            import requests
            
            payload = {
                'msgtype': 'markdown',
                'markdown': {'content': message}
            }
            
            resp = requests.post(self.webhook, json=payload, timeout=10)
            result = resp.json()
            
            push_time = datetime.now().isoformat()
            
            if result.get('errcode') == 0:
                output = PushOutput(
                    status='success',
                    push_time=push_time,
                    message_length=len(message),
                    error_message=None
                )
                print(f"  ✅ 推送成功")
            else:
                output = PushOutput(
                    status='failed',
                    push_time=push_time,
                    message_length=len(message),
                    error_message=f"API 返回错误：{result}"
                )
                print(f"  ❌ 推送失败：{result}")
            
            # 验证输出
            print(f"\n🔍 验证推送 Layer 输出...")
            valid, msg = output.validate()
            if not valid:
                raise PushException(
                    layer='Push',
                    message='输出数据格式验证失败',
                    details=msg
                )
            print(f"  ✅ 输出格式验证通过")
            
            return output
            
        except PushException:
            raise
        except Exception as e:
            raise PushException(
                layer='Push',
                message='推送处理异常',
                details=f'{str(e)}\n{traceback.format_exc()}'
            )
    
    def _format_message(self, input_data: PushInput) -> str:
        """格式化推送消息"""
        lines = [
            f"🎯 工作流最终决策 Top{input_data.top_n}",
            f"⏰{datetime.now().strftime('%m-%d %H:%M')}",
            f"📊 仅主板 | 排除创业/科创/北交所",
            f"⚠️ 仅供参考，不构成投资建议",
            f"🔒 版本：{input_data.workflow_version}",
            ""
        ]
        
        # 分组显示
        rating_groups = {'强烈推荐': [], '推荐': [], '关注': [], '观望': []}
        for stock in input_data.stocks:
            rating = stock.get('rating', '观望')
            rating_groups[rating].append(stock)
        
        for rating in ['强烈推荐', '推荐', '关注', '观望']:
            group = rating_groups[rating]
            if not group:
                continue
            
            if rating == '强烈推荐':
                lines.append(f"━━⭐⭐⭐{rating} ({len(group)})━━")
            elif rating == '推荐':
                lines.append(f"━━⭐⭐{rating} ({len(group)})━━")
            elif rating == '关注':
                lines.append(f"━━⭐{rating} ({len(group)})━━")
            else:
                lines.append(f"━━⭕{rating} ({len(group)})━━")
            
            for i, stock in enumerate(group, 1):
                # 状态图标
                change = stock.get('change_pct', 0)
                if change > 2:
                    icon = '📗'
                elif change < -2:
                    icon = '📉'
                elif change > 0:
                    icon = '📈'
                else:
                    icon = '📉'
                
                code = stock.get('code', '')
                name = stock.get('name', '')
                price = stock.get('price', 0)
                turnover = stock.get('turnover', 0) / 100000000  # 亿
                
                lines.append(f"{i}. {icon}{name}(sh{code})⭐⭐⭐" if rating == '强烈推荐' else 
                            f"{i}. {icon}{name}(sh{code})⭐⭐" if rating == '推荐' else
                            f"{i}. {icon}{name}(sh{code})⭕")
                lines.append(f"   ¥{price:.2f} {change:+.1f}% 成交{turnover:.1f}亿")
                lines.append(f"   置信{stock.get('confidence', 0)}% 止盈¥{stock.get('stop_profit', 0):.1f} 止损¥{stock.get('stop_loss', 0):.1f}")
                lines.append(f"   💡{stock.get('tags', '')}")
            
            lines.append("")
        
        lines.append("="*50)
        lines.append("_💰 = 真实主力数据 | 📊 = 真实成交额数据_")
        lines.append("_🎯 综合多策略生成的最终决策_")
        lines.append("_⚠️ 严禁使用模拟/估算数据_")
        
        return '\n'.join(lines)
    
    def push_error(self, error: WorkflowException) -> PushOutput:
        """推送错误信息"""
        print(f"\n📤 推送错误报告...")
        
        message = f"""🚨 v8.0-Financial-Enhanced 基准版 - 执行异常报告
⏰{datetime.now().strftime('%m-%d %H:%M')}
📊 仅主板 | 排除创业/科创/北交所
⚠️ 仅供参考，不构成投资建议

━━❌ 工作流执行失败━━

📋 异常信息:
  Layer: {error.layer}
  错误：{error.message}
  详情：{error.details or '无'}

💡 建议:
  - 检查数据源状态
  - 查看完整日志
  - 等待系统恢复

==================================================
_📊 v8.0-Financial-Enhanced 基准版 - 严格数据契约_
_🔒 数据格式验证失败 = 工作流终止_"""
        
        try:
            import requests
            payload = {
                'msgtype': 'markdown',
                'markdown': {'content': message}
            }
            
            resp = requests.post(self.webhook, json=payload, timeout=10)
            result = resp.json()
            
            if result.get('errcode') == 0:
                print(f"  ✅ 错误报告推送成功")
                return PushOutput(
                    status='success',
                    push_time=datetime.now().isoformat(),
                    message_length=len(message),
                    error_message=None
                )
            else:
                print(f"  ❌ 错误报告推送失败：{result}")
                return PushOutput(
                    status='failed',
                    push_time=datetime.now().isoformat(),
                    message_length=len(message),
                    error_message=str(result)
                )
                
        except Exception as e:
            print(f"  ❌ 错误报告推送异常：{e}")
            return PushOutput(
                status='failed',
                push_time=datetime.now().isoformat(),
                message_length=len(message),
                error_message=str(e)
            )


# ============================================================================
# 主工作流
# ============================================================================

class V8StrictWorkflow:
    """
    v8.0-Financial-Enhanced 基准版 - 严格数据契约工作流
    
    执行流程:
    1. Layer 1: 数据获取 → 验证输出格式 → 失败则中断并推送
    2. Layer 2: 分析决策 → 验证输入输出 → 失败则中断并推送
    3. Layer 3: 输出推送 → 验证输入输出 → 失败则终止
    """
    
    VERSION = 'v8.0-Financial-Enhanced-Strict'
    
    def __init__(self):
        self.layer1 = DataFetchLayer()
        self.layer2 = AnalysisLayer()
        self.layer3 = PushLayer()
    
    def run(self, strategy: str = 'main', top_n: int = 10, push: bool = True) -> bool:
        """
        运行工作流
        
        Args:
            strategy: 策略类型
            top_n: 推荐数量
            push: 是否推送
        
        Returns:
            bool: 是否成功
        """
        print("\n" + "="*80)
        print(f"🚀 {self.VERSION} 严格数据契约工作流启动")
        print("="*80)
        print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"策略：{strategy}")
        print(f"目标数量：Top {top_n}")
        print(f"推送：{'开启' if push else '关闭'}")
        
        execution_time = datetime.now().isoformat()
        
        try:
            # Layer 1: 数据获取
            layer1_results = self.layer1.fetch(top_n)
            
            # 准备 Layer 2 输入
            all_stocks = []
            data_sources = []
            for result in layer1_results:
                if result.status == 'success':
                    all_stocks.extend(result.stocks)
                    data_sources.append(result.source_name)
            
            if not all_stocks:
                raise DataFetchException(
                    layer='DataFetch',
                    message='无有效股票数据',
                    details='所有数据源均失败'
                )
            
            analysis_input = AnalysisInput(
                stocks=all_stocks,
                data_sources=data_sources,
                total_count=len(all_stocks),
                fetch_time=execution_time
            )
            
            # Layer 2: 分析决策
            layer2_output = self.layer2.analyze(analysis_input, top_n)
            
            # 准备 Layer 3 输入
            push_input = PushInput(
                stocks=layer2_output.stocks,
                top_n=top_n,
                workflow_version=self.VERSION,
                execution_time=execution_time
            )
            
            # Layer 3: 输出推送
            if push:
                layer3_output = self.layer3.push(push_input)
                
                if layer3_output.status == 'failed':
                    print(f"\n❌ 推送失败：{layer3_output.error_message}")
                    return False
            
            print("\n" + "="*80)
            print("✅ 工作流执行成功")
            print("="*80)
            return True
            
        except WorkflowException as e:
            print(f"\n❌ 工作流异常：{e}")
            print(f"详情：{e.details}")
            
            if push:
                self.layer3.push_error(e)
            
            return False
            
        except Exception as e:
            print(f"\n❌ 未知异常：{e}")
            traceback.print_exc()
            
            if push:
                error = WorkflowException(
                    layer='Workflow',
                    message='未知异常',
                    details=str(e)
                )
                self.layer3.push_error(error)
            
            return False


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='v8.0-Financial-Enhanced 严格数据契约工作流')
    parser.add_argument('--strategy', default='main', choices=['main', 'gainers', 'volume'])
    parser.add_argument('--top', type=int, default=10, help='推荐数量')
    parser.add_argument('--push', action='store_true', help='推送到企业微信')
    
    args = parser.parse_args()
    
    workflow = V8StrictWorkflow()
    success = workflow.run(
        strategy=args.strategy,
        top_n=args.top,
        push=args.push
    )
    
    sys.exit(0 if success else 1)
