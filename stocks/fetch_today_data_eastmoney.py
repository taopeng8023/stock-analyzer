#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用东方财富 API 获取今日收盘后交易数据

数据源：东方财富（免费，无需 Token）
接口：http://push2.eastmoney.com/api/qt/stock/get

优势:
- 完全免费，无需注册
- 数据实时
- 覆盖全市场 A 股
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

# 配置
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
LOG_DIR = Path('/home/admin/.openclaw/workspace/stocks/logs')

# 今日日期
TODAY = datetime.now().strftime('%Y%m%d')

print("=" * 80)
print("东方财富 今日数据获取")
print("=" * 80)
print(f"数据源：东方财富 (免费)")
print(f"目标日期：{TODAY}")
print(f"数据目录：{DATA_DIR}")
print()

# 东方财富 API
EASTMONEY_API = 'http://push2.eastmoney.com/api/qt/stock/get'

# 获取 A 股市场列表
def get_market_list():
    """获取 A 股市场股票列表"""
    # 沪市 A 股
    sh_stocks = []
    for i in range(0, 200):
        url = f'http://nufm.dfcfw.com/EM_Fund2099/QF_Stock2099/JSPI/GetStockList?cb=jQuery&sort=f&sr=-1&st=code&s=600000&ps=5000&pz=5000&pn={i}&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&dect=1&wzm2=1&fid=f12&fs=m:1&fields=f12,f13,f14'
        try:
            resp = requests.get(url, timeout=30)
            text = resp.text
            if 'var' in text:
                # 解析 JSONP
                json_str = text.split('=')[1].strip()
                data = json.loads(json_str)
                if data and 'data' in data:
                    for item in data['data']:
                        sh_stocks.append({
                            'code': item[0],
                            'name': item[2]
                        })
        except:
            break
    
    # 深市 A 股
    sz_stocks = []
    for i in range(0, 200):
        url = f'http://nufm.dfcfw.com/EM_Fund2099/QF_Stock2099/JSPI/GetStockList?cb=jQuery&sort=f&sr=-1&st=code&s=000001&ps=5000&pz=5000&pn={i}&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&dect=1&wzm2=1&fid=f12&fs=m:0&fields=f12,f13,f14'
        try:
            resp = requests.get(url, timeout=30)
            text = resp.text
            if 'var' in text:
                json_str = text.split('=')[1].strip()
                data = json.loads(json_str)
                if data and 'data' in data:
                    for item in data['data']:
                        sz_stocks.append({
                            'code': item[0],
                            'name': item[2]
                        })
        except:
            break
    
    return sh_stocks + sz_stocks


# 获取单只股票行情
def get_stock_quote(code, market):
    """
    获取单只股票行情
    
    Args:
        code: 股票代码
        market: 市场 (0=深市，1=沪市)
    
    Returns:
        dict: 行情数据
    """
    url = f'http://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f84,f85,f86,f87,f117,f118,f119,f120,f121,f122,f123,f124,f125,f126,f127,f128,f129,f130,f131,f132,f133,f134,f135,f136,f137,f138,f139,f140,f141,f142,f143,f144,f145,f146,f147,f148,f149,f150,f151,f152,f153,f154,f155,f156,f157,f158,f159,f160,f161,f162,f163,f164,f165,f166,f167,f168,f169,f170,f171,f172,f173,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f193,f194,f195,f196,f197,f198,f199,f200,f201,f202,f203,f204,f205,f206,f207,f208,f209,f210,f211,f212,f213,f214,f215,f216,f217,f218,f219,f220,f221,f222,f223,f224,f225,f226,f227,f228,f229,f230,f231,f232,f233,f234,f235,f236,f237,f238,f239,f240,f241,f242,f243,f244,f245,f246,f247,f248,f249,f250,f251,f252,f253,f254,f255,f256,f257,f258,f259,f260,f261,f262,f263,f264,f265,f266,f267,f268,f269,f270,f271,f272,f273,f274,f275,f276,f277,f278,f279,f280,f281,f282,f283,f284,f285,f286,f287,f288,f289,f290,f291,f292,f293,f294,f295,f296,f297,f298,f299,f300,f301,f302,f303,f304,f305,f306,f307,f308,f309,f310,f311,f312,f313,f314,f315,f316,f317,f318,f319,f320,f321,f322,f323,f324,f325,f326,f327,f328,f329,f330,f331,f332,f333,f334,f335,f336,f337,f338,f339,f340,f341,f342,f343,f344,f345,f346,f347,f348,f349,f350,f351,f352,f353,f354,f355,f356,f357,f358,f359,f360,f361,f362,f363,f364,f365,f366,f367,f368,f369,f370,f371,f372,f373,f374,f375,f376,f377,f378,f379,f380,f381,f382,f383,f384,f385,f386,f387,f388,f389,f390,f391,f392,f393,f394,f395,f396,f397,f398,f399,f400,f401,f402,f403,f404,f405,f406,f407,f408,f409,f410,f411,f412,f413,f414,f415,f416,f417,f418,f419,f420,f421,f422,f423,f424,f425,f426,f427,f428,f429,f430,f431,f432,f433,f434,f435,f436,f437,f438,f439,f440,f441,f442,f443,f444,f445,f446,f447,f448,f449,f450,f451,f452,f453,f454,f455,f456,f457,f458,f459,f460,f461,f462,f463,f464,f465,f466,f467,f468,f469,f470,f471,f472,f473,f474,f475,f476,f477,f478,f479,f480,f481,f482,f483,f484,f485,f486,f487,f488,f489,f490,f491,f492,f493,f494,f495,f496,f497,f498,f499'
    
    try:
        resp = requests.get(url, timeout=10)
        result = resp.json()
        
        if result.get('data'):
            data = result['data']
            
            # 解析行情数据
            return {
                '代码': data.get('f12', ''),
                '名称': data.get('f14', ''),
                '最新价': float(data.get('f43', 0)) / 100,
                '开盘': float(data.get('f46', 0)) / 100,
                '收盘': float(data.get('f43', 0)) / 100,
                '最高': float(data.get('f44', 0)) / 100,
                '最低': float(data.get('f45', 0)) / 100,
                '成交量': int(data.get('f47', 0)),
                '成交额': float(data.get('f48', 0)),
                '涨跌幅': float(data.get('f170', 0)) / 100,
                '涨额': float(data.get('f169', 0)) / 100,
                '换手率': float(data.get('f168', 0)),
                '量比': float(data.get('f167', 0)),
                '市盈率': float(data.get('f164', 0)),
                '市净率': float(data.get('f165', 0)),
            }
        
        return None
        
    except Exception as e:
        return None


def main():
    start_time = time.time()
    
    # 获取股票列表
    print("[1/3] 获取 A 股股票列表...")
    stocks = get_market_list()
    
    if not stocks:
        print("❌ 获取股票列表失败")
        return
    
    print(f"   股票总数：{len(stocks)} 只")
    
    # 获取今日行情
    print(f"\n[2/3] 获取 {TODAY} 行情数据...")
    print("   预计耗时：10-20 分钟")
    print()
    
    success = 0
    exists = 0
    fail = 0
    
    for i, stock in enumerate(stocks):
        code = stock['code']
        name = stock['name']
        symbol = code
        filepath = DATA_DIR / f'{symbol}.json'
        
        # 判断市场
        if code.startswith('6'):
            market = 1  # 沪市
        else:
            market = 0  # 深市
        
        # 获取行情
        quote = get_stock_quote(code, market)
        
        if quote:
            # 构建数据
            new_data = {
                '日期': TODAY,
                '开盘': quote['开盘'],
                '收盘': quote['收盘'],
                '最高': quote['最高'],
                '最低': quote['最低'],
                '成交量': quote['成交量'],
                '成交额': quote['成交额'],
                '涨跌幅': quote['涨跌幅']
            }
            
            # 读取现有数据
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                # 检查是否已存在
                existing_dates = [d['日期'] for d in existing_data]
                if new_data['日期'] in existing_dates:
                    exists += 1
                    continue
                
                # 追加数据
                existing_data.append(new_data)
                existing_data.sort(key=lambda x: x['日期'])
                
                # 保存
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
            else:
                # 新文件
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump([new_data], f, ensure_ascii=False, indent=2)
            
            success += 1
        else:
            fail += 1
        
        # 进度
        if (i + 1) % 500 == 0:
            elapsed = time.time() - start_time
            print(f"   进度：{i+1}/{len(stocks)} (成功:{success} 已存在:{exists} 失败:{fail}) 耗时:{elapsed:.1f}s")
        
        # 频率控制
        time.sleep(0.1)
    
    elapsed = time.time() - start_time
    
    # 完成统计
    print()
    print("=" * 80)
    print("执行完成")
    print("=" * 80)
    print(f"   股票总数：{len(stocks)} 只")
    print(f"   成功更新：{success} 只")
    print(f"   已存在：{exists} 只")
    print(f"   失败：{fail} 只")
    print(f"   总耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print("=" * 80)
    
    # 保存报告
    report = {
        'date': TODAY,
        'time': datetime.now().isoformat(),
        'data_source': '东方财富',
        'summary': {
            'total': len(stocks),
            'success': success,
            'exists': exists,
            'fail': fail
        },
        'elapsed': elapsed
    }
    
    report_file = LOG_DIR / f'update_report_{TODAY}_eastmoney.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 报告已保存：{report_file}")
    print()
    print("✅ 今日数据获取完成！")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ 执行异常：{e}")
        import traceback
        traceback.print_exc()
