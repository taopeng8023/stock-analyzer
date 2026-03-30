#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日收盘后自动更新数据

功能:
1. 检查是否交易日
2. 获取全市场今日行情
3. 追加到现有数据文件
4. 推送执行结果到微信

执行时间：交易日 15:30
"""

import json
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta
import traceback

# 配置
TUSHARE_TOKEN = 'a7358a0255666758b3ef492a6c1de79f2447de968d4a1785b73716a4'
DATA_DIR = Path('/home/admin/.openclaw/workspace/stocks/data_tushare')
LOG_DIR = Path('/home/admin/.openclaw/workspace/stocks/logs')
CONFIG_FILE = Path('/home/admin/.openclaw/workspace/stocks/push_config.json')

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


def load_config():
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def is_trading_day(date=None):
    """
    检查是否交易日
    
    Args:
        date: 日期 (YYYYMMDD)，默认今天
    
    Returns:
        bool: 是否交易日
    """
    if not date:
        date = datetime.now().strftime('%Y%m%d')
    
    # 检查周末
    dt = datetime.strptime(date, '%Y%m%d')
    if dt.weekday() >= 5:  # 周六=5, 周日=6
        return False
    
    # 调用 Tushare 交易日历接口
    api_url = 'http://api.tushare.pro'
    payload = {
        'api_name': 'trade_cal',
        'token': TUSHARE_TOKEN,
        'params': {
            'exchange': 'SSE',
            'start_date': date,
            'end_date': date,
            'is_open': '1'
        },
        'fields': ''
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        result = resp.json()
        
        if result.get('code') != 0:
            print(f"API 错误：{result.get('msg')}")
            return False
        
        data = result.get('data')
        if data and 'items' in data and data['items']:
            return True
        
        return False
        
    except Exception as e:
        print(f"检查交易日失败：{e}")
        # 默认认为是交易日（保守策略）
        return True


def get_stock_list():
    """获取全市场股票列表"""
    api_url = 'http://api.tushare.pro'
    payload = {
        'api_name': 'stock_basic',
        'token': TUSHARE_TOKEN,
        'params': {'list_status': 'L'},
        'fields': ''
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=60)
        result = resp.json()
        
        if result.get('code') != 0:
            return None
        
        data = result.get('data')
        if data and 'items' in data:
            fields = data.get('fields', [])
            items = data.get('items', [])
            
            stocks = []
            for item in items:
                record = dict(zip(fields, item))
                ts_code = record.get('ts_code', '')
                if ts_code:
                    stocks.append({
                        'ts_code': ts_code,
                        'symbol': ts_code.split('.')[0]
                    })
            
            return stocks
        
        return None
        
    except Exception as e:
        print(f"获取股票列表失败：{e}")
        return None


def fetch_daily_data(ts_code, trade_date):
    """获取单日行情数据"""
    api_url = 'http://api.tushare.pro'
    payload = {
        'api_name': 'daily',
        'token': TUSHARE_TOKEN,
        'params': {
            'ts_code': ts_code,
            'start_date': trade_date,
            'end_date': trade_date
        },
        'fields': ''
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=30)
        result = resp.json()
        
        if result.get('code') != 0:
            return None
        
        data = result.get('data')
        if data and 'items' in data and data['items']:
            fields = data.get('fields', [])
            item = data['items'][0]
            record = dict(zip(fields, item))
            
            return {
                '日期': str(record.get('trade_date', '')),
                '开盘': float(record.get('open', 0)),
                '收盘': float(record.get('close', 0)),
                '最高': float(record.get('high', 0)),
                '最低': float(record.get('low', 0)),
                '成交量': float(record.get('vol', 0)) * 100,
                '成交额': float(record.get('amount', 0)) * 1000,
                '涨跌幅': float(record.get('pct_chg', 0))
            }
        
        return None
        
    except Exception as e:
        return None


def append_data(symbol, new_data):
    """追加数据到文件"""
    filepath = DATA_DIR / f'{symbol}.json'
    
    try:
        # 读取现有数据
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = []
        
        # 检查是否已存在
        existing_dates = [d['日期'] for d in data]
        if new_data['日期'] in existing_dates:
            return 'exists'
        
        # 追加数据
        data.append(new_data)
        
        # 按日期排序
        data.sort(key=lambda x: x['日期'])
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return 'success'
        
    except Exception as e:
        print(f"保存数据失败 {symbol}: {e}")
        return 'error'


def push_wechat(content, config):
    """推送微信通知"""
    # 企业微信
    if config.get('wecom_webhook'):
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content}
        }
        
        try:
            resp = requests.post(config['wecom_webhook'], json=payload, timeout=10)
            result = resp.json()
            if result.get('errcode') == 0:
                print("✅ 企业微信推送成功")
                return True
        except Exception as e:
            print(f"企业微信推送失败：{e}")
    
    # 钉钉
    if config.get('dingtalk_webhook'):
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "数据更新通知",
                "text": content
            }
        }
        
        try:
            resp = requests.post(config['dingtalk_webhook'], json=payload, timeout=10)
            result = resp.json()
            if result.get('errcode') == 0:
                print("✅ 钉钉推送成功")
                return True
        except Exception as e:
            print(f"钉钉推送失败：{e}")
    
    return False


def main():
    log_file = LOG_DIR / f'update_{datetime.now().strftime("%Y%m%d")}.log'
    
    with open(log_file, 'w', encoding='utf-8') as log:
        def log_print(msg):
            print(msg)
            log.write(msg + '\n')
            log.flush()
        
        log_print("=" * 80)
        log_print("每日数据更新")
        log_print(f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_print("=" * 80)
        
        start_time = time.time()
        
        # 加载配置
        config = load_config()
        
        # 1. 检查是否交易日
        today = datetime.now().strftime('%Y%m%d')
        log_print(f"\n[1/5] 检查交易日：{today}")
        
        if not is_trading_day(today):
            log_print("❌ 今天不是交易日，跳过更新")
            return
        
        log_print("✅ 确认是交易日")
        
        # 2. 获取股票列表
        log_print(f"\n[2/5] 获取股票列表...")
        stocks = get_stock_list()
        
        if not stocks:
            log_print("❌ 获取股票列表失败")
            return
        
        log_print(f"   股票总数：{len(stocks)} 只")
        
        # 3. 批量获取数据
        log_print(f"\n[3/5] 获取今日行情...")
        
        success = 0
        exists = 0
        fail = 0
        last_request = 0
        
        for i, stock in enumerate(stocks):
            ts_code = stock['ts_code']
            symbol = stock['symbol']
            
            # 频率限制
            now = time.time()
            if now - last_request < 1.0:
                time.sleep(1.0 - (now - last_request))
            last_request = time.time()
            
            # 获取数据
            data = fetch_daily_data(ts_code, today)
            
            if data:
                result = append_data(symbol, data)
                if result == 'success':
                    success += 1
                elif result == 'exists':
                    exists += 1
                else:
                    fail += 1
            else:
                fail += 1
            
            # 进度
            if (i + 1) % 500 == 0:
                log_print(f"   进度：{i+1}/{len(stocks)} (成功:{success} 已存在:{exists} 失败:{fail})")
        
        elapsed = time.time() - start_time
        
        # 4. 生成报告
        log_print(f"\n[4/5] 生成报告...")
        log_print(f"\n执行结果:")
        log_print(f"   成功更新：{success} 只")
        log_print(f"   已存在：{exists} 只")
        log_print(f"   失败：{fail} 只")
        log_print(f"   总耗时：{elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
        
        # 5. 推送微信
        log_print(f"\n[5/5] 推送微信通知...")
        
        wechat_content = f"""# 📊 数据更新完成

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**日期**: {today}

## 执行结果
- ✅ 成功更新：{success} 只
- ⏭️ 已存在：{exists} 只
- ❌ 失败：{fail} 只
- ⏱️ 总耗时：{elapsed/60:.1f}分钟

## 数据状态
- 数据目录：`/home/admin/.openclaw/workspace/stocks/data_tushare/`
- 股票总数：{len(stocks)} 只
- 最新日期：{today}

{'**注意**: 部分股票更新失败，请检查日志' if fail > 10 else ''}
"""
        
        if push_wechat(wechat_content, config):
            log_print("✅ 微信推送成功")
        else:
            log_print("⚠️  微信推送失败（可能未配置）")
        
        log_print("\n" + "=" * 80)
        log_print("执行完成")
        log_print("=" * 80)
        
        # 保存详细报告
        report = {
            'date': today,
            'time': datetime.now().isoformat(),
            'elapsed': elapsed,
            'summary': {
                'total': len(stocks),
                'success': success,
                'exists': exists,
                'fail': fail
            }
        }
        
        report_file = LOG_DIR / f'update_report_{today}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        log_print(f"\n💾 报告已保存：{report_file}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"执行异常：{e}")
        traceback.print_exc()
        
        # 推送错误通知
        config = load_config()
        error_content = f"""# ❌ 数据更新失败

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**错误**: {str(e)}

请检查日志文件了解详情。
"""
        push_wechat(error_content, config)
        sys.exit(1)
