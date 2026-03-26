#!/usr/bin/env python3
"""
定时调度脚本
使用 cron 或 Airflow 调度工作流
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_workflow():
    """运行工作流"""
    print("="*60)
    print("🕐 定时调度启动")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    workflow_path = Path(__file__).parent / 'workflow.py'
    
    try:
        # 运行工作流
        result = subprocess.run(
            [sys.executable, str(workflow_path)],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 分钟超时
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"❌ 工作流执行失败：{result.stderr}")
            return False
        
        print("✅ 工作流执行成功")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ 工作流执行超时")
        return False
    except Exception as e:
        print(f"❌ 执行异常：{e}")
        return False


if __name__ == '__main__':
    success = run_workflow()
    sys.exit(0 if success else 1)
