#!/usr/bin/env python3
"""
数据源健康监控器

监控所有数据源的健康状态
- 记录成功/失败次数
- 计算成功率
- 失败告警
- 自动降级
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path


class SourceHealthMonitor:
    """数据源健康监控器"""
    
    def __init__(self):
        self.health_file = Path(__file__).parent / 'cache' / 'source_health.json'
        self.health_file.parent.mkdir(exist_ok=True)
        self.health = self._load_health()
        
        # 告警阈值
        self.alert_threshold = {
            'fail_rate': 0.3,  # 失败率超过 30% 告警
            'consecutive_fails': 5,  # 连续失败 5 次告警
        }
        
        # 需要告警的数据源（最近一次运行）
        self.alerts = []
    
    def _load_health(self) -> dict:
        """加载健康数据"""
        if not self.health_file.exists():
            return {}
        
        try:
            with open(self.health_file, 'r', encoding='utf-8') as f:
                health = json.load(f)
            
            # 清理 7 天前的数据
            cutoff_time = datetime.now() - timedelta(days=7)
            for source in list(health.keys()):
                if 'last_update' in health[source]:
                    last_update = datetime.fromisoformat(health[source]['last_update'])
                    if last_update < cutoff_time:
                        del health[source]
            
            return health
        except Exception as e:
            return {}
    
    def _save_health(self):
        """保存健康数据"""
        try:
            with open(self.health_file, 'w', encoding='utf-8') as f:
                json.dump(self.health, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
    
    def record_success(self, source: str, items_count: int = 0):
        """
        记录成功
        
        Args:
            source: 数据源名称
            items_count: 获取到的数据条数
        """
        if source not in self.health:
            self.health[source] = {
                'success': 0,
                'fail': 0,
                'consecutive_fails': 0,
                'last_success': None,
                'last_fail': None,
                'last_update': None,
                'items_total': 0,
                'items_avg': 0,
            }
        
        health = self.health[source]
        health['success'] += 1
        health['consecutive_fails'] = 0
        health['last_success'] = datetime.now().isoformat()
        health['last_update'] = datetime.now().isoformat()
        health['items_total'] += items_count
        
        # 计算平均获取条数
        total_runs = health['success'] + health['fail']
        if total_runs > 0:
            health['items_avg'] = health['items_total'] / health['success'] if health['success'] > 0 else 0
        
        self._save_health()
    
    def record_fail(self, source: str, error: str = ''):
        """
        记录失败
        
        Args:
            source: 数据源名称
            error: 错误信息
        """
        if source not in self.health:
            self.health[source] = {
                'success': 0,
                'fail': 0,
                'consecutive_fails': 0,
                'last_success': None,
                'last_fail': None,
                'last_update': None,
                'items_total': 0,
                'items_avg': 0,
            }
        
        health = self.health[source]
        health['fail'] += 1
        health['consecutive_fails'] += 1
        health['last_fail'] = datetime.now().isoformat()
        health['last_update'] = datetime.now().isoformat()
        
        # 检查是否需要告警
        self._check_alert(source, error)
        
        self._save_health()
    
    def _check_alert(self, source: str, error: str = ''):
        """检查是否需要告警"""
        health = self.health[source]
        
        # 计算失败率
        total_runs = health['success'] + health['fail']
        fail_rate = health['fail'] / total_runs if total_runs > 0 else 0
        
        # 连续失败告警
        if health['consecutive_fails'] >= self.alert_threshold['consecutive_fails']:
            self.alerts.append({
                'source': source,
                'type': 'consecutive_fails',
                'message': f"数据源 {source} 连续失败 {health['consecutive_fails']} 次",
                'error': error,
                'time': datetime.now().isoformat(),
            })
        
        # 失败率告警
        elif fail_rate >= self.alert_threshold['fail_rate'] and total_runs >= 10:
            self.alerts.append({
                'source': source,
                'type': 'high_fail_rate',
                'message': f"数据源 {source} 失败率过高 ({fail_rate:.1%})",
                'error': error,
                'time': datetime.now().isoformat(),
            })
    
    def get_health_status(self, source: str) -> dict:
        """
        获取数据源健康状态
        
        Args:
            source: 数据源名称
        
        Returns:
            dict: 健康状态
        """
        if source not in self.health:
            return {
                'status': 'unknown',
                'success': 0,
                'fail': 0,
                'fail_rate': 0,
                'consecutive_fails': 0,
            }
        
        health = self.health[source]
        total_runs = health['success'] + health['fail']
        fail_rate = health['fail'] / total_runs if total_runs > 0 else 0
        
        # 判断状态
        if health['consecutive_fails'] >= 5:
            status = 'error'
        elif fail_rate >= 0.5:
            status = 'warning'
        elif fail_rate >= 0.3:
            status = 'degraded'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'success': health['success'],
            'fail': health['fail'],
            'fail_rate': fail_rate,
            'consecutive_fails': health['consecutive_fails'],
            'last_success': health.get('last_success'),
            'last_fail': health.get('last_fail'),
            'items_avg': health.get('items_avg', 0),
        }
    
    def get_all_health(self) -> dict:
        """获取所有数据源健康状态"""
        result = {}
        for source in self.health:
            result[source] = self.get_health_status(source)
        return result
    
    def get_alerts(self) -> list:
        """获取告警列表"""
        return self.alerts
    
    def clear_alerts(self):
        """清空告警"""
        self.alerts = []
    
    def generate_report(self) -> str:
        """生成健康报告"""
        lines = []
        lines.append('='*60)
        lines.append('📊 数据源健康报告')
        lines.append('='*60)
        lines.append(f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append('')
        
        # 按状态分组
        healthy = []
        warning = []
        error = []
        
        for source in sorted(self.health.keys()):
            status = self.get_health_status(source)
            if status['status'] == 'error':
                error.append((source, status))
            elif status['status'] in ['warning', 'degraded']:
                warning.append((source, status))
            else:
                healthy.append((source, status))
        
        # 输出
        if healthy:
            lines.append(f'🟢 健康 ({len(healthy)}个)')
            for source, status in healthy:
                lines.append(f'  ✅ {source}: 成功{status["success"]}次，失败{status["fail"]}次，成功率{1-status["fail_rate"]:.1%}')
            lines.append('')
        
        if warning:
            lines.append(f'🟡 警告 ({len(warning)}个)')
            for source, status in warning:
                lines.append(f'  ⚠️ {source}: 失败率{status["fail_rate"]:.1%}，连续失败{status["consecutive_fails"]}次')
            lines.append('')
        
        if error:
            lines.append(f'🔴 异常 ({len(error)}个)')
            for source, status in error:
                lines.append(f'  ❌ {source}: 连续失败{status["consecutive_fails"]}次，需要检查')
            lines.append('')
        
        # 告警
        if self.alerts:
            lines.append('🚨 告警信息')
            for alert in self.alerts[-5:]:  # 最近 5 条
                lines.append(f'  {alert["time"]}: {alert["message"]}')
            lines.append('')
        
        lines.append('='*60)
        
        return '\n'.join(lines)
    
    def print_health(self):
        """打印健康状态"""
        print(self.generate_report())


# 测试
if __name__ == '__main__':
    monitor = SourceHealthMonitor()
    
    # 模拟记录
    monitor.record_success('今日头条', 20)
    monitor.record_success('华尔街见闻', 15)
    monitor.record_fail('某数据源', '连接超时')
    monitor.record_fail('某数据源', '连接超时')
    monitor.record_fail('某数据源', '连接超时')
    
    # 打印报告
    monitor.print_health()
    
    # 获取单个状态
    status = monitor.get_health_status('今日头条')
    print(f"\n今日头条状态：{status}")
