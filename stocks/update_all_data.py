#!/usr/bin/env python3
"""全量数据更新 - 并行获取行情/资金流/板块涨幅"""
import json, requests, time, sys
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_DIR = Path("data")
HISTORY_DIR = Path("data_history_2022_2026")
DATA_DIR.mkdir(exist_ok=True)

today = datetime.now()
today_str = today.strftime("%Y%m%d")
yesterday = today - timedelta(days=1)
if today.weekday() == 0:  # Monday
    yesterday = today - timedelta(days=3)
elif today.weekday() == 6:  # Sunday
    yesterday = today - timedelta(days=2)
yesterday_str = yesterday.strftime("%Y%m%d")

# ============ 1. 行情数据更新 ============
def update_quotes():
    """更新全市场行情数据"""
    print("="*60)
    print("📊 [1/4] 更新全市场行情数据")
    print("="*60)
    
    token = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'
    api_url = 'http://api.tushare.pro'
    
    # 获取交易日历
    cal = requests.post(api_url, json={
        'api_name': 'trade_cal',
        'params': {'exchange': 'SSE', 'start_date': yesterday_str, 'end_date': today_str},
        'token': token
    }, timeout=10).json()
    
    trade_dates = []
    if cal.get('data') and cal['data'].get('items'):
        fields = cal['data']['fields']
        di = fields.index('cal_date') if 'cal_date' in fields else 0
        for row in cal['data']['items']:
            if row[fields.index('is_open') if 'is_open' in fields else 1] == 1:
                trade_dates.append(row[di])
    
    if not trade_dates:
        print("  ❌ 无交易日")
        return False
    
    trade_date = trade_dates[-1]
    print(f"  最新交易日：{trade_date}")
    
    # 获取日线数据
    print(f"  获取 {trade_date} 行情...")
    resp = requests.post(api_url, json={
        'api_name': 'daily',
        'params': {'trade_date': trade_date},
        'token': token
    }, timeout=60)
    data = resp.json()
    
    if not data.get('data') or not data['data'].get('items'):
        print(f"  ❌ 获取失败：{data.get('msg', 'unknown')}")
        return False
    
    items = data['data']['items']
    fields = data['data']['fields']
    
    ti = fields.index('ts_code')
    ci = fields.index('close') if 'close' in fields else 4
    oi = fields.index('open') if 'open' in fields else 1
    hi = fields.index('high') if 'high' in fields else 2
    li = fields.index('low') if 'low' in fields else 3
    vi = fields.index('vol') if 'vol' in fields else 6
    
    print(f"  ✅ 获取 {len(items)} 只股票")
    
    updated = 0
    for item in items:
        code = item[ti].split('.')[0]
        fpath = HISTORY_DIR / f"{code}.json"
        
        new_row = [trade_date, item[oi], item[hi], item[li], item[ci], item[vi]]
        
        if fpath.exists():
            with open(fpath) as f:
                stock = json.load(f)
            # 检查是否已存在
            existing_dates = [r[0] for r in stock['items']]
            if trade_date in existing_dates:
                # 更新
                idx = existing_dates.index(trade_date)
                stock['items'][idx] = new_row
            else:
                stock['items'].append(new_row)
            with open(fpath, 'w') as f:
                json.dump(stock, f)
            updated += 1
        else:
            stock = {
                'code': code,
                'fields': ['trade_date', 'open', 'high', 'low', 'close', 'vol'],
                'items': [new_row]
            }
            with open(fpath, 'w') as f:
                json.dump(stock, f)
            updated += 1
    
    print(f"  ✅ 行情更新完成：{updated} 只股票")
    return True

# ============ 2. 资金流数据 ============
def update_zjlx():
    """更新主力资金流排行"""
    print("\n" + "="*60)
    print("💰 [2/4] 更新主力资金流信息")
    print("="*60)
    
    api_url = "http://push2.eastmoney.com/api/qt/clist/get"
    
    # 主板
    params = {
        'pn': 1, 'pz': 100, 'po': 1, 'np': 1,
        'ut': 'bd1d9ddb04089700cf3c27f2672e909d',
        'fltt': 2, 'invt': 2,
        'fid': 'f62',
        'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
        'fields': 'f12,f14,f2,f3,f5,f6,f62,f63,f103,f104',
        '_': int(time.time()*1000)
    }
    
    try:
        resp = requests.get(api_url, params=params, timeout=15)
        data = resp.json()
        
        if not data.get('data') or not data['data'].get('diff'):
            print("  ❌ API 返回空数据")
            return False
        
        stocks = data['data']['diff']
        print(f"  ✅ 获取 {len(stocks)} 只")
        
        ranking = []
        for i, s in enumerate(stocks[:50], 1):
            def parse_num(v):
                try: return float(v)
                except: return 0
            ranking.append({
                '序号': i,
                '代码': s.get('f12', ''),
                '名称': s.get('f14', ''),
                '最新价': parse_num(s.get('f2', 0)),
                '涨跌幅': parse_num(s.get('f3', 0)),
                '主力净流入_净额': parse_num(s.get('f62', 0)),
                '主力净流入_净占比': parse_num(s.get('f63', 0)),
                '超大单净流入_净额': parse_num(s.get('f103', 0)),
                '超大单净流入_净占比': parse_num(s.get('f104', 0))
            })
        
        out = DATA_DIR / f"zjlx_ranking_{today_str}.json"
        with open(out, 'w') as f:
            json.dump({'date': datetime.now().strftime('%Y-%m-%d %H:%M'), 'total': len(ranking), 'ranking': ranking}, f, indent=2, ensure_ascii=False)
        
        print(f"  💾 已保存：{out}")
        print(f"  🏆 TOP3: {ranking[0]['代码']} {ranking[0]['名称']} | {ranking[1]['代码']} {ranking[1]['名称']} | {ranking[2]['代码']} {ranking[2]['名称']}")
        return True
        
    except Exception as e:
        print(f"  ❌ 失败：{e}")
        return False

# ============ 3. 主力排名 ============
def update_mainforce():
    """更新主力排名"""
    print("\n" + "="*60)
    print("🏦 [3/4] 更新主力排名信息")
    print("="*60)
    
    # 主力排名用东方财富的 datacenter 接口
    api_url = "http://push2.eastmoney.com/api/qt/clist/get"
    
    params = {
        'pn': 1, 'pz': 100, 'po': 1, 'np': 1,
        'ut': 'bd1d9ddb04089700cf3c27f2672e909d',
        'fltt': 2, 'invt': 2,
        'fid': 'f62',  # 按主力净流入排名
        'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
        'fields': 'f12,f14,f2,f3,f62,f63,f183,f184',
        '_': int(time.time()*1000)
    }
    
    try:
        resp = requests.get(api_url, params=params, timeout=15)
        data = resp.json()
        
        if not data.get('data') or not data['data'].get('diff'):
            print("  ❌ API 返回空数据")
            return False
        
        stocks = data['data']['diff']
        print(f"  ✅ 获取 {len(stocks)} 只")
        
        ranking = []
        for i, s in enumerate(stocks[:100], 1):
            def parse_num(v):
                try: return float(v)
                except: return 0
            ranking.append({
                '序号': i,
                '代码': s.get('f12', ''),
                '名称': s.get('f14', ''),
                '最新价': parse_num(s.get('f2', 0)),
                '涨跌幅': parse_num(s.get('f3', 0)),
                '主力净流入': parse_num(s.get('f62', 0)),
                '主力净占比': parse_num(s.get('f63', 0)),
                '超大单净流入': parse_num(s.get('f183', 0)),
                '超大单净占比': parse_num(s.get('f184', 0))
            })
        
        out = DATA_DIR / f"mainforce_ranking_{today_str}.json"
        with open(out, 'w') as f:
            json.dump({'date': datetime.now().strftime('%Y-%m-%d %H:%M'), 'total': len(ranking), 'ranking': ranking}, f, indent=2, ensure_ascii=False)
        
        print(f"  💾 已保存：{out}")
        print(f"  🏆 TOP3: {ranking[0]['代码']} {ranking[0]['名称']} | {ranking[1]['代码']} {ranking[1]['名称']} | {ranking[2]['代码']} {ranking[2]['名称']}")
        return True
        
    except Exception as e:
        print(f"  ❌ 失败：{e}")
        return False

# ============ 4. 板块涨幅 ============
def update_sectors():
    """获取板块涨幅前5"""
    print("\n" + "="*60)
    print("📊 [4/4] 获取板块涨幅前五")
    print("="*60)
    
    # 行业板块
    api_url = "http://push2.eastmoney.com/api/qt/clist/get"
    
    params = {
        'pn': 1, 'pz': 31, 'po': 0, 'np': 1,
        'ut': 'bd1d9ddb04089700cf3c27f2672e909d',
        'fltt': 2, 'invt': 2,
        'fid': 'f3',  # 按涨跌幅排序
        'fs': 'm:90 t:2 f:!50',  # 行业板块
        'fields': 'f1,f2,f3,f4,f12,f14',
        '_': int(time.time()*1000)
    }
    
    try:
        resp = requests.get(api_url, params=params, timeout=15)
        data = resp.json()
        
        if not data.get('data') or not data['data'].get('diff'):
            print("  ❌ API 返回空数据")
            return False
        
        sectors = data['data']['diff'][:5]
        print(f"  ✅ 行业板块涨幅 TOP5")
        
        result = []
        for i, s in enumerate(sectors, 1):
            def parse_num(v):
                try: return float(v)
                except: return 0
            entry = {
                '序号': i,
                '代码': s.get('f12', ''),
                '名称': s.get('f14', ''),
                '涨跌幅': parse_num(s.get('f3', 0)),
                '领涨股': '',
                '领涨股涨幅': 0
            }
            result.append(entry)
            print(f"  {i}. {s.get('f14', '')} {parse_num(s.get('f3', 0)):+.2f}%")
        
        # 获取每个板块的领涨股
        for sector in result:
            sector_code = sector['代码']
            params2 = {
                'pn': 1, 'pz': 1, 'po': 1, 'np': 1,
                'ut': 'bd1d9ddb04089700cf3c27f2672e909d',
                'fltt': 2, 'invt': 2,
                'fid': 'f3',
                'fs': f'b:mk0{sector_code}',
                'fields': 'f12,f14,f3',
                '_': int(time.time()*1000)
            }
            try:
                resp2 = requests.get(api_url, params=params2, timeout=10)
                data2 = resp2.json()
                if data2.get('data') and data2['data'].get('diff'):
                    top = data2['data']['diff'][0]
                    def parse_num2(v):
                        try: return float(v)
                        except: return 0
                    sector['领涨股'] = top.get('f14', '')
                    sector['领涨股涨幅'] = parse_num2(top.get('f3', 0))
            except:
                pass
        
        out = DATA_DIR / f"sector_top5_{today_str}.json"
        with open(out, 'w') as f:
            json.dump({'date': datetime.now().strftime('%Y-%m-%d %H:%M'), 'sectors': result}, f, indent=2, ensure_ascii=False)
        
        print(f"  💾 已保存：{out}")
        return True
        
    except Exception as e:
        print(f"  ❌ 失败：{e}")
        return False

# ============ 主流程 ============
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"🔄 全量数据更新 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(update_quotes): "行情",
            executor.submit(update_zjlx): "资金流",
            executor.submit(update_mainforce): "主力排名",
            executor.submit(update_sectors): "板块涨幅",
        }
        
        for future in as_completed(futures):
            task_name = futures[future]
            try:
                results[task_name] = future.result(timeout=120)
            except Exception as e:
                print(f"\n  ❌ {task_name} 任务异常：{e}")
                results[task_name] = False
    
    # 汇总
    print(f"\n{'='*60}")
    print("📊 更新结果汇总")
    print(f"{'='*60}")
    
    for name, ok in results.items():
        status = "✅ 成功" if ok else "❌ 失败"
        print(f"  {name}: {status}")
    
    success = sum(1 for v in results.values() if v)
    print(f"\n  总计：{success}/{len(results)} 项成功")
    print(f"{'='*60}")
