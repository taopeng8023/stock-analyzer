#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票可视化系统 - HTML 版本
生成可交互的 HTML 图表（使用 Plotly.js CDN）
"""

import json
import os
from datetime import datetime, timedelta
import numpy as np

def generate_mock_data(code: str, days: int = 60) -> list:
    """生成模拟 K 线数据"""
    np.random.seed(42)
    data = []
    base_price = 50.0
    current_price = base_price
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d')
        change = np.random.randn() * 0.03
        close = current_price * (1 + change)
        high = max(current_price, close) * (1 + np.random.rand() * 0.02)
        low = min(current_price, close) * (1 - np.random.rand() * 0.02)
        open_price = low + (high - low) * np.random.rand()
        volume = np.random.randint(1000000, 10000000)
        
        data.append({
            'date': date,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume
        })
        current_price = close
    
    return data

def calculate_macd(data: list) -> dict:
    """计算 MACD"""
    closes = [d['close'] for d in data]
    
    exp1 = []
    exp2 = []
    
    for i in range(len(closes)):
        if i == 0:
            exp1.append(closes[0])
            exp2.append(closes[0])
        else:
            exp1.append(closes[i] * 2/13 + exp1[-1] * 11/13)
            exp2.append(closes[i] * 2/27 + exp2[-1] * 25/27)
    
    dif = [exp1[i] - exp2[i] for i in range(len(exp1))]
    dea = []
    for i in range(len(dif)):
        if i == 0:
            dea.append(dif[0])
        else:
            dea.append(dif[i] * 2/10 + dea[-1] * 8/10)
    
    macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(dif))]
    
    return {
        'dif': [round(x, 4) for x in dif],
        'dea': [round(x, 4) for x in dea],
        'macd': [round(x, 4) for x in macd_bar]
    }

def create_html_chart(code: str, name: str, stock_info: dict, save_path: str = None):
    """创建 HTML 交互式图表"""
    
    # 生成数据
    data = generate_mock_data(code, 60)
    dates = [d['date'] for d in data]
    opens = [d['open'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    closes = [d['close'] for d in data]
    volumes = [d['volume'] for d in data]
    
    # 计算 MACD
    macd_data = calculate_macd(data)
    
    # 计算均线
    def calc_ma(prices, period):
        ma = []
        for i in range(len(prices)):
            if i < period - 1:
                ma.append(None)
            else:
                ma.append(round(sum(prices[i-period+1:i+1]) / period, 2))
        return ma
    
    ma5 = calc_ma(closes, 5)
    ma10 = calc_ma(closes, 10)
    ma20 = calc_ma(closes, 20)
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} ({code}) - 股票分析仪表盘</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            color: #333;
            font-size: 28px;
        }}
        .header p {{
            margin: 10px 0 0 0;
            color: #666;
            font-size: 14px;
        }}
        .score-card {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .score-item {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .score-value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }}
        .score-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        .chart-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .info-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .info-card h3 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .indicator-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .indicator-table th,
        .indicator-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .indicator-table th {{
            background: #f8f9fa;
            font-weight: bold;
            color: #333;
        }}
        .indicator-table tr:hover {{
            background: #f8f9fa;
        }}
        .recommendation {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .recommendation h3 {{
            margin-top: 0;
        }}
        .rec-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-top: 15px;
        }}
        .rec-item {{
            text-align: center;
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 8px;
        }}
        .rec-value {{
            font-size: 24px;
            font-weight: bold;
        }}
        .rec-label {{
            font-size: 12px;
            opacity: 0.9;
            margin-top: 5px;
        }}
        .footer {{
            text-align: center;
            color: white;
            padding: 20px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 {name} ({code}) 股票分析仪表盘</h1>
            <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据周期：60 日</p>
        </div>
        
        <div class="score-card">
            <div class="score-item">
                <div class="score-value">{stock_info.get('total_score', 0):.1f}</div>
                <div class="score-label">综合评分</div>
            </div>
            <div class="score-item">
                <div class="score-value">{stock_info.get('tech_score', 0):.1f}</div>
                <div class="score-label">技术面 (30 分)</div>
            </div>
            <div class="score-item">
                <div class="score-value">{stock_info.get('fund_score', 0):.1f}</div>
                <div class="score-label">资金面 (20 分)</div>
            </div>
            <div class="score-item">
                <div class="score-value">{stock_info.get('win_probability', 70)}%</div>
                <div class="score-label">盈利概率</div>
            </div>
            <div class="score-item">
                <div class="score-value">{stock_info.get('recommendation', {}).get('position', '-')}</div>
                <div class="score-label">建议仓位</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div id="kline-chart"></div>
        </div>
        
        <div class="chart-container">
            <div id="macd-chart"></div>
        </div>
        
        <div class="info-grid">
            <div class="info-card">
                <h3>📊 技术指标明细</h3>
                <table class="indicator-table">
                    <thead>
                        <tr>
                            <th>指标</th>
                            <th>得分</th>
                            <th>数值</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>MACD</td>
                            <td>{stock_info.get('macd_score', 0):.1f}/10</td>
                            <td>DIF: {stock_info.get('macd_dif', 0):.2f}</td>
                            <td>{stock_info.get('macd_trend', '-')}</td>
                        </tr>
                        <tr>
                            <td>KDJ</td>
                            <td>{stock_info.get('kdj_score', 0):.1f}/10</td>
                            <td>K: {stock_info.get('kdj_k', 0):.0f}</td>
                            <td>{stock_info.get('kdj_position', '-')}</td>
                        </tr>
                        <tr>
                            <td>RSI</td>
                            <td>{stock_info.get('rsi_score', 0):.1f}/10</td>
                            <td>RSI6: {stock_info.get('rsi6', 0):.0f}</td>
                            <td>{'多头' if stock_info.get('rsi6', 50) > stock_info.get('rsi12', 50) else '空头'}</td>
                        </tr>
                        <tr>
                            <td>均线</td>
                            <td>{stock_info.get('ma_score', 0):.1f}/10</td>
                            <td>MA5: {stock_info.get('ma5', 0):.2f}</td>
                            <td>{stock_info.get('ma_trend', '-')}</td>
                        </tr>
                        <tr>
                            <td>成交量</td>
                            <td>{stock_info.get('volume_score', 0):.1f}/10</td>
                            <td>量比：{stock_info.get('volume_ratio', 0):.2f}</td>
                            <td>{'活跃' if stock_info.get('volume_ratio', 1) > 1.5 else '一般'}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="info-card">
                <h3>💰 资金流分析</h3>
                <table class="indicator-table">
                    <tr>
                        <td><strong>主力净流入</strong></td>
                        <td style="color: {'red' if stock_info.get('main_net_inflow', 0) > 0 else 'green'}">
                            {stock_info.get('main_net_inflow', 0):,.0f} 万
                        </td>
                    </tr>
                    <tr>
                        <td><strong>主力占比</strong></td>
                        <td>{stock_info.get('main_ratio', 0):.2f}%</td>
                    </tr>
                    <tr>
                        <td><strong>超大单占比</strong></td>
                        <td>{stock_info.get('super_ratio', 0):.2f}%</td>
                    </tr>
                    <tr>
                        <td><strong>成交额</strong></td>
                        <td>{stock_info.get('amount', 0):.1f} 亿</td>
                    </tr>
                    <tr>
                        <td><strong>换手率</strong></td>
                        <td>{stock_info.get('turnover_rate', 0):.2f}%</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="recommendation">
            <h3>💡 推荐建议</h3>
            <div class="rec-grid">
                <div class="rec-item">
                    <div class="rec-value">{stock_info.get('recommendation', {}).get('position', '-')}</div>
                    <div class="rec-label">建议仓位</div>
                </div>
                <div class="rec-item">
                    <div class="rec-value">{stock_info.get('recommendation', {}).get('take_profit', '-')}</div>
                    <div class="rec-label">止盈目标</div>
                </div>
                <div class="rec-item">
                    <div class="rec-value">{stock_info.get('recommendation', {}).get('stop_loss', '-')}</div>
                    <div class="rec-label">止损点位</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>⚠️ 免责声明：以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。</p>
            <p>股票推荐系统 v3.0 | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
    
    <script>
        // K 线图
        const traceCandle = {{
            x: {json.dumps(dates)},
            close: {json.dumps(closes)},
            decreasing: {{line: {{color: 'green'}}}},
            high: {json.dumps(highs)},
            increasing: {{line: {{color: 'red'}}}},
            low: {json.dumps(lows)},
            open: {json.dumps(opens)},
            type: 'candlestick',
            xaxis: 'x',
            yaxis: 'y',
            name: 'K 线'
        }};
        
        const traceMA5 = {{
            x: {json.dumps(dates)},
            y: {json.dumps(ma5)},
            type: 'scatter',
            mode: 'lines',
            line: {{color: 'white', width: 1.5}},
            name: 'MA5'
        }};
        
        const traceMA10 = {{
            x: {json.dumps(dates)},
            y: {json.dumps(ma10)},
            type: 'scatter',
            mode: 'lines',
            line: {{color: 'yellow', width: 1.5}},
            name: 'MA10'
        }};
        
        const traceMA20 = {{
            x: {json.dumps(dates)},
            y: {json.dumps(ma20)},
            type: 'scatter',
            mode: 'lines',
            line: {{color: 'cyan', width: 1.5}},
            name: 'MA20'
        }};
        
        const layoutKline = {{
            title: '{name} ({code}) K 线与均线',
            plot_bgcolor: '#1e1e1e',
            paper_bgcolor: '#1e1e1e',
            font: {{color: 'white'}},
            xaxis: {{
                title: '日期',
                gridcolor: '#333',
                showgrid: true
            }},
            yaxis: {{
                title: '价格',
                gridcolor: '#333',
                showgrid: true
            }},
            showlegend: true,
            legend: {{
                x: 0,
                y: 1
            }},
            margin: {{t: 60, b: 60, l: 60, r: 60}}
        }};
        
        Plotly.newPlot('kline-chart', [traceCandle, traceMA5, traceMA10, traceMA20], layoutKline, {{responsive: true}});
        
        // MACD 图
        const macdBar = {{
            x: {json.dumps(dates)},
            y: {json.dumps(macd_data['macd'])},
            type: 'bar',
            marker: {{
                color: {json.dumps(['red' if x > 0 else 'green' for x in macd_data['macd']])}
            }},
            name: 'MACD',
            opacity: 0.7
        }};
        
        const traceDIF = {{
            x: {json.dumps(dates)},
            y: {json.dumps(macd_data['dif'])},
            type: 'scatter',
            mode: 'lines',
            line: {{color: 'white', width: 1.5}},
            name: 'DIF'
        }};
        
        const traceDEA = {{
            x: {json.dumps(dates)},
            y: {json.dumps(macd_data['dea'])},
            type: 'scatter',
            mode: 'lines',
            line: {{color: 'yellow', width: 1.5}},
            name: 'DEA'
        }};
        
        const layoutMACD = {{
            title: 'MACD 指标',
            plot_bgcolor: '#1e1e1e',
            paper_bgcolor: '#1e1e1e',
            font: {{color: 'white'}},
            xaxis: {{
                title: '日期',
                gridcolor: '#333',
                showgrid: true
            }},
            yaxis: {{
                title: 'MACD',
                gridcolor: '#333',
                showgrid: true
            }},
            showlegend: true,
            margin: {{t: 60, b: 60, l: 60, r: 60}}
        }};
        
        Plotly.newPlot('macd-chart', [macdBar, traceDIF, traceDEA], layoutMACD, {{responsive: true}});
    </script>
</body>
</html>
'''
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ HTML 图表已保存：{save_path}")
    
    return html_content

def main():
    """主函数"""
    print("=" * 70)
    print(" " * 20 + "股票可视化系统 - HTML 版")
    print("=" * 70)
    
    # 示例股票信息
    stock_info = {
        'tech_score': 27.5,
        'fund_score': 20.0,
        'theme_score': 15.0,
        'fundamental_score': 10.5,
        'risk_score': 7.5,
        'total_score': 80.5,
        'win_probability': 70,
        'macd_score': 10.0,
        'macd_dif': 1.5,
        'macd_trend': '金叉',
        'kdj_score': 8.0,
        'kdj_k': 75,
        'kdj_position': '中性',
        'rsi_score': 8.0,
        'rsi6': 68,
        'rsi12': 62,
        'ma_score': 9.0,
        'ma5': 49.5,
        'ma_trend': '多头',
        'volume_score': 10.0,
        'volume_ratio': 3.14,
        'turnover_rate': 3.53,
        'amount': 128,
        'main_net_inflow': 296900,
        'main_ratio': 22.76,
        'super_ratio': 27.70,
        'recommendation': {
            'position': '15-20%',
            'take_profit': '+10-15%',
            'stop_loss': '-10%'
        }
    }
    
    # 创建输出目录
    output_dir = '/home/admin/.openclaw/workspace/data/charts'
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建 HTML 图表
    print("\n📊 生成 HTML 交互式图表...")
    create_html_chart('002475', '立讯精密', stock_info,
                     save_path=f'{output_dir}/dashboard_002475.html')
    
    print("\n✅ 图表生成完成！")
    print(f"📁 保存位置：{output_dir}/")
    print("\n使用说明:")
    print("  用浏览器打开 HTML 文件即可查看交互式图表")
    print("  支持缩放、悬停查看数据、切换指标显示等")

if __name__ == "__main__":
    main()
