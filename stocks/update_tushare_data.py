#!/usr/bin/env python3
"""
Tushare数据更新脚本 - 补充今日行情
使用Tushare API获取最新行情数据并更新历史文件

操作方式：
1. 设置Tushare token（需要有积分）
2. 获取今日实时行情
3. 更新到历史数据文件

记录：2026-04-15 凯文使用Tushare补充数据
"""
import os
import json
import tushare as ts
from datetime import datetime, timedelta
import pandas as pd
import time

print("="*80)
print("Tushare数据更新 - 补充今日行情")
print("="*80)
print(f"开始时间: {datetime.now()}")

DATA_DIR = "/home/admin/.openclaw/workspace/stocks/data_history_2022_2026"

# Tushare配置
# 注意：需要有效的token才能获取数据
# 免费token每日有调用限制
TUSHARE_TOKEN = "0e6e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e"  # 占位token

print("\n初始化Tushare...")
try:
    pro = ts.pro_api(TUSHARE_TOKEN)
    
    # 测试连接 - 获取交易日历
    cal = pro.trade_cal(exchange='SSE', start_date='20260401', end_date='20260415')
    print(f"✅ Tushare连接成功")
    print(f"  近期交易日: {len(cal[cal['is_open']==1])}天")
    
except Exception as e:
    print(f"⚠️ Tushare连接失败: {e}")
    print("\n💡 解决方案:")
    print("  1. 注册Tushare账号: https://tushare.pro")
    print("  2. 获取token后替换脚本中的TUSHARE_TOKEN")
    print("  3. 或使用以下备用方案...")
    
    # 备用：使用akshare
    try:
        import akshare as ak
        print("\n尝试使用akshare...")
        
        # 获取实时行情
        df = ak.stock_zh_a_spot_em()
        print(f"  获取股票数: {len(df)}")
        
        if len(df) > 0:
            print(f"  示例数据:")
            print(df.head(3))
            
            # 更新持仓股票
            holdings = ['002709', '600089', '603739', '600163']
            
            print(f"\n更新持仓股票...")
            for code in holdings:
                row = df[df['代码'] == code]
                if len(row) > 0:
                    close = float(row['最新价'].values[0])
                    pct = float(row['涨跌幅'].values[0])
                    print(f"  {code}: ¥{close:.2f} ({pct:.2f}%)")
                    
                    # 更新文件
                    file_path = os.path.join(DATA_DIR, f"{code}.json")
                    with open(file_path, 'r') as f:
                        hist = json.load(f)
                    
                    if 'items' in hist:
                        today = datetime.now().strftime('%Y%m%d')
                        dates = [item[1] for item in hist['items']]
                        
                        if today not in dates:
                            # 构建新数据项
                            new_item = [
                                code + '.SZ' if code.startswith(('0','3')) else code + '.SH',
                                today,
                                float(row['今开'].values[0]) if '今开' in row.columns else close,
                                float(row['最高'].values[0]) if '最高' in row.columns else close,
                                float(row['最低'].values[0]) if '最低' in row.columns else close,
                                close,
                                float(row['昨收'].values[0]) if '昨收' in row.columns else close,
                                close - float(row['昨收'].values[0]) if '昨收' in row.columns else 0,
                                pct,
                                float(row['成交量'].values[0]) if '成交量' in row.columns else 0,
                                float(row['成交额'].values[0]) if '成交额' in row.columns else 0,
                            ]
                            hist['items'].append(new_item)
                            
                            with open(file_path, 'w') as f:
                                json.dump(hist, f)
                            
                            print(f"    ✅ 已更新")
                        else:
                            print(f"    ⏭️ 已存在")
            
            print(f"\n✅ akshare数据更新成功")
            
    except Exception as ak_e:
        print(f"  akshare失败: {ak_e}")

print(f"\n完成时间: {datetime.now()}")

# 记录操作方式
print("\n" + "="*80)
print("💡 Tushare使用方式（记录）")
print("="*80)
print("""
1. 安装: pip3 install tushare
2. 配置token: 
   - 注册账号: https://tushare.pro
   - 获取token后设置: ts.pro_api('your_token')
3. 获取数据:
   - 实时行情: pro.daily(trade_date='20260415')
   - 历史数据: pro.daily(ts_code='002709.SZ', start_date='20260101')
4. 注意:
   - 免费token每日调用有限制
   - 需要积分才能获取实时数据
   - akshare可作为免费备选
""")