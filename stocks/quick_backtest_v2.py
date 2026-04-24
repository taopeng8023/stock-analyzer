#!/usr/bin/env python3
"""
快速回测脚本 V2 - 简化版
只回测最近 1 年数据（2025-2026），测试三个优化方案
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 配置
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/backtest_reports")

# 回测参数 - 只回测最近 1 年
START_DATE = "20250101"
END_DATE = "20261231"

# 三个优化方案
STRATEGIES = {
    'A': {
        'name': '方案 A (严格)',
        'rsi_threshold': 35,
        'drop_threshold': 15,
        'require_ma5': False,
        'require_volume': False
    },
    'B': {
        'name': '方案 B (MA5 确认)',
        'rsi_threshold': 40,
        'drop_threshold': 12,
        'require_ma5': True,  # 站上 MA5
        'require_volume': False
    },
    'C': {
        'name': '方案 C (成交量)',
        'rsi_threshold': 45,
        'drop_threshold': 10,
        'require_ma5': False,
        'require_volume': True  # 成交量放大
    }
}

def calculate_rsi(closes, period=14):
    """计算 RSI 指标"""
    if len(closes) < period + 1:
        return 50
    
    deltas = [closes[i] - closes[i-1] for i in range(len(closes)-period, len(closes))]
    gains = sum(d for d in deltas if d > 0)
    losses = sum(-d for d in deltas if d < 0)
    
    if losses == 0:
        return 100
    
    rs = gains / (losses + 0.001)
    rsi = 100 - 100 / (1 + rs)
    return rsi

def calculate_drop(closes, period=10):
    """计算近 N 天跌幅"""
    if len(closes) < period:
        return 0
    
    high = max(closes[-period:])
    current = closes[-1]
    drop = (high - current) / high * 100
    return drop

def calculate_ma(closes, period=5):
    """计算移动平均线"""
    if len(closes) < period:
        return closes[-1]
    return np.mean(closes[-period:])

def calculate_volume_ratio(volumes, period=5):
    """计算成交量比率（当日/近 5 日均量）"""
    if len(volumes) < period:
        return 1.0
    avg_vol = np.mean(volumes[-period:])
    if avg_vol == 0:
        return 1.0
    return volumes[-1] / avg_vol

def check_buy_signal(closes, volumes, strategy):
    """检查买入信号"""
    if len(closes) < 30:  # 至少需要 30 天数据
        return False
    
    rsi = calculate_rsi(closes)
    drop = calculate_drop(closes)
    
    # 基础条件：RSI 和跌幅
    if rsi >= strategy['rsi_threshold']:
        return False
    if drop < strategy['drop_threshold']:
        return False
    
    # 方案 B：需要站上 MA5
    if strategy['require_ma5']:
        ma5 = calculate_ma(closes, 5)
        if closes[-1] < ma5:
            return False
    
    # 方案 C：需要成交量放大
    if strategy['require_volume']:
        vol_ratio = calculate_volume_ratio(volumes)
        if vol_ratio < 1.2:  # 成交量放大 20%
            return False
    
    return True

def backtest_stock(code, items, strategy):
    """回测单只股票"""
    trades = []
    position = None
    holding_days = 0
    
    # items 格式：[ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount]
    # 按日期排序
    sorted_items = sorted(items, key=lambda x: x[1])
    
    for i, item in enumerate(sorted_items):
        date = str(item[1])  # trade_date
        if date < START_DATE or date > END_DATE:
            continue
        
        close = item[5]  # close price
        volume = item[9]  # volume
        
        # 收集历史数据
        hist_items = sorted_items[:i+1]
        closes = [item[5] for item in hist_items[-60:]]
        volumes = [item[9] for item in hist_items[-60:]]
        
        if not position:
            # 检查买入信号
            if check_buy_signal(closes, volumes, strategy):
                position = {
                    'buy_date': date,
                    'buy_price': close,
                    'high_price': close
                }
                holding_days = 0
        else:
            holding_days += 1
            # 更新最高价
            if close > position['high_price']:
                position['high_price'] = close
            
            # 卖出条件
            sell = False
            sell_reason = ''
            sell_price = close
            
            # 1. 止损 8%
            if close < position['buy_price'] * 0.92:
                sell = True
                sell_reason = '止损'
            
            # 2. 止盈：从最高点回撤 5%
            elif close < position['high_price'] * 0.95 and (close - position['buy_price']) / position['buy_price'] > 0.05:
                sell = True
                sell_reason = '回撤止盈'
            
            # 3. 固定止盈 15%
            elif (close - position['buy_price']) / position['buy_price'] > 0.15:
                sell = True
                sell_reason = '止盈'
            
            # 4. 最长持有 15 天
            elif holding_days >= 15:
                sell = True
                sell_reason = '到期'
            
            if sell:
                ret = (sell_price - position['buy_price']) / position['buy_price'] * 100
                trades.append({
                    'code': code,
                    'buy_date': position['buy_date'],
                    'sell_date': date,
                    'buy_price': position['buy_price'],
                    'sell_price': sell_price,
                    'return': ret,
                    'reason': sell_reason
                })
                position = None
    
    return trades

def load_stock_data(code):
    """加载股票历史数据"""
    # 尝试不同的文件名格式
    possible_files = [
        HISTORY_DIR / f"{code}.json",
        HISTORY_DIR / f"{code.lower()}.json",
    ]
    
    for file_path in possible_files:
        if file_path.exists():
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    # 返回 items 数组
                    return data.get('items', [])
            except:
                pass
    return None

def run_backtest():
    """运行回测"""
    print("=" * 60)
    print("快速回测 V2 - 三个优化方案对比")
    print(f"回测区间：{START_DATE} 至 {END_DATE}")
    print("=" * 60)
    
    # 获取所有股票文件
    stock_files = list(HISTORY_DIR.glob("*.json"))
    print(f"发现 {len(stock_files)} 只股票数据文件")
    
    # 限制测试股票数量（快速回测）
    max_stocks = 500  # 测试前 500 只股票
    stock_files = stock_files[:max_stocks]
    
    results = {key: [] for key in STRATEGIES.keys()}
    top_stocks = {key: [] for key in STRATEGIES.keys()}
    
    for idx, stock_file in enumerate(stock_files):
        code = stock_file.stem
        items = load_stock_data(code)
        
        if not items or len(items) < 60:
            continue
        
        # 对每个策略回测
        for key, strategy in STRATEGIES.items():
            trades = backtest_stock(code, items, strategy)
            results[key].extend(trades)
            
            # 记录盈利交易用于 TOP10
            for trade in trades:
                if trade['return'] > 0:
                    top_stocks[key].append({
                        'code': code,
                        'return': trade['return'],
                        'buy_date': trade['buy_date']
                    })
        
        if (idx + 1) % 100 == 0:
            print(f"已处理 {idx + 1}/{len(stock_files)} 只股票...")
    
    # 统计结果
    print("\n" + "=" * 60)
    print("回测结果对比")
    print("=" * 60)
    
    summary = {}
    for key, strategy in STRATEGIES.items():
        trades = results[key]
        if not trades:
            print(f"\n{strategy['name']}: 无交易")
            continue
        
        total_trades = len(trades)
        winning = sum(1 for t in trades if t['return'] > 0)
        losing = total_trades - winning
        win_rate = winning / total_trades * 100 if total_trades > 0 else 0
        
        returns = [t['return'] for t in trades]
        avg_return = np.mean(returns)
        total_return = sum(returns)
        
        summary[key] = {
            'name': strategy['name'],
            'total_trades': total_trades,
            'winning': winning,
            'losing': losing,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': total_return
        }
        
        print(f"\n{strategy['name']}:")
        print(f"  总交易数：{total_trades}")
        print(f"  盈利/亏损：{winning}/{losing}")
        print(f"  胜率：{win_rate:.2f}%")
        print(f"  平均收益：{avg_return:.2f}%")
        print(f"  总收益：{total_return:.2f}%")
    
    # 找出最优方案
    if summary:
        best_key = max(summary.keys(), key=lambda k: summary[k]['win_rate'])
        best_strategy = summary[best_key]
        
        print("\n" + "=" * 60)
        print(f"🏆 最优方案：{best_strategy['name']}")
        print(f"   胜率：{best_strategy['win_rate']:.2f}%")
        print(f"   平均收益：{best_strategy['avg_return']:.2f}%")
        print("=" * 60)
        
        # 如果胜率>60%，输出 TOP10 选股
        if best_strategy['win_rate'] > 60:
            print("\n📈 TOP10 选股（按收益排序）:")
            sorted_stocks = sorted(top_stocks[best_key], key=lambda x: x['return'], reverse=True)[:10]
            for i, stock in enumerate(sorted_stocks, 1):
                print(f"  {i}. {stock['code']} - 收益 {stock['return']:.2f}% (买入日期：{stock['buy_date']})")
        
        # 保存结果
        output_file = OUTPUT_DIR / f"quick_backtest_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_data = {
            'summary': summary,
            'best_strategy': best_key,
            'top_stocks': {k: sorted(v, key=lambda x: x['return'], reverse=True)[:10] for k, v in top_stocks.items()}
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n结果已保存至：{output_file}")
        
        return summary, best_key
    else:
        print("\n⚠️  无有效交易数据")
        return {}, None

if __name__ == "__main__":
    summary, best_key = run_backtest()
