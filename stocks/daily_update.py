#!/usr/bin/env python3
"""
每日行情数据更新脚本 - 使用Tushare API
自动追加最新交易日数据到历史文件

用法:
    python3 daily_update.py          # 更新最新交易日
    python3 daily_update.py --date 20260415  # 更新指定日期

记录:
    - Token: a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4
    - API: http://api.tushare.pro
    - 接口: daily (日线行情)
    - 凯文 2026-04-15 创建
"""
import requests
import json
import os
import sys
from datetime import datetime, timedelta

# ============== 配置 ==============
TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'
API_URL = 'http://api.tushare.pro'
DATA_DIR = '/home/admin/.openclaw/workspace/stocks/data_history_2022_2026'
# ==================================

def get_latest_trade_date():
    """获取最近交易日（简化版：用今天或前一工作日）"""
    today = datetime.now()
    
    # 如果是周末，用周五
    if today.weekday() == 5:  # 周六
        trade_date = today - timedelta(days=1)
    elif today.weekday() == 6:  # 周日
        trade_date = today - timedelta(days=2)
    else:
        trade_date = today
    
    # 如果是下午15:30前，用前一天（当日数据可能未更新）
    if today.hour < 16:
        trade_date = today - timedelta(days=1)
        if trade_date.weekday() == 5:
            trade_date = trade_date - timedelta(days=1)
        elif trade_date.weekday() == 6:
            trade_date = trade_date - timedelta(days=2)
    
    return trade_date.strftime('%Y%m%d')

def fetch_daily_quotes(trade_date):
    """从Tushare获取指定日期的全部股票行情"""
    print(f"获取 {trade_date} 行情数据...")
    
    payload = {
        'api_name': 'daily',
        'token': TOKEN,
        'params': {'trade_date': trade_date},
        'fields': ''
    }
    
    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        result = resp.json()
        
        if result.get('code') != 0:
            print(f"❌ API错误: {result.get('msg', '未知错误')}")
            return None
        
        data = result.get('data')
        if not data or 'items' not in data:
            print("❌ 无数据返回")
            return None
        
        items = data['items']
        print(f"✅ 获取到 {len(items)} 条数据")
        
        return items
    
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def update_history_files(items, trade_date):
    """将行情数据追加到历史文件"""
    print(f"\n更新历史文件...")
    
    updated = 0
    skipped = 0
    not_found = 0
    
    for item in items:
        # 解析数据 (字段顺序固定)
        ts_code = item[0]
        code = ts_code.split('.')[0]
        
        file_path = os.path.join(DATA_DIR, f"{code}.json")
        
        if not os.path.exists(file_path):
            not_found += 1
            continue
        
        try:
            with open(file_path, 'r') as f:
                hist = json.load(f)
            
            if 'items' not in hist:
                skipped += 1
                continue
            
            # 检查是否已有该日期数据
            dates = [it[1] for it in hist['items']]
            
            if trade_date in dates:
                skipped += 1
                continue
            
            # 追加新数据
            hist['items'].append(item)
            hist['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            hist['record_count'] = len(hist['items'])
            
            with open(file_path, 'w') as f:
                json.dump(hist, f)
            
            updated += 1
            
        except Exception as e:
            skipped += 1
    
    print(f"\n统计:")
    print(f"  ✅ 成功更新: {updated}股")
    print(f"  ⏭️ 已存在跳过: {skipped}股")
    print(f"  📄 文件不存在: {not_found}股")
    
    return updated

def verify_update(holdings=['002709', '600089', '603739', '600163']):
    """验证持仓股票数据"""
    print(f"\n验证持仓股票:")
    
    for code in holdings:
        file_path = os.path.join(DATA_DIR, f"{code}.json")
        
        if not os.path.exists(file_path):
            print(f"  {code}: 文件不存在")
            continue
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if 'items' in data:
            latest = data['items'][-1]
            print(f"  {code}: {latest[1]} ¥{latest[5]:.2f} ({latest[8]:.2f}%)")

def main():
    """主函数"""
    print("="*60)
    print("每日行情数据更新 - Tushare")
    print("="*60)
    print(f"时间: {datetime.now()}")
    
    # 确定更新日期
    if len(sys.argv) > 2 and sys.argv[1] == '--date':
        trade_date = sys.argv[2]
    else:
        trade_date = get_latest_trade_date()
    
    print(f"目标日期: {trade_date}")
    
    # 获取数据
    items = fetch_daily_quotes(trade_date)
    
    if not items:
        print("❌ 更新失败")
        return
    
    # 更新文件
    updated = update_history_files(items, trade_date)
    
    # 验证
    verify_update()
    
    print(f"\n✅ 完成: {datetime.now()}")
    
    # 记录操作方式
    print("\n💡 Tushare操作记录:")
    print("  脚本: daily_update.py")
    print("  Token: a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4")
    print("  API: http://api.tushare.pro")
    print("  接口: daily (日线行情)")
    print("  参数: trade_date='YYYYMMDD'")

if __name__ == '__main__':
    main()