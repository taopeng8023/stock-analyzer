#!/usr/bin/env python3
"""
处理指定股票列表 - v8.0 工作流

用法: python3 process_custom_stocks.py
"""
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/stocks')

from workflow_v8_strict import AnalysisLayer, AnalysisInput, StockData
from datetime import datetime
import requests
import re

# 用户指定的股票代码
CUSTOM_STOCKS = [
    '002594', '002506', '002565', '600143', '600580', '002218', '000572', '601088',
    '300085', '300345', '600989', '601985', '000983', '002112', '000592', '600938',
    '001258', '603529', '601872', '601857', '600111', '002896', '002812', '002575',
    '000422', '300207', '600481', '600376', '601615', '688411', '600026', '002428',
    '000333', '002309', '300383', '603105', '603817', '603803', '600188', '600176',
    '003035', '000933', '002648', '600905', '000831', '300113', '600792', '601908',
    '000688', '600844'
]

def fetch_stock_data(codes: list) -> list:
    """从腾讯财经获取指定股票数据"""
    print("\n" + "="*80)
    print("📡 获取指定股票数据...")
    print("="*80)
    
    stocks = []
    
    # 批量获取，每批 50 个
    batch_size = 50
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]
        
        # 添加市场前缀
        stock_codes = []
        for code in batch:
            if code.startswith('6') or code.startswith('5'):
                stock_codes.append(f'sh{code}')
            else:
                stock_codes.append(f'sz{code}')
        
        url = f"http://qt.gtimg.cn/q={','.join(stock_codes)}"
        
        try:
            resp = requests.get(url, timeout=10)
            resp.encoding = 'gbk'  # 腾讯财经返回 GBK 编码
            lines = resp.text.strip().split('\n')
            
            for line in lines:
                if '=' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        code = parts[0].split('~')[0].replace('v_', '')
                        data = parts[1].strip('"').split('~')
                        
                        if len(data) >= 50:
                            try:
                                # 腾讯财经数据格式：~ 分隔
                                # data[3]= 价格，data[32]= 涨跌幅%，data[6]= 成交量 (手), data[37]= 成交额 (元)
                                price = float(data[3]) if data[3] else 0
                                change_pct = float(data[32]) if data[32] else 0
                                volume = int(float(data[6]) * 100) if data[6] else 0  # 手→股
                                turnover = float(data[37]) if data[37] else 0  # 成交额 (元)
                                
                                stock = StockData(
                                    code=code[2:],  # 去掉 sh/sz 前缀
                                    name=data[1],
                                    price=price,
                                    change_pct=change_pct,
                                    volume=volume,
                                    turnover=turnover,
                                    source='custom_list',
                                    crawl_time=datetime.now().isoformat()
                                )
                                stocks.append(stock)
                                print(f"  ✅ {code} {data[1]} ¥{stock.price} {stock.change_pct:+.2f}%")
                            except (ValueError, IndexError) as e:
                                print(f"  ⚠️ {code} 解析失败：{e}")
            
            print(f"\n  批次 {i//batch_size + 1}: 获取 {len([l for l in lines if '=' in l])} 只")
            
        except Exception as e:
            print(f"  ❌ 批次 {i//batch_size + 1} 失败：{e}")
    
    print(f"\n✅ 共获取 {len(stocks)} 只股票数据")
    return stocks


def main():
    print("="*80)
    print("🚀 v8.0-Financial-Enhanced 定制股票分析")
    print("="*80)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"股票数量：{len(CUSTOM_STOCKS)}")
    
    # Layer 1: 数据获取
    stocks = fetch_stock_data(CUSTOM_STOCKS)
    
    if not stocks:
        print("\n❌ 未获取到任何股票数据")
        return
    
    # Layer 2: 分析决策
    layer2 = AnalysisLayer()
    
    analysis_input = AnalysisInput(
        stocks=stocks,
        data_sources=['custom_list'],
        total_count=len(stocks),
        fetch_time=datetime.now().isoformat()
    )
    
    output = layer2.analyze(analysis_input, len(stocks))
    
    # 显示结果
    print("\n" + "="*80)
    print("📊 分析结果 - 按评分排序")
    print("="*80 + "\n")
    
    # 分组显示
    groups = {'强烈推荐': [], '推荐': [], '关注': [], '观望': []}
    for stock in output.stocks:
        rating = stock.get('rating', '观望')
        groups[rating].append(stock)
    
    for rating in ['强烈推荐', '推荐', '关注', '观望']:
        group = groups[rating]
        if not group:
            continue
        
        rating_icon = {'强烈推荐': '⭐⭐⭐', '推荐': '⭐⭐', '关注': '⭐', '观望': '⭕'}.get(rating, '')
        print(f"\n━━ {rating_icon} {rating} ({len(group)}) ━━\n")
        
        for i, stock in enumerate(group, 1):
            code = stock.get('code', 'N/A')
            name = stock.get('name', 'N/A')
            price = stock.get('price', 0)
            change = stock.get('change_pct', 0)
            turnover = stock.get('turnover', 0) / 100000000
            score = stock.get('score', 0)
            
            if change > 2:
                icon = '📗'
            elif change < -2:
                icon = '📉'
            elif change > 0:
                icon = '📈'
            else:
                icon = '📉'
            
            print(f"{i:2}. {icon} {name}({code})")
            print(f"    ¥{price:.2f} {change:+.2f}% 成交{turnover:.2f}亿 评分:{score}")
            print(f"    止盈¥{stock.get('stop_profit', 0):.2f} 止损¥{stock.get('stop_loss', 0):.2f}")
            print(f"    {stock.get('tags', '')}")
    
    print("\n" + "="*80)
    print("✅ 分析完成")
    print("="*80)
    
    # Layer 3: 推送
    print("\n📤 正在推送到企业微信...")
    from workflow_v8_strict import PushLayer, PushInput
    
    push_layer = PushLayer()
    push_input = PushInput(
        stocks=output.stocks[:20],  # 推送 Top 20
        top_n=20,
        workflow_version='v8.0-Custom-List',
        execution_time=datetime.now().isoformat()
    )
    
    push_output = push_layer.push(push_input)
    
    if push_output.status == 'success':
        print("\n✅ 推送成功！")
    else:
        print(f"\n❌ 推送失败：{push_output.error_message}")


if __name__ == '__main__':
    main()
