#!/usr/bin/env python3
"""
选股系统 - 本地缓存数据测试
使用缓存数据测试完整流程，不依赖网络

鹏总专用 - 2026 年 3 月 27 日
"""

import os
import json
import sys
from datetime import datetime

sys.path.insert(0, '/home/admin/.openclaw/workspace')
sys.path.insert(0, '/home/admin/.openclaw/workspace/stocks')

from stocks.deep_push import PushNotifier


def test_with_cache_data():
    """使用缓存数据测试"""
    
    # 查找最新缓存数据
    cache_dir = '/home/admin/.openclaw/workspace/stocks/cache/auto_select'
    
    if not os.path.exists(cache_dir):
        print("❌ 缓存目录不存在")
        return
    
    # 查找最新的数据文件
    data_files = [f for f in os.listdir(cache_dir) if f.startswith('data_') and f.endswith('.json')]
    
    if not data_files:
        print("❌ 未找到缓存数据文件")
        print("\n💡 建议:")
        print("1. 先运行一次 auto_daily_push.py 获取数据")
        print("2. 等待网络恢复后重试")
        return
    
    # 排序取最新
    data_files.sort(reverse=True)
    latest_file = data_files[0]
    
    print(f"📂 使用缓存数据：{latest_file}\n")
    
    # 读取数据
    with open(os.path.join(cache_dir, latest_file), 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    main_force = data.get('main_force', [])
    sectors = data.get('sectors', [])
    
    print(f"📊 缓存数据概览:")
    print(f"   主力股票：{len(main_force)} 只")
    print(f"   板块数量：{len(sectors)} 个")
    print(f"   数据日期：{data.get('date', 'N/A')}")
    print()
    
    if len(main_force) < 50:
        print(f"⚠️ 缓存数据不足 ({len(main_force)} < 50)，无法测试")
        return
    
    # 验证数据质量
    valid_count = sum(1 for s in main_force if (s.get('f4001', 0) or 0) != 0)
    print(f"✅ 有效数据：{valid_count} 条")
    
    if valid_count < 30:
        print(f"⚠️ 有效数据不足 ({valid_count} < 30)，无法测试")
        return
    
    # 分析股票（简化版）
    print("\n🔍 分析股票...")
    buy_signals = []
    
    for i, stock in enumerate(main_force[:100], 1):
        code = stock.get('f12', '')
        name = stock.get('f14', '')
        
        if not code:
            continue
        
        # 快速评分
        score = 50.0
        main_net = stock.get('f4001', 0) or 0
        main_ratio = stock.get('f4002', 0) or 0
        change = stock.get('f3', 0) or 0
        
        # 主力评分
        if main_net > 100000000:
            score += 20
        elif main_net > 50000000:
            score += 15
        elif main_net > 0:
            score += 5
        
        if main_ratio > 10:
            score += 10
        elif main_ratio > 5:
            score += 5
        
        # 涨跌幅评分
        if 2 <= change <= 7:
            score += 15
        elif 0 < change < 2:
            score += 10
        
        if score >= 70:
            buy_signals.append({
                'code': code,
                'name': name,
                'score': score,
                'data': stock,
            })
        
        if i % 20 == 0:
            print(f"   已分析 {i}/{len(main_force[:100])} 只股票")
    
    # 排序
    buy_signals.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n✅ 发现 {len(buy_signals)} 个买入信号")
    
    if not buy_signals:
        print("⚠️ 无符合条件的股票，不推送")
        return
    
    # 推送 TOP 5
    top5 = buy_signals[:5]
    
    print(f"\n📱 准备推送 TOP 5 买入信号...\n")
    
    content = f"""## 🎯 选股信号推送 (缓存数据测试)

**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**数据来源**: 缓存数据 ({data.get('date', 'N/A')})

### 买入信号 TOP 5

"""
    
    for i, signal in enumerate(top5, 1):
        code = signal['code']
        name = signal['name']
        score = signal['score']
        stock_data = signal['data']
        
        price = stock_data.get('f2', 0) or 0
        change = stock_data.get('f3', 0) or 0
        main_net = (stock_data.get('f4001', 0) or 0) / 100000000
        main_ratio = stock_data.get('f4002', 0) or 0
        
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
*注：使用缓存数据测试*
"""
    
    # 推送
    notifier = PushNotifier('/home/admin/.openclaw/workspace/stocks/push_config.json')
    result = notifier.send_wecom('🎯 选股信号推送 (测试)', content, msg_type='markdown')
    
    if result:
        print("✅ 推送成功！请查看企业微信\n")
        print("📊 已推送股票:")
        for i, signal in enumerate(top5, 1):
            print(f"  {i}. {signal['name']}({signal['code']}) - 评分 {signal['score']:.1f}")
    else:
        print("❌ 推送失败\n")
    
    # 保存记录
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'cache_test',
        'signals': [
            {
                'code': s['code'],
                'name': s['name'],
                'score': s['score'],
            }
            for s in top5
        ],
    }
    
    history_file = os.path.join(cache_dir, 'push_history.json')
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
    
    print(f"\n📁 推送记录已保存")


if __name__ == "__main__":
    print("🧪 选股系统 - 本地缓存数据测试\n")
    print("="*60)
    test_with_cache_data()
    print("="*60)
    print("\n✅ 测试完成\n")
