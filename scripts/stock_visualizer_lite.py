#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票可视化系统 - 简化版
使用 matplotlib 生成 K 线图和指标图
"""

import matplotlib
matplotlib.use('Agg')  # 非交互模式
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

def generate_mock_data(code: str, days: int = 60) -> pd.DataFrame:
    """生成模拟 K 线数据"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    base_price = 50.0
    returns = np.random.randn(days) * 0.03
    close = base_price * (1 + returns).cumprod()
    
    high = close * (1 + np.random.rand(days) * 0.02)
    low = close * (1 - np.random.rand(days) * 0.02)
    open_price = low + (high - low) * np.random.rand(days)
    volume = np.random.randint(1000000, 10000000, days)
    
    df = pd.DataFrame({
        'Date': dates,
        'Open': open_price,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume
    })
    df.set_index('Date', inplace=True)
    
    return df

def calculate_indicators(df: pd.DataFrame) -> dict:
    """计算技术指标"""
    indicators = {}
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    dif = exp1 - exp2
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_bar = (dif - dea) * 2
    indicators['macd'] = {'dif': dif, 'dea': dea, 'bar': macd_bar}
    
    # KDJ
    low_min = df['Low'].rolling(window=9).min()
    high_max = df['High'].rolling(window=9).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    indicators['kdj'] = {'k': k, 'd': d, 'j': j}
    
    # RSI
    for period in [6, 12, 24]:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        indicators[f'rsi{period}'] = rsi
    
    # 均线
    for period in [5, 10, 20, 60]:
        indicators[f'ma{period}'] = df['Close'].rolling(window=period).mean()
    
    return indicators

def create_kdj_chart(df: pd.DataFrame, indicators: dict, code: str, name: str, 
                     save_path: str = None):
    """创建 KDJ 分析图表"""
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.08)
    
    # 1. K 线图
    ax0 = fig.add_subplot(gs[0, 0])
    x = np.arange(len(df))
    
    # 绘制蜡烛图
    colors = ['red' if df.iloc[i]['Close'] >= df.iloc[i]['Open'] else 'green' 
              for i in range(len(df))]
    
    for i in range(len(df)):
        if df.iloc[i]['Close'] >= df.iloc[i]['Open']:
            # 阳线
            ax0.plot([x[i], x[i]], [df.iloc[i]['Low'], df.iloc[i]['High']], 'r-', linewidth=1)
            ax0.plot([x[i], x[i]], [df.iloc[i]['Open'], df.iloc[i]['Close']], 'r-', linewidth=3)
        else:
            # 阴线
            ax0.plot([x[i], x[i]], [df.iloc[i]['Low'], df.iloc[i]['High']], 'g-', linewidth=1)
            ax0.plot([x[i], x[i]], [df.iloc[i]['Open'], df.iloc[i]['Close']], 'g-', linewidth=3)
    
    # 绘制均线
    for period, color in [(5, 'white'), (10, 'yellow'), (20, 'blue'), (60, 'gray')]:
        ma = indicators.get(f'ma{period}', pd.Series())
        if len(ma) > 0:
            ax0.plot(x, ma, color=color, label=f'MA{period}', linewidth=1, alpha=0.8)
    
    ax0.set_title(f'{name} ({code}) K 线图', fontsize=14, fontweight='bold', pad=10)
    ax0.set_ylabel('价格')
    ax0.legend(loc='upper left', fontsize=8)
    ax0.grid(True, alpha=0.3)
    ax0.set_xlim(0, len(df)-1)
    
    # 2. KDJ 指标
    ax1 = fig.add_subplot(gs[1, 0], sharex=ax0)
    kdj = indicators.get('kdj', {})
    if kdj:
        ax1.plot(x, kdj.get('k', []), label='K', color='yellow', linewidth=1)
        ax1.plot(x, kdj.get('d', []), label='D', color='blue', linewidth=1)
        ax1.plot(x, kdj.get('j', []), label='J', color='magenta', linewidth=1)
        ax1.axhline(80, color='red', linestyle='--', linewidth=0.5, alpha=0.5)
        ax1.axhline(20, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
        ax1.fill_between(x, 20, 80, alpha=0.1, color='gray')
        ax1.set_ylabel('KDJ')
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 100)
    
    # 3. MACD 指标
    ax2 = fig.add_subplot(gs[2, 0], sharex=ax0)
    macd = indicators.get('macd', {})
    if macd:
        colors_bar = ['red' if val > 0 else 'green' for val in macd.get('bar', [])]
        ax2.bar(x, macd.get('bar', []), color=colors_bar, alpha=0.5, width=1)
        ax2.plot(x, macd.get('dif', []), label='DIF', color='white', linewidth=1)
        ax2.plot(x, macd.get('dea', []), label='DEA', color='yellow', linewidth=1)
        ax2.axhline(0, color='gray', linestyle='-', linewidth=0.5)
        ax2.set_ylabel('MACD')
        ax2.legend(loc='upper right', fontsize=8)
        ax2.grid(True, alpha=0.3)
    
    # 4. RSI 指标
    ax3 = fig.add_subplot(gs[3, 0], sharex=ax0)
    for period, color in [(6, 'white'), (12, 'yellow'), (24, 'blue')]:
        rsi = indicators.get(f'rsi{period}', pd.Series())
        if len(rsi) > 0:
            ax3.plot(x, rsi, label=f'RSI{period}', color=color, linewidth=1)
    ax3.axhline(70, color='red', linestyle='--', linewidth=0.5, alpha=0.5)
    ax3.axhline(30, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
    ax3.fill_between(x, 30, 70, alpha=0.1, color='gray')
    ax3.set_ylabel('RSI')
    ax3.set_xlabel('日期')
    ax3.legend(loc='upper right', fontsize=8)
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, 100)
    
    # 隐藏 x 轴标签
    plt.setp(ax0.get_xticklabels(), visible=False)
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), visible=False)
    
    plt.suptitle(f'{name} ({code}) 技术分析', fontsize=16, fontweight='bold', y=0.995)
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"✅ 图表已保存：{save_path}")
    
    plt.close()

def create_dashboard_chart(df: pd.DataFrame, indicators: dict, code: str, name: str, 
                          stock_info: dict, save_path: str = None):
    """创建股票分析仪表盘"""
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 2, height_ratios=[2, 1, 1], hspace=0.3, wspace=0.25)
    
    x = np.arange(len(df))
    
    # 1. K 线图 + 均线
    ax0 = fig.add_subplot(gs[0, :])
    colors = ['red' if df.iloc[i]['Close'] >= df.iloc[i]['Open'] else 'green' 
              for i in range(len(df))]
    
    for i in range(len(df)):
        color = 'r' if df.iloc[i]['Close'] >= df.iloc[i]['Open'] else 'g'
        ax0.plot([x[i], x[i]], [df.iloc[i]['Low'], df.iloc[i]['High']], f'{color}-', linewidth=1)
        ax0.plot([x[i], x[i]], [df.iloc[i]['Open'], df.iloc[i]['Close']], f'{color}-', linewidth=3)
    
    # 绘制均线
    for period, color in [(5, 'white'), (10, 'yellow'), (20, 'cyan'), (60, 'magenta')]:
        ma = indicators.get(f'ma{period}', pd.Series())
        if len(ma) > 0:
            ax0.plot(x, ma, color=color, label=f'MA{period}', linewidth=1.5, alpha=0.8)
    
    ax0.set_title(f'{name} ({code}) K 线与均线', fontsize=14, fontweight='bold')
    ax0.set_ylabel('价格')
    ax0.legend(loc='upper left', fontsize=9)
    ax0.grid(True, alpha=0.3)
    
    # 2. 成交量
    ax1 = fig.add_subplot(gs[1, 0])
    vol_colors = ['red' if df.iloc[i]['Close'] >= df.iloc[i]['Open'] else 'green' 
                  for i in range(len(df))]
    ax1.bar(x, df['Volume'], color=vol_colors, alpha=0.5, width=1)
    ax1.set_title('成交量', fontsize=12, fontweight='bold')
    ax1.set_ylabel('成交量')
    ax1.grid(True, alpha=0.3)
    
    # 3. 评分雷达图
    ax2 = fig.add_subplot(gs[1, 1], projection='polar')
    categories = ['技术面\n(30 分)', '资金面\n(20 分)', '题材面\n(20 分)', '基本面\n(15 分)', '风险面\n(15 分)']
    scores = [
        stock_info.get('tech_score', 0),
        stock_info.get('fund_score', 0),
        stock_info.get('theme_score', 0),
        stock_info.get('fundamental_score', 0),
        stock_info.get('risk_score', 0)
    ]
    max_scores = [30, 20, 20, 15, 15]
    normalized = [s/m*100 for s, m in zip(scores, max_scores)]
    
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values = normalized + [normalized[0]]
    angles += angles[:1]
    
    ax2.plot(angles, values, 'o-', linewidth=2, color='#FF6B6B', markersize=8)
    ax2.fill(angles, values, alpha=0.25, color='#FF6B6B')
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(categories, fontsize=9)
    ax2.set_ylim(0, 100)
    ax2.set_title(f'综合评分：{stock_info.get("total_score", 0):.1f}/100', 
                  fontsize=12, fontweight='bold', pad=20)
    ax2.grid(True)
    
    # 4. 技术指标表
    ax3 = fig.add_subplot(gs[2, :])
    ax3.axis('off')
    
    table_data = [
        ['MACD', f"{stock_info.get('macd_score', 0):.1f}/10", 
         f"DIF: {stock_info.get('macd_dif', 0):.2f}", f"趋势：{stock_info.get('macd_trend', '-')}"],
        ['KDJ', f"{stock_info.get('kdj_score', 0):.1f}/10",
         f"K: {stock_info.get('kdj_k', 0):.0f}", f"位置：{stock_info.get('kdj_position', '-')}"],
        ['RSI', f"{stock_info.get('rsi_score', 0):.1f}/10",
         f"RSI6: {stock_info.get('rsi6', 0):.0f}", f"排列：{'多头' if stock_info.get('rsi6', 50) > stock_info.get('rsi12', 50) else '空头'}"],
        ['均线', f"{stock_info.get('ma_score', 0):.1f}/10",
         f"MA5: {stock_info.get('ma5', 0):.2f}", f"趋势：{stock_info.get('ma_trend', '-')}"],
        ['成交量', f"{stock_info.get('volume_score', 0):.1f}/10",
         f"量比：{stock_info.get('volume_ratio', 0):.2f}", f"换手：{stock_info.get('turnover_rate', 0):.2f}%"],
    ]
    
    table = ax3.table(cellText=table_data,
                     colLabels=['指标', '得分', '数值 1', '数值 2'],
                     loc='center',
                     cellLoc='center',
                     colWidths=[0.15, 0.15, 0.35, 0.35])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.8)
    
    # 表头样式
    for i in range(4):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    
    # 交替行颜色
    for i in range(1, len(table_data) + 1):
        for j in range(4):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f8f8f8')
    
    ax3.set_title('技术指标明细', fontsize=14, fontweight='bold', pad=20)
    
    # 添加资金流和推荐信息
    textstr = f"""
┌─────────────────────────────────────┐
│  资金流分析                         │
├─────────────────────────────────────┤
│  主力净流入：{stock_info.get('main_net_inflow', 0):>12,.0f}万  │
│  主力占比：  {stock_info.get('main_ratio', 0):>12.2f}%  │
│  超大单占比：{stock_info.get('super_ratio', 0):>12.2f}%  │
├─────────────────────────────────────┤
│  推荐建议                           │
├─────────────────────────────────────┤
│  仓位：{stock_info.get('recommendation', {}).get('position', '-'):>20}  │
│  止盈：{stock_info.get('recommendation', {}).get('take_profit', '-'):>20}  │
│  止损：{stock_info.get('recommendation', {}).get('stop_loss', '-'):>20}  │
└─────────────────────────────────────┘
"""
    
    fig.text(0.98, 0.02, textstr, fontsize=9, verticalalignment='bottom', 
             horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='#FFF3CD', alpha=0.8, edgecolor='#FFC107'))
    
    plt.suptitle(f'{name} ({code}) 股票分析仪表盘', fontsize=16, fontweight='bold', y=0.995)
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"✅ 仪表盘已保存：{save_path}")
    
    plt.close()

def main():
    """主函数"""
    print("=" * 70)
    print(" " * 20 + "股票可视化系统 v3.0")
    print("=" * 70)
    
    # 生成示例数据
    print("\n📊 生成模拟 K 线数据...")
    df = generate_mock_data('002475', days=60)
    
    # 计算指标
    print("📈 计算技术指标...")
    indicators = calculate_indicators(df)
    
    # 示例股票信息
    stock_info = {
        'tech_score': 27.5,
        'fund_score': 20.0,
        'theme_score': 15.0,
        'fundamental_score': 10.5,
        'risk_score': 7.5,
        'total_score': 80.5,
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
    
    # 创建 KDJ 分析图表
    print("\n📊 生成 KDJ 分析图表...")
    create_kdj_chart(df, indicators, '002475', '立讯精密', 
                    save_path=f'{output_dir}/kdj_002475.png')
    
    # 创建仪表盘
    print("📊 生成分析仪表盘...")
    create_dashboard_chart(df, indicators, '002475', '立讯精密', stock_info,
                          save_path=f'{output_dir}/dashboard_002475.png')
    
    print("\n✅ 图表生成完成！")
    print(f"📁 保存位置：{output_dir}/")
    print("\n生成的文件:")
    for f in os.listdir(output_dir):
        print(f"  - {f}")

if __name__ == "__main__":
    main()
