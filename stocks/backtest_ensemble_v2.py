#!/usr/bin/env python3
"""
三重确认策略回测脚本 V2
回测三个优化方案，对比胜率、收益、夏普比率

方案 A：ML+ 技术面双重确认
  买入条件：ML 置信度 > 80%, RSI < 40, 近 10 天跌幅 > 8%
  卖出条件：止盈 10% 后回撤 5%, 止损 8%, 最长持有 15 天

方案 B：资金流 + 技术面
  买入条件：主力净流入 > 0, 主力占比 > 10%, RSI < 45, 近 10 天跌幅 > 10%
  卖出条件：同上

方案 C：三重确认增强版
  买入条件：ML 置信度 > 75%, 资金流：主力净流入 > 0 或无数据, RSI < 45, 近 10 天跌幅 > 10%
  卖出条件：同上
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
import pickle
warnings.filterwarnings('ignore')

# 配置
HISTORY_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data_history_2022_2026")
FLOW_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/data")
MODEL_FILE = Path("/Users/taopeng/.openclaw/workspace/stocks/models/ml_nn_full_balanced_20260417_1338.pkl")
OUTPUT_DIR = Path("/Users/taopeng/.openclaw/workspace/stocks/backtest_reports")

# 回测参数
START_DATE = "20220101"
END_DATE = "20261231"
INITIAL_CAPITAL = 1000000  # 初始资金 100 万

class StrategyBacktest:
    """策略回测器"""
    
    def __init__(self):
        self.trades = {'A': [], 'B': [], 'C': []}
        self.model = None
        self.scaler = None
        self.features = None
        self.load_model()
    
    def load_model(self):
        """加载 ML 模型"""
        try:
            if MODEL_FILE.exists():
                with open(MODEL_FILE, 'rb') as f:
                    data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
                self.features = data['features']
                print(f"✓ ML 模型已加载：{MODEL_FILE.name}")
        except Exception as e:
            print(f"⚠ ML 模型加载失败：{e}，将使用模拟置信度")
            self.model = None
    
    def calculate_rsi(self, closes, period=14):
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
    
    def calculate_drop(self, closes, period=10):
        """计算近 N 天跌幅"""
        if len(closes) < period:
            return 0
        
        high = max(closes[-period:])
        current = closes[-1]
        drop = (high - current) / high * 100
        return drop
    
    def predict_confidence(self, closes, volumes, highs, lows):
        """使用 ML 模型预测置信度"""
        if self.model is None or len(closes) < 30:
            # 模拟置信度：基于技术面强度
            rsi = self.calculate_rsi(closes)
            drop = self.calculate_drop(closes)
            # 超卖程度越高，置信度越高
            base_conf = 0.5 + (45 - rsi) / 100 + drop / 200
            return min(0.95, max(0.3, base_conf))
        
        try:
            i = len(closes) - 1
            ma5 = np.mean(closes[i-5:i+1])
            ma10 = np.mean(closes[i-10:i+1])
            ma20 = np.mean(closes[i-20:i+1])
            
            feat = {
                'p_ma5': (closes[i] - ma5) / ma5,
                'p_ma10': (closes[i] - ma10) / ma10,
                'p_ma20': (closes[i] - ma20) / ma20,
                'vol5': np.std([closes[j] - closes[j-1] for j in range(i-4, i+1)]) / closes[i],
            }
            
            deltas = [closes[j] - closes[j-1] for j in range(i-13, i+1)]
            gains = sum(d for d in deltas if d > 0)
            losses = sum(-d for d in deltas if d < 0)
            feat['rsi'] = 100 - 100/(1 + gains/(losses+0.001)) if losses > 0 else 100
            
            vol5 = np.mean(volumes[i-5:i+1])
            feat['vol_ratio'] = volumes[i] / (vol5 + 0.001)
            feat['hl_pct'] = (highs[i] - lows[i]) / closes[i]
            feat['boll_pos'] = (closes[i] - ma20) / (2 * np.std(closes[i-20:i+1]) + 0.001)
            
            X = np.array([[feat.get(k, 0) for k in self.features]])
            X_scaled = self.scaler.transform(X)
            prob = self.model.predict_proba(X_scaled)[0][1]
            return prob
        except:
            return 0.5
    
    def load_flow_data(self, code):
        """加载资金流数据"""
        flow_files = list(FLOW_DIR.glob(f"flow_{code}_*.json"))
        if not flow_files:
            return None
        
        # 加载最新的资金流文件
        flow_file = sorted(flow_files)[-1]
        try:
            with open(flow_file) as f:
                return json.load(f)
        except:
            return None
    
    def get_flow_signal(self, flow_data, date):
        """获取指定日期的资金流信号"""
        if not flow_data:
            return {'main_flow': None, 'main_pct': None}
        
        # 查找匹配日期的数据
        for item in flow_data:
            item_date = item.get('date', '').replace('-', '')
            if item_date == date:
                return {
                    'main_flow': item.get('main_flow', 0),
                    'main_pct': item.get('main_pct', 0)
                }
        
        # 如果没有精确匹配，返回最新数据
        if flow_data:
            latest = flow_data[-1]
            return {
                'main_flow': latest.get('main_flow', 0),
                'main_pct': latest.get('main_pct', 0)
            }
        
        return {'main_flow': None, 'main_pct': None}
    
    def check_strategy_a(self, closes, volumes, highs, lows, i):
        """方案 A：ML+ 技术面双重确认"""
        if i < 30:
            return False
        
        hist_closes = closes[:i+1]
        rsi = self.calculate_rsi(hist_closes)
        drop = self.calculate_drop(hist_closes, period=10)
        confidence = self.predict_confidence(hist_closes, volumes[:i+1], highs[:i+1], lows[:i+1])
        
        # 买入条件：ML 置信度 > 80%, RSI < 40, 近 10 天跌幅 > 8%
        return confidence > 0.80 and rsi < 40 and drop > 8
    
    def check_strategy_b(self, closes, volumes, highs, lows, i, flow_data, date):
        """方案 B：资金流 + 技术面"""
        if i < 30:
            return False
        
        hist_closes = closes[:i+1]
        rsi = self.calculate_rsi(hist_closes)
        drop = self.calculate_drop(hist_closes, period=10)
        
        flow = self.get_flow_signal(flow_data, date)
        main_flow = flow['main_flow']
        main_pct = flow['main_pct']
        
        # 买入条件：主力净流入 > 0, 主力占比 > 10%, RSI < 45, 近 10 天跌幅 > 10%
        if main_flow is None:
            return False
        
        return main_flow > 0 and main_pct > 10 and rsi < 45 and drop > 10
    
    def check_strategy_c(self, closes, volumes, highs, lows, i, flow_data, date):
        """方案 C：三重确认增强版"""
        if i < 30:
            return False
        
        hist_closes = closes[:i+1]
        rsi = self.calculate_rsi(hist_closes)
        drop = self.calculate_drop(hist_closes, period=10)
        confidence = self.predict_confidence(hist_closes, volumes[:i+1], highs[:i+1], lows[:i+1])
        
        flow = self.get_flow_signal(flow_data, date)
        main_flow = flow['main_flow']
        
        # 买入条件：ML 置信度 > 75%, 资金流：主力净流入 > 0 或无数据, RSI < 45, 近 10 天跌幅 > 10%
        flow_ok = main_flow is None or main_flow > 0
        
        return confidence > 0.75 and flow_ok and rsi < 45 and drop > 10
    
    def check_exit(self, buy_price, current_price, high_since_buy):
        """检查卖出条件"""
        # 止盈：盈利 10% 后回撤 5%
        if current_price >= buy_price * 1.10:
            peak_return = (high_since_buy - buy_price) / buy_price
            current_return = (current_price - buy_price) / buy_price
            if peak_return - current_return >= 0.05:
                return 'trailing_stop'
        
        # 止损：亏损 8%
        if current_price <= buy_price * 0.92:
            return 'stop_loss'
        
        return None
    
    def backtest_stock(self, code, strategy):
        """回测单只股票的单个策略"""
        try:
            with open(HISTORY_DIR / f"{code}.json") as f:
                raw = json.load(f)
            
            items, fields = raw['items'], raw['fields']
            if len(items) < 100:
                return []
            
            # 解析数据
            data = []
            for item in items:
                d = dict(zip(fields, item))
                trade_date = str(d.get('trade_date', ''))
                
                if trade_date < START_DATE or trade_date > END_DATE:
                    continue
                
                c = float(d.get('close', 0))
                if c > 0:
                    data.append({
                        'date': trade_date,
                        'close': c,
                        'open': float(d.get('open', c)),
                        'high': float(d.get('high', c)),
                        'low': float(d.get('low', c)),
                        'vol': float(d.get('vol', 0))
                    })
            
            if len(data) < 100:
                return []
            
            # 加载资金流数据
            flow_data = self.load_flow_data(code)
            
            closes = [d['close'] for d in data]
            volumes = [d['vol'] for d in data]
            highs = [d['high'] for d in data]
            lows = [d['low'] for d in data]
            dates = [d['date'] for d in data]
            
            trades = []
            position = None
            max_hold_days = 15
            
            for i in range(30, len(data)):
                date = dates[i]
                current_price = closes[i]
                
                if position is not None:
                    # 更新持仓最高价
                    position['high'] = max(position['high'], current_price)
                    hold_days = i - position['buy_idx']
                    
                    # 检查卖出条件
                    exit_reason = self.check_exit(
                        position['buy_price'],
                        current_price,
                        position['high']
                    )
                    
                    # 止盈回撤或止损
                    if exit_reason:
                        return_pct = (current_price - position['buy_price']) / position['buy_price'] * 100
                        trades.append({
                            'code': code,
                            'buy_date': dates[position['buy_idx']],
                            'sell_date': date,
                            'buy_price': position['buy_price'],
                            'sell_price': current_price,
                            'return_pct': return_pct,
                            'hold_days': hold_days,
                            'exit_reason': exit_reason
                        })
                        position = None
                    # 最长持有时间
                    elif hold_days >= max_hold_days:
                        return_pct = (current_price - position['buy_price']) / position['buy_price'] * 100
                        trades.append({
                            'code': code,
                            'buy_date': dates[position['buy_idx']],
                            'sell_date': date,
                            'buy_price': position['buy_price'],
                            'sell_price': current_price,
                            'return_pct': return_pct,
                            'hold_days': hold_days,
                            'exit_reason': 'max_hold'
                        })
                        position = None
                
                # 如果没有持仓，检查买入信号
                if position is None:
                    buy_signal = False
                    
                    if strategy == 'A':
                        buy_signal = self.check_strategy_a(closes, volumes, highs, lows, i)
                    elif strategy == 'B':
                        buy_signal = self.check_strategy_b(closes, volumes, highs, lows, i, flow_data, date)
                    elif strategy == 'C':
                        buy_signal = self.check_strategy_c(closes, volumes, highs, lows, i, flow_data, date)
                    
                    if buy_signal:
                        position = {
                            'buy_idx': i,
                            'buy_price': current_price,
                            'buy_date': date,
                            'high': current_price
                        }
            
            # 处理最后的持仓
            if position is not None:
                sell_idx = min(position['buy_idx'] + max_hold_days, len(data) - 1)
                sell_price = closes[sell_idx]
                return_pct = (sell_price - position['buy_price']) / position['buy_price'] * 100
                trades.append({
                    'code': code,
                    'buy_date': dates[position['buy_idx']],
                    'sell_date': dates[sell_idx],
                    'buy_price': position['buy_price'],
                    'sell_price': sell_price,
                    'return_pct': return_pct,
                    'hold_days': sell_idx - position['buy_idx'],
                    'exit_reason': 'end'
                })
            
            return trades
            
        except Exception as e:
            print(f"回测股票 {code} 失败：{e}", flush=True)
            return []
    
    def run_strategy(self, strategy):
        """执行单个策略的回测"""
        print(f"\n{'='*70}", flush=True)
        print(f"策略 {strategy} 回测", flush=True)
        print(f"{'='*70}", flush=True)
        
        if strategy == 'A':
            print("方案 A：ML+ 技术面双重确认", flush=True)
            print("  买入：ML 置信度 > 80%, RSI < 40, 近 10 天跌幅 > 8%", flush=True)
        elif strategy == 'B':
            print("方案 B：资金流 + 技术面", flush=True)
            print("  买入：主力净流入 > 0, 主力占比 > 10%, RSI < 45, 近 10 天跌幅 > 10%", flush=True)
        elif strategy == 'C':
            print("方案 C：三重确认增强版", flush=True)
            print("  买入：ML 置信度 > 75%, 资金流>=0 或无数据，RSI < 45, 近 10 天跌幅 > 10%", flush=True)
        
        print(f"  卖出：止盈 10% 后回撤 5%, 止损 8%, 最长持有 15 天", flush=True)
        print(f"{'='*70}\n", flush=True)
        
        stock_files = list(HISTORY_DIR.glob("*.json"))
        total_stocks = len(stock_files)
        print(f"回测股票数量：{total_stocks}", flush=True)
        
        all_trades = []
        for idx, stock_file in enumerate(stock_files):
            code = stock_file.stem
            trades = self.backtest_stock(code, strategy)
            all_trades.extend(trades)
            
            if (idx + 1) % 500 == 0:
                print(f"进度：{idx + 1}/{total_stocks} (交易数：{len(all_trades)})", flush=True)
        
        print(f"\n完成回测：{len(all_trades)} 笔交易\n", flush=True)
        self.trades[strategy] = all_trades
        
        return self.calculate_stats(all_trades)
    
    def calculate_stats(self, trades):
        """计算统计指标"""
        if not trades:
            return None
        
        returns = [t['return_pct'] for t in trades]
        
        total_trades = len(returns)
        winning_trades = sum(1 for r in returns if r > 0)
        losing_trades = sum(1 for r in returns if r <= 0)
        
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        # 夏普比率 (假设无风险利率为 3% 年化)
        # 日收益率转换为年化
        daily_returns = [r / 100 for r in returns]
        if len(daily_returns) > 1 and std_return > 0:
            sharpe = (np.mean(daily_returns) * 252) / (np.std(daily_returns) * np.sqrt(252))
        else:
            sharpe = 0
        
        avg_win = np.mean([r for r in returns if r > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([r for r in returns if r <= 0]) if losing_trades > 0 else 0
        
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        expected_return = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)
        
        max_win = max(returns)
        max_loss = min(returns)
        
        # 计算最大回撤
        cumulative = [1]
        for r in returns:
            cumulative.append(cumulative[-1] * (1 + r/100))
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative) / peak * 100
        max_drawdown = max(drawdown)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'std_return': std_return,
            'sharpe_ratio': sharpe,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expected_return': expected_return,
            'max_win': max_win,
            'max_loss': max_loss,
            'total_return': sum(returns),
            'max_drawdown': max_drawdown,
            'cumulative_return': (cumulative[-1] - 1) * 100
        }
    
    def run_all(self):
        """运行所有策略"""
        print("\n" + "="*70, flush=True)
        print("三重确认策略优化 V2 - 回测系统", flush=True)
        print("="*70, flush=True)
        print(f"回测周期：{START_DATE} ~ {END_DATE}", flush=True)
        print(f"初始资金：{INITIAL_CAPITAL:,} 元", flush=True)
        print("="*70, flush=True)
        
        results = {}
        for strategy in ['A', 'B', 'C']:
            stats = self.run_strategy(strategy)
            results[strategy] = stats
        
        # 对比结果
        self.compare_strategies(results)
        
        # 保存结果
        self.save_results(results)
        
        return results
    
    def compare_strategies(self, results):
        """对比策略结果"""
        print("\n" + "="*70, flush=True)
        print("策略对比结果", flush=True)
        print("="*70, flush=True)
        
        print(f"\n{'指标':<15} {'方案 A':<15} {'方案 B':<15} {'方案 C':<15}", flush=True)
        print("-"*70, flush=True)
        
        metrics = [
            ('胜率 (%)', 'win_rate'),
            ('期望收益 (%)', 'expected_return'),
            ('平均收益 (%)', 'avg_return'),
            ('夏普比率', 'sharpe_ratio'),
            ('总收益 (%)', 'cumulative_return'),
            ('最大回撤 (%)', 'max_drawdown'),
            ('交易次数', 'total_trades'),
            ('盈亏比', 'profit_factor'),
        ]
        
        for name, key in metrics:
            values = []
            for s in ['A', 'B', 'C']:
                val = results[s].get(key, 0) if results[s] else 0
                if key in ['win_rate', 'expected_return', 'avg_return', 'total_return', 'cumulative_return', 'max_drawdown']:
                    values.append(f"{val:.2f}")
                elif key == 'sharpe_ratio':
                    values.append(f"{val:.3f}")
                elif key == 'profit_factor':
                    values.append(f"{val:.2f}" if val != float('inf') else "∞")
                else:
                    values.append(f"{int(val)}")
            print(f"{name:<15} {values[0]:<15} {values[1]:<15} {values[2]:<15}", flush=True)
        
        # 找出最优策略
        best_strategy = max(['A', 'B', 'C'], key=lambda s: results[s]['win_rate'] if results[s] else 0)
        best_win_rate = results[best_strategy]['win_rate']
        
        print("\n" + "-"*70, flush=True)
        print(f"★ 最优策略：方案 {best_strategy} (胜率 {best_win_rate:.2f}%)", flush=True)
        
        if best_win_rate > 65:
            print(f"✓ 胜率 > 65%，建议创建实盘选股脚本", flush=True)
        else:
            print(f"⚠ 胜率 <= 65%，需要进一步优化", flush=True)
        
        print("="*70, flush=True)
    
    def save_results(self, results):
        """保存结果"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存详细结果
        results_file = OUTPUT_DIR / f"backtest_ensemble_v2_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'strategies': {
                    'A': {'name': 'ML+ 技术面', 'stats': results['A']},
                    'B': {'name': '资金流 + 技术面', 'stats': results['B']},
                    'C': {'name': '三重确认增强版', 'stats': results['C']},
                }
            }, f, ensure_ascii=False, indent=2)
        print(f"\n详细结果已保存：{results_file}", flush=True)
        
        # 保存交易明细
        trades_file = OUTPUT_DIR / f"backtest_ensemble_v2_trades_{timestamp}.json"
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump(self.trades, f, ensure_ascii=False, indent=2)
        print(f"交易明细已保存：{trades_file}", flush=True)


def main():
    backtest = StrategyBacktest()
    results = backtest.run_all()
    
    # 返回最优策略信息
    best_strategy = max(['A', 'B', 'C'], key=lambda s: results[s]['win_rate'] if results[s] else 0)
    best_win_rate = results[best_strategy]['win_rate']
    
    return {
        'best_strategy': best_strategy,
        'best_win_rate': best_win_rate,
        'results': results
    }


if __name__ == "__main__":
    result = main()
    print(f"\n最终推荐：方案 {result['best_strategy']}, 胜率 {result['best_win_rate']:.2f}%")
