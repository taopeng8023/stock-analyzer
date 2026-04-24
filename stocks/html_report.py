#!/usr/bin/env python3
"""
鹏总选股系统 - HTML 可视化报告生成器
生成美观的 HTML 报告，包含图表、评分、资金流向等

鹏总专用 - 2026 年 3 月 26 日
"""

import json
import os
from datetime import datetime
from typing import Dict, List


class HTMLReportGenerator:
    """HTML 可视化报告生成器"""
    
    def __init__(self, output_dir: str = "/home/admin/.openclaw/workspace/stocks/reports/"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_stock_report(self, stock_data: dict, output_file: str = None) -> str:
        """生成个股分析报告"""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"{self.output_dir}/{stock_data.get('code', 'stock')}_{timestamp}.html"
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{stock_data.get('name', '股票')} - 分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }}
        .header h1 {{ font-size: 36px; margin-bottom: 10px; }}
        .header .code {{ font-size: 18px; opacity: 0.9; }}
        .header .price {{ font-size: 48px; font-weight: bold; margin: 20px 0; }}
        .header .change {{ font-size: 24px; padding: 10px 30px; background: rgba(255,255,255,0.2); border-radius: 50px; display: inline-block; }}
        .content {{ padding: 40px; }}
        .section {{ margin-bottom: 40px; }}
        .section-title {{ font-size: 24px; color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #667eea; }}
        .score-card {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .score-item {{ background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 30px; border-radius: 15px; text-align: center; transition: transform 0.3s; }}
        .score-item:hover {{ transform: translateY(-5px); }}
        .score-label {{ font-size: 16px; color: #666; margin-bottom: 10px; }}
        .score-value {{ font-size: 48px; font-weight: bold; color: #667eea; }}
        .score-bar {{ height: 10px; background: #e0e0e0; border-radius: 5px; margin-top: 15px; overflow: hidden; }}
        .score-bar-fill {{ height: 100%; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 5px; transition: width 1s; }}
        .advice-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 15px; text-align: center; margin-bottom: 30px; }}
        .advice-icon {{ font-size: 72px; margin-bottom: 20px; }}
        .advice-text {{ font-size: 32px; font-weight: bold; margin-bottom: 10px; }}
        .advice-position {{ font-size: 20px; opacity: 0.9; }}
        .data-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .data-item {{ background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea; }}
        .data-label {{ font-size: 14px; color: #666; margin-bottom: 5px; }}
        .data-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .signal-list {{ list-style: none; }}
        .signal-item {{ padding: 15px; margin-bottom: 10px; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #667eea; }}
        .signal-item.positive {{ border-left-color: #4caf50; }}
        .signal-item.negative {{ border-left-color: #f44336; }}
        .signal-item.neutral {{ border-left-color: #ff9800; }}
        .chart-container {{ position: relative; height: 300px; margin: 30px 0; }}
        .footer {{ text-align: center; padding: 30px; background: #f8f9fa; color: #666; font-size: 14px; }}
        .positive {{ color: #4caf50; }}
        .negative {{ color: #f44336; }}
        @media (max-width: 768px) {{ .header h1 {{ font-size: 24px; }} .score-value {{ font-size: 36px; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{stock_data.get('name', '股票')}</h1>
            <div class="code">代码：{stock_data.get('code', 'N/A')}</div>
            <div class="price">¥{stock_data.get('price', 0):.2f}</div>
            <div class="change {'positive' if stock_data.get('change_pct', 0) > 0 else 'negative'}">
                {stock_data.get('change_pct', 0):+.2f}%
            </div>
            <div style="margin-top: 20px; opacity: 0.9;">
                分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        
        <div class="content">
            <!-- 综合评分 -->
            <div class="section">
                <h2 class="section-title">🎯 综合评分</h2>
                <div class="score-card">
                    <div class="score-item">
                        <div class="score-label">技术面</div>
                        <div class="score-value">{stock_data.get('tech_score', 0)}</div>
                        <div class="score-bar">
                            <div class="score-bar-fill" style="width: {stock_data.get('tech_score', 0)}%;"></div>
                        </div>
                    </div>
                    <div class="score-item">
                        <div class="score-label">基本面</div>
                        <div class="score-value">{stock_data.get('fund_score', 0)}</div>
                        <div class="score-bar">
                            <div class="score-bar-fill" style="width: {stock_data.get('fund_score', 0)}%;"></div>
                        </div>
                    </div>
                    <div class="score-item">
                        <div class="score-label">资金面</div>
                        <div class="score-value">{stock_data.get('money_score', 0)}</div>
                        <div class="score-bar">
                            <div class="score-bar-fill" style="width: {stock_data.get('money_score', 0)}%;"></div>
                        </div>
                    </div>
                    <div class="score-item" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                        <div class="score-label">总评分</div>
                        <div class="score-value" style="color: white;">{stock_data.get('total_score', 0):.1f}</div>
                        <div class="score-bar" style="background: rgba(255,255,255,0.3);">
                            <div class="score-bar-fill" style="width: {stock_data.get('total_score', 0):.1f}%; background: white;"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 操作建议 -->
            <div class="section">
                <h2 class="section-title">💡 操作建议</h2>
                <div class="advice-card">
                    <div class="advice-icon">{stock_data.get('icon', '⚪')}</div>
                    <div class="advice-text">{stock_data.get('advice', '观望')}</div>
                    <div class="advice-position">建议仓位：{stock_data.get('position', '0%')}</div>
                </div>
            </div>
            
            <!-- 详细数据 -->
            <div class="section">
                <h2 class="section-title">📊 详细数据</h2>
                <div class="data-grid">
                    <div class="data-item">
                        <div class="data-label">10 日预期收益</div>
                        <div class="data-value {'positive' if stock_data.get('expected_return', 0) > 0 else 'negative'}">{stock_data.get('expected_return', 0):+.1f}%</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">成功概率</div>
                        <div class="data-value">{stock_data.get('probability', 0):.1f}%</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">目标价位</div>
                        <div class="data-value">¥{stock_data.get('target_price', 0):.2f}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">止损价位</div>
                        <div class="data-value negative">¥{stock_data.get('stop_loss', 0):.2f}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">主力净流入</div>
                        <div class="data-value {'positive' if stock_data.get('main_net', 0) > 0 else 'negative'}">{stock_data.get('main_net', 0)/100000000:.2f}亿</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">主力占比</div>
                        <div class="data-value">{stock_data.get('main_ratio', 0):.2f}%</div>
                    </div>
                </div>
            </div>
            
            <!-- 信号列表 -->
            <div class="section">
                <h2 class="section-title">📋 分析信号</h2>
                <ul class="signal-list">
"""
        
        for signal in stock_data.get('signals', []):
            signal_class = 'neutral'
            if signal.startswith('✓'):
                signal_class = 'positive'
            elif signal.startswith('✗'):
                signal_class = 'negative'
            
            html += f'                    <li class="signal-item {signal_class}">{signal}</li>\n'
        
        html += f"""
                </ul>
            </div>
            
            <!-- 策略建议 -->
            <div class="section">
                <h2 class="section-title">🎯 交易策略</h2>
                <div class="data-grid">
"""
        
        for i, strategy in enumerate(stock_data.get('strategies', []), 1):
            html += f"""                    <div class="data-item">
                        <div class="data-label">策略 {i}</div>
                        <div class="data-value" style="font-size: 16px;">{strategy}</div>
                    </div>
"""
        
        html += f"""
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>⚠️ 风险提示：股市有风险，投资需谨慎</p>
            <p>本报告由鹏总选股系统 v2.0 自动生成，仅供参考，不构成投资建议</p>
            <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_file
    
    def generate_daily_report(self, market_data: dict, top_stocks: list, top_sectors: list) -> str:
        """生成每日报告"""
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = f"{self.output_dir}/daily_report_{timestamp}.html"
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>鹏总选股日报 {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f6fa; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.1); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }}
        .header h1 {{ font-size: 36px; margin-bottom: 10px; }}
        .header .date {{ font-size: 18px; opacity: 0.9; }}
        .content {{ padding: 40px; }}
        .section {{ margin-bottom: 40px; }}
        .section-title {{ font-size: 24px; color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #667eea; }}
        .market-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .market-item {{ background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 25px; border-radius: 15px; text-align: center; }}
        .market-label {{ font-size: 14px; color: #666; margin-bottom: 10px; }}
        .market-value {{ font-size: 28px; font-weight: bold; color: #667eea; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; text-align: left; }}
        td {{ padding: 15px; border-bottom: 1px solid #e0e0e0; }}
        tr:hover {{ background: #f5f6fa; }}
        .positive {{ color: #4caf50; }}
        .negative {{ color: #f44336; }}
        .footer {{ text-align: center; padding: 30px; background: #f8f9fa; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 鹏总选股日报</h1>
            <div class="date">{datetime.now().strftime('%Y年%m月%d日')}</div>
        </div>
        
        <div class="content">
            <!-- 市场概览 -->
            <div class="section">
                <h2 class="section-title">📈 市场概览</h2>
                <div class="market-grid">
                    <div class="market-item">
                        <div class="market-label">上证指数</div>
                        <div class="market-value">{market_data.get('sh_index', 'N/A')}</div>
                    </div>
                    <div class="market-item">
                        <div class="market-label">深证成指</div>
                        <div class="market-value">{market_data.get('sz_index', 'N/A')}</div>
                    </div>
                    <div class="market-item">
                        <div class="market-label">创业板指</div>
                        <div class="market-value">{market_data.get('cyb_index', 'N/A')}</div>
                    </div>
                    <div class="market-item">
                        <div class="market-label">成交量</div>
                        <div class="market-value">{market_data.get('volume', 'N/A')}亿</div>
                    </div>
                </div>
            </div>
            
            <!-- 主力净流入 TOP 10 -->
            <div class="section">
                <h2 class="section-title">💰 主力净流入 TOP 10</h2>
                <table>
                    <thead>
                        <tr>
                            <th>序号</th>
                            <th>代码</th>
                            <th>名称</th>
                            <th>现价</th>
                            <th>涨幅</th>
                            <th>主力净额 (亿)</th>
                            <th>主力占比</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for i, stock in enumerate(top_stocks[:10], 1):
            change_class = 'positive' if stock.get('change_pct', 0) > 0 else 'negative'
            html += f"""                        <tr>
                            <td>{i}</td>
                            <td>{stock.get('code', 'N/A')}</td>
                            <td>{stock.get('name', 'N/A')}</td>
                            <td>¥{stock.get('price', 0):.2f}</td>
                            <td class="{change_class}">{stock.get('change_pct', 0):+.2f}%</td>
                            <td class="{'positive' if stock.get('main_net', 0) > 0 else 'negative'}">{stock.get('main_net', 0)/100000000:.2f}</td>
                            <td>{stock.get('main_ratio', 0):.2f}%</td>
                        </tr>
"""
        
        html += f"""
                    </tbody>
                </table>
            </div>
            
            <!-- 热门板块 -->
            <div class="section">
                <h2 class="section-title">🔥 热门板块</h2>
                <table>
                    <thead>
                        <tr>
                            <th>序号</th>
                            <th>板块名称</th>
                            <th>最新价</th>
                            <th>涨幅</th>
                            <th>主力净额 (亿)</th>
                            <th>主力占比</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for i, sector in enumerate(top_sectors[:10], 1):
            change_class = 'positive' if sector.get('change_pct', 0) > 0 else 'negative'
            html += f"""                        <tr>
                            <td>{i}</td>
                            <td>{sector.get('name', 'N/A')}</td>
                            <td>{sector.get('price', 0):.2f}</td>
                            <td class="{change_class}">{sector.get('change_pct', 0):+.2f}%</td>
                            <td class="{'positive' if sector.get('main_net', 0) > 0 else 'negative'}">{sector.get('main_net', 0)/100000000:.2f}</td>
                            <td>{sector.get('main_ratio', 0):.2f}%</td>
                        </tr>
"""
        
        html += f"""
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>⚠️ 风险提示：股市有风险，投资需谨慎</p>
            <p>鹏总选股系统 v2.0 - 让投资更简单</p>
            <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_file


if __name__ == "__main__":
    generator = HTMLReportGenerator()
    
    # 测试数据
    test_stock = {
        'code': '601899',
        'name': '紫金矿业',
        'price': 32.09,
        'change_pct': 1.25,
        'tech_score': 75,
        'fund_score': 82,
        'money_score': 73,
        'total_score': 77.4,
        'icon': '🟢',
        'advice': '推荐买入',
        'position': '25-35%',
        'expected_return': 9.7,
        'probability': 71.2,
        'target_price': 35.20,
        'stop_loss': 29.52,
        'main_net': 1250000000,
        'main_ratio': 8.5,
        'signals': [
            '✓ 主力大幅净流入 (12.50 亿)',
            '✓ 主力占比很高 (8.5%)',
            '✓ 均线多头排列',
            '✓ RSI 中性偏强 (62.5)',
            '✓ PE 合理 (15.2)',
            '✓ ROE 优秀 (>20%)',
        ],
        'strategies': [
            '分批建仓，首笔 30%',
            '止损位：-8%',
            '止盈位：+25%',
            '持有周期：5-10 天',
        ]
    }
    
    # 生成报告
    output_file = generator.generate_stock_report(test_stock)
    print(f"\n✅ HTML 报告已生成：{output_file}\n")
