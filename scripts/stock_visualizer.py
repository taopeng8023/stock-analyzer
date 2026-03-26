#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票可视化系统
生成 K 线图 + 技术指标图（MACD/KDJ/RSI/成交量）
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import mplfinance as mpf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def generate_mock_data(code: str, days: int = 60) -> pd.DataFrame:
    """
    生成模拟 K 线数据（实际使用时替换为真实 API 数据）
    """
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # 生成股价数据
    base_price = 50.0
    returns = np.random.randn(days) * 0.03  # 3% 日波动
    close = base_price * (1 + returns).cumprod()
    
    # 生成 OHLC
    high = close * (1 + np.random.rand(days) * 0.02)
    low = close * (1 - np.random.rand(days) * 0.02)
    open_price = low + (high - low) * np.random.rand(days)
    
    # 成交量
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

def calculate_macd(df: pd.DataFrame) -> tuple:
    """计算 MACD 指标"""
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    dif = exp1 - exp2
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_bar = (dif - dea) * 2
    return dif, dea, macd_bar

def calculate_kdj(df: pd.DataFrame) -> tuple:
    """计算 KDJ 指标"""
    low_min = df['Low'].rolling(window=9).min()
    high_max = df['High'].rolling(window=9).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    
    return k, d, j

def calculate_rsi(df: pd.DataFrame, periods: list = [6, 12, 24]) -> dict:
    """计算 RSI 指标"""
    rsi_dict = {}
    for period in periods:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_dict[f'RSI{period}'] = rsi
    return rsi_dict

def calculate_ma(df: pd.DataFrame) -> dict:
    """计算均线"""
    ma_dict = {}
    for period in [5, 10, 20, 60]:
        ma_dict[f'MA{period}'] = df['Close'].rolling(window=period).mean()
    return ma_dict

def plot_kdj(df: pd.DataFrame, ax):
    """绘制 KDJ 指标"""
    k, d, j = calculate_kdj(df)
    
    ax.plot(k.index, k, label='K', color='yellow', linewidth=1)
    ax.plot(d.index, d, label='D', color='blue', linewidth=1)
    ax.plot(j.index, j, label='J', color='magenta', linewidth=1)
    
    ax.axhline(80, color='red', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.axhline(20, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.fill_between(k.index, 20, 80, alpha=0.1, color='gray')
    
    ax.set_ylabel('KDJ')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 100)

def plot_macd(df: pd.DataFrame, ax):
    """绘制 MACD 指标"""
    dif, dea, macd_bar = calculate_macd(df)
    
    # 绘制柱状图
    colors = ['red' if val > 0 else 'green' for val in macd_bar]
    ax.bar(dif.index, macd_bar, color=colors, alpha=0.5, width=1)
    
    # 绘制 DIF 和 DEA
    ax.plot(dif.index, dif, label='DIF', color='white', linewidth=1)
    ax.plot(dea.index, dea, label='DEA', color='yellow', linewidth=1)
    
    ax.axhline(0, color='gray', linestyle='-', linewidth=0.5)
    ax.set_ylabel('MACD')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)

def plot_rsi(df: pd.DataFrame, ax):
    """绘制 RSI 指标"""
    rsi_dict = calculate_rsi(df)
    
    colors = {'RSI6': 'white', 'RSI12': 'yellow', 'RSI24': 'blue'}
    for name, rsi in rsi_dict.items():
        ax.plot(rsi.index, rsi, label=name, color=colors.get(name, 'gray'), linewidth=1)
    
    ax.axhline(70, color='red', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.axhline(30, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.fill_between(rsi.index, 30, 70, alpha=0.1, color='gray')
    
    ax.set_ylabel('RSI')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 100)

def plot_volume(df: pd.DataFrame, ax, macd_bar):
    """绘制成交量"""
    colors = ['red' if df.loc[idx, 'Close'] >= df.loc[idx, 'Open'] else 'green' 
              for idx in df.index]
    
    ax.bar(df.index, df['Volume'], color=colors, alpha=0.5, width=1)
    ax.set_ylabel('成交量')
    ax.grid(True, alpha=0.3)

def create_kdj_chart(df: pd.DataFrame, code: str, name: str, save_path: str = None):
    """创建 KDJ 分析图表"""
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.1)
    
    # K 线图
    ax0 = fig.add_subplot(gs[0, 0])
    mpf.plot(df, type='candle', ax=ax0, volume=False, 
             style='charles', show_nontrading=False)
    ax0.set_title(f'{name} ({code}) K 线图', fontsize=14, fontweight='bold')
    
    # KDJ 指标
    ax1 = fig.add_subplot(gs[1, 0], sharex=ax0)
    plot_kdj(df, ax1)
    
    # MACD 指标
    ax2 = fig.add_subplot(gs[2, 0], sharex=ax0)
    plot_macd(df, ax2)
    
    # RSI 指标
    ax3 = fig.add_subplot(gs[3, 0], sharex=ax0)
    plot_rsi(df, ax3)
    
    # 设置 x 轴
    plt.setp(ax0.get_xticklabels(), visible=False)
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), visible=False)
    
    plt.suptitle(f'{name} ({code}) 技术分析', fontsize=16, fontweight='bold', y=0.995)
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"✅ 图表已保存：{save_path}")
    
    plt.show()

def create_multi_stock_chart(stocks_data: dict, save_path: str = None):
    """
    创建多股票对比图表
    stocks_data: {code: {'name': str, 'df': DataFrame}, ...}
    """
    n_stocks = len(stocks_data)
    fig = plt.figure(figsize=(16, 4 * n_stocks))
    
    for i, (code, data) in enumerate(stocks_data.items()):
        df = data['df']
        name = data['name']
        
        gs = GridSpec(2, 1, height_ratios=[2, 1], hspace=0.1)
        
        # K 线图
        ax0 = fig.add_subplot(gs[0, i])
        mpf.plot(df, type='candle', ax=ax0, volume=False,
                 style='charles', show_nontrading=False)
        ax0.set_title(f'{name} ({code})', fontsize=12, fontweight='bold')
        
        # 成交量 + MACD
        ax1 = fig.add_subplot(gs[1, i], sharex=ax0)
        dif, dea, macd_bar = calculate_macd(df)
        colors = ['red' if val > 0 else 'green' for val in macd_bar]
        ax1.bar(df.index, macd_bar, color=colors, alpha=0.5, width=1)
        ax1.plot(dif.index, dif, label='DIF', color='white', linewidth=1)
        ax1.plot(dea.index, dea, label='DEA', color='yellow', linewidth=1)
        ax1.axhline(0, color='gray', linestyle='-', linewidth=0.5)
        ax1.set_ylabel('MACD')
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        plt.setp(ax0.get_xticklabels(), visible=False)
    
    plt.suptitle('多股票技术对比', fontsize=16, fontweight='bold')
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"✅ 图表已保存：{save_path}")
    
    plt.show()

def create_dashboard_chart(df: pd.DataFrame, code: str, name: str, 
                          stock_info: dict, save_path: str = None):
    """
    创建股票分析仪表盘
    stock_info: 包含评分、资金流等信息
    """
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 2, height_ratios=[2, 1, 1], hspace=0.3, wspace=0.25)
    
    # 1. K 线图 + 均线
    ax0 = fig.add_subplot(gs[0, :])
    ma_dict = calculate_ma(df)
    
    mpf.plot(df, type='candle', ax=ax0, volume=False,
             style='charles', show_nontrading=False,
             addplot=[mpf.make_addplot(ma, label=f'MA{p}') 
                     for p, ma in ma_dict.items()])
    ax0.set_title(f'{name} ({code}) K 线与均线', fontsize=14, fontweight='bold')
    ax0.legend(loc='upper left', fontsize=8)
    
    # 2. 成交量
    ax1 = fig.add_subplot(gs[1, 0])
    colors = ['red' if df.loc[idx, 'Close'] >= df.loc[idx, 'Open'] else 'green' 
              for idx in df.index]
    ax1.bar(df.index, df['Volume'], color=colors, alpha=0.5, width=1)
    ax1.set_title('成交量', fontsize=12, fontweight='bold')
    ax1.set_ylabel('成交量')
    ax1.grid(True, alpha=0.3)
    
    # 3. 评分雷达图
    ax2 = fig.add_subplot(gs[1, 1], projection='polar')
    categories = ['技术面', '资金面', '题材面', '基本面', '风险面']
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
    
    ax2.plot(angles, values, 'o-', linewidth=2, color='blue')
    ax2.fill(angles, values, alpha=0.25, color='blue')
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(categories, fontsize=10)
    ax2.set_ylim(0, 100)
    ax2.set_title(f'综合评分：{stock_info.get("total_score", 0):.1f}', 
                  fontsize=12, fontweight='bold', pad=20)
    ax2.grid(True)
    
    # 4. 技术指标表
    ax3 = fig.add_subplot(gs[2, :])
    ax3.axis('off')
    
    # 创建表格数据
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
    table.set_fontsize(10)
    table.scale(1.2, 1.5)
    
    # 表头样式
    for i in range(4):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    
    # 交替行颜色
    for i in range(1, len(table_data) + 1):
        for j in range(4):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f2f2f2')
    
    ax3.set_title('技术指标明细', fontsize=14, fontweight='bold', pad=20)
    
    # 添加资金流信息
    textstr = f"""
    资金流分析:
    主力净流入：{stock_info.get('main_net_inflow', 0):,.0f}万
    主力占比：{stock_info.get('main_ratio', 0):.2f}%
    超大单占比：{stock_info.get('super_ratio', 0):.2f}%
    
    推荐建议:
    仓位：{stock_info.get('recommendation', {}).get('position', '-')}
    止盈：{stock_info.get('recommendation', {}).get('take_profit', '-')}
    止损：{stock_info.get('recommendation', {}).get('stop_loss', '-')}
    """
    
    fig.text(0.98, 0.02, textstr, fontsize=9, verticalalignment='bottom', 
             horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle(f'{name} ({code}) 股票分析仪表盘', fontsize=16, fontweight='bold', y=0.995)
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"✅ 仪表盘已保存：{save_path}")
    
    plt.show()

def main():
    """主函数 - 演示"""
    print("=" * 70)
    print(" " * 20 + "股票可视化系统")
    print("=" * 70)
    
    # 生成示例数据
    print("\n生成模拟 K 线数据...")
    df = generate_mock_data('002475', days=60)
    
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
    
    # 创建 KDJ 分析图表
    print("\n生成 KDJ 分析图表...")
    create_kdj_chart(df, '002475', '立讯精密', 
                    save_path='/home/admin/.openclaw/workspace/data/charts/kdj_002475.png')
    
    # 创建仪表盘
    print("\n生成分析仪表盘...")
    create_dashboard_chart(df, '002475', '立讯精密', stock_info,
                          save_path='/home/admin/.openclaw/workspace/data/charts/dashboard_002475.png')
    
    print("\n✅ 图表生成完成！")
    print("📁 保存位置：/home/admin/.openclaw/workspace/data/charts/")

if __name__ == "__main__":
    # 检查依赖
    try:
        import mplfinance
        print("✅ mplfinance 已安装")
    except ImportError:
        print("❌ 请安装 mplfinance: pip install mplfinance")
        exit(1)
    
    main()
