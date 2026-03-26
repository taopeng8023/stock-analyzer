#!/usr/bin/env python3
"""
数据源健康监控模块

监控所有数据源的可用性、响应时间、成功率
生成健康报告和告警

用法:
    python3 datasource_health_monitor.py --check     # 检查所有数据源
    python3 datasource_health_monitor.py --report    # 生成健康报告
    python3 datasource_health_monitor.py --watch     # 持续监控
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import requests


@dataclass
class DataSourceHealth:
    """数据源健康状态"""
    name: str                   # 数据源名称
    status: str                 # 状态：healthy/degraded/down
    response_time_ms: int       # 响应时间（毫秒）
    success_rate: float         # 成功率（0-100）
    last_check: str             # 最后检查时间
    last_error: Optional[str]   # 最后错误信息
    uptime_24h: float           # 24 小时可用率


@dataclass
class HealthReport:
    """健康报告"""
    check_time: str             # 检查时间
    total_sources: int          # 总数据源数
    healthy_count: int          # 健康数量
    degraded_count: int         # 降级数量
    down_count: int             # 宕机数量
    avg_response_time: int      # 平均响应时间
    avg_success_rate: float     # 平均成功率
    sources: List[DataSourceHealth]  # 各数据源状态


class DataSourceHealthMonitor:
    """数据源健康监控器"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
        self.health_file = self.cache_dir / 'health_status.json'
        self.history_file = self.cache_dir / 'health_history.json'
        
        # 数据源列表
        self.sources = {
            'baidu': 'https://gushitong.baidu.com/opendata',
            'eastmoney': 'http://push2.eastmoney.com/api/qt/clist/get',
            'tencent': 'http://qt.gtimg.cn/q=sh600519',
            'sina': 'http://hq.sinajs.cn/list=sh600519',
            'netease': 'http://quotes.money.163.com/quote/price/600519.html',
        }
        
        # 健康阈值
        self.thresholds = {
            'response_time_warning': 5000,    # 5 秒告警
            'response_time_critical': 10000,  # 10 秒严重
            'success_rate_warning': 80,       # 80% 告警
            'success_rate_critical': 50,      # 50% 严重
        }
        
        # 历史数据
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """加载历史数据"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_history(self):
        """保存历史数据"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def check_source(self, name: str, url: str) -> DataSourceHealth:
        """检查单个数据源"""
        start_time = time.time()
        
        try:
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            
            resp = session.get(url, timeout=10)
            response_time = int((time.time() - start_time) * 1000)
            
            # 判断状态
            if resp.status_code == 200 and len(resp.content) > 100:
                status = 'healthy'
                error = None
            else:
                status = 'degraded'
                error = f'HTTP {resp.status_code}'
                
        except requests.Timeout:
            response_time = 10000
            status = 'down'
            error = 'Timeout'
            
        except requests.ConnectionError:
            response_time = 0
            status = 'down'
            error = 'Connection Error'
            
        except Exception as e:
            response_time = 0
            status = 'down'
            error = str(e)
        
        # 更新历史
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.history:
            self.history[today] = {}
        
        if name not in self.history[today]:
            self.history[today][name] = {'checks': [], 'successes': 0}
        
        self.history[today][name]['checks'].append({
            'time': datetime.now().isoformat(),
            'status': status,
            'response_time': response_time,
        })
        
        if status == 'healthy':
            self.history[today][name]['successes'] += 1
        
        self._save_history()
        
        # 计算成功率
        checks_today = self.history[today][name]['checks']
        successes = self.history[today][name]['successes']
        success_rate = (successes / len(checks_today) * 100) if checks_today else 0
        
        # 计算 24 小时可用率
        uptime_24h = self._calculate_uptime(name)
        
        return DataSourceHealth(
            name=name,
            status=status,
            response_time_ms=response_time,
            success_rate=success_rate,
            last_check=datetime.now().isoformat(),
            last_error=error,
            uptime_24h=uptime_24h,
        )
    
    def _calculate_uptime(self, name: str) -> float:
        """计算 24 小时可用率"""
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        total_checks = 0
        total_successes = 0
        
        for day in [today, yesterday]:
            if day in self.history and name in self.history[day]:
                total_checks += len(self.history[day][name]['checks'])
                total_successes += self.history[day][name]['successes']
        
        if total_checks == 0:
            return 100.0
        
        return total_successes / total_checks * 100
    
    def check_all_sources(self) -> HealthReport:
        """检查所有数据源"""
        print("\n" + "="*80)
        print("🔍 数据源健康检查")
        print("="*80)
        
        health_list = []
        
        for name, url in self.sources.items():
            print(f"\n[{name}] 检查中...", end=' ')
            
            health = self.check_source(name, url)
            health_list.append(health)
            
            # 显示状态
            if health.status == 'healthy':
                print(f"✅ {health.response_time_ms}ms")
            elif health.status == 'degraded':
                print(f"⚠️ {health.response_time_ms}ms - {health.last_error}")
            else:
                print(f"❌ {health.last_error}")
            
            time.sleep(0.5)
        
        # 生成报告
        healthy_count = sum(1 for h in health_list if h.status == 'healthy')
        degraded_count = sum(1 for h in health_list if h.status == 'degraded')
        down_count = sum(1 for h in health_list if h.status == 'down')
        
        avg_response = int(sum(h.response_time_ms for h in health_list) / len(health_list)) if health_list else 0
        avg_success = sum(h.success_rate for h in health_list) / len(health_list) if health_list else 0
        
        report = HealthReport(
            check_time=datetime.now().isoformat(),
            total_sources=len(health_list),
            healthy_count=healthy_count,
            degraded_count=degraded_count,
            down_count=down_count,
            avg_response_time=avg_response,
            avg_success_rate=avg_success,
            sources=health_list,
        )
        
        # 保存报告
        self._save_report(report)
        
        # 显示汇总
        print("\n" + "="*80)
        print("📊 健康状态汇总")
        print("="*80)
        print(f"检查时间：{report.check_time}")
        print(f"总数据源：{report.total_sources}")
        print(f"✅ 健康：{report.healthy_count}")
        print(f"⚠️ 降级：{report.degraded_count}")
        print(f"❌ 宕机：{report.down_count}")
        print(f"平均响应：{report.avg_response_time}ms")
        print(f"平均成功率：{report.avg_success_rate:.1f}%")
        
        return report
    
    def _save_report(self, report: HealthReport):
        """保存报告"""
        with open(self.health_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
    
    def get_report(self) -> Optional[HealthReport]:
        """获取最新报告"""
        if self.health_file.exists():
            with open(self.health_file, 'r') as f:
                data = json.load(f)
            return HealthReport(**data)
        return None
    
    def generate_alert(self, health: DataSourceHealth) -> Optional[str]:
        """生成告警消息"""
        if health.status == 'down':
            return f"🚨 {health.name} 宕机\n错误：{health.last_error}"
        
        if health.status == 'degraded':
            if health.response_time_ms > self.thresholds['response_time_critical']:
                return f"⚠️ {health.name} 响应过慢\n响应时间：{health.response_time_ms}ms"
            
            if health.success_rate < self.thresholds['success_rate_critical']:
                return f"⚠️ {health.name} 成功率过低\n成功率：{health.success_rate:.1f}%"
        
        return None
    
    def send_alert(self, message: str, webhook: str = None):
        """发送告警（支持多渠道）"""
        print(f"\n🚨 告警：{message}")
        
        if webhook:
            # 推送到企业微信
            try:
                payload = {
                    'msgtype': 'text',
                    'text': {'content': message}
                }
                resp = requests.post(webhook, json=payload, timeout=5)
                result = resp.json()
                
                if result.get('errcode') == 0:
                    print("✅ 告警已推送到企业微信")
                else:
                    print(f"❌ 推送失败：{result}")
            except Exception as e:
                print(f"❌ 推送异常：{e}")
        
        # 同时记录到日志文件
        self._log_alert(message)
    
    def _log_alert(self, message: str):
        """记录告警到日志文件"""
        log_file = self.cache_dir / 'health_alerts.log'
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(f"📝 告警已记录到：{log_file}")
    
    def send_health_report(self, report: HealthReport, webhook: str = None):
        """发送健康报告"""
        lines = [
            "📊 数据源健康报告",
            f"检查时间：{report.check_time}",
            "",
            f"总数据源：{report.total_sources}",
            f"✅ 健康：{report.healthy_count}",
            f"⚠️ 降级：{report.degraded_count}",
            f"❌ 宕机：{report.down_count}",
            "",
            f"平均响应：{report.avg_response_time}ms",
            f"平均成功率：{report.avg_success_rate:.1f}%",
            "",
            "详细状态:",
        ]
        
        for source in report.sources:
            icon = "✅" if source.status == 'healthy' else "⚠️" if source.status == 'degraded' else "❌"
            lines.append(f"{icon} {source.name}: {source.status} ({source.response_time_ms}ms)")
        
        message = "\n".join(lines)
        
        if webhook:
            self.send_alert(message, webhook)
        else:
            print("\n" + message)


# CLI 入口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据源健康监控')
    parser.add_argument('--check', action='store_true', help='检查所有数据源')
    parser.add_argument('--report', action='store_true', help='显示最新报告')
    parser.add_argument('--watch', action='store_true', help='持续监控')
    parser.add_argument('--interval', type=int, default=300, help='监控间隔（秒）')
    parser.add_argument('--webhook', type=str, help='告警 Webhook')
    
    args = parser.parse_args()
    
    monitor = DataSourceHealthMonitor()
    
    if args.check:
        monitor.check_all_sources()
    
    elif args.report:
        report = monitor.get_report()
        if report:
            print(f"\n📊 最新健康报告")
            print(f"检查时间：{report.check_time}")
            print(f"健康：{report.healthy_count}/{report.total_sources}")
            print(f"平均响应：{report.avg_response_time}ms")
        else:
            print("❌ 无历史报告")
    
    elif args.watch:
        print(f"👁️ 开始持续监控（间隔{args.interval}秒）")
        print("按 Ctrl+C 停止")
        
        try:
            while True:
                report = monitor.check_all_sources()
                
                # 检查告警
                for health in report.sources:
                    alert = monitor.generate_alert(health)
                    if alert:
                        monitor.send_alert(alert, args.webhook)
                
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\n👋 停止监控")
