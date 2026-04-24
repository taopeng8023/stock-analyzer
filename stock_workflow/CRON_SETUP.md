# 股票筛选与多因子决策工作流 - Cron 配置

## 每日调度配置

### 交易时间调度（周一至周五）

```bash
# 编辑 crontab
crontab -e

# 添加以下配置（北京时间）

# 15:30 启动工作流（收盘后）
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stock_workflow && /usr/bin/python3.8 workflow.py >> logs/cron.log 2>&1

# 或者使用 scheduler.py
30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stock_workflow && /usr/bin/python3.8 scheduler.py >> logs/cron.log 2>&1
```

### 模型训练调度（每周日）

```bash
# 每周日 10:00 重新训练模型
0 10 * * 0 cd /home/admin/.openclaw/workspace/stock_workflow && /usr/bin/python3.8 modules/model_trainer.py >> logs/training.log 2>&1
```

### 日志清理（每天）

```bash
# 每天凌晨 2 点清理 30 天前的日志
0 2 * * * find /home/admin/.openclaw/workspace/stock_workflow/logs -name "*.log" -mtime +30 -delete
```

## Airflow DAG 配置（可选）

```python
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'stock_workflow',
    'depends_on_past': False,
    'start_date': datetime(2026, 3, 19),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'stock_workflow_daily',
    default_args=default_args,
    description='股票筛选与多因子决策工作流',
    schedule_interval='30 15 * * 1-5',
    catchup=False,
)

run_workflow = BashOperator(
    task_id='run_workflow',
    bash_command='cd /home/admin/.openclaw/workspace/stock_workflow && python3.8 workflow.py',
    dag=dag,
)
```

## 系统服务配置（Systemd）

### 创建服务文件

```bash
sudo nano /etc/systemd/system/stock-workflow.service
```

```ini
[Unit]
Description=Stock Workflow Daily Job
After=network.target

[Service]
Type=oneshot
User=admin
WorkingDirectory=/home/admin/.openclaw/workspace/stock_workflow
ExecStart=/usr/bin/python3.8 workflow.py
StandardOutput=append:/home/admin/.openclaw/workspace/stock_workflow/logs/systemd.log
StandardError=append:/home/admin/.openclaw/workspace/stock_workflow/logs/systemd.log

[Install]
WantedBy=multi-user.target
```

### 创建定时器

```bash
sudo nano /etc/systemd/system/stock-workflow.timer
```

```ini
[Unit]
Description=Run Stock Workflow Daily at 15:30
Requires=stock-workflow.service

[Timer]
OnCalendar=*-*-* 15:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 启用服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启用定时器
sudo systemctl enable stock-workflow.timer
sudo systemctl start stock-workflow.timer

# 查看状态
sudo systemctl status stock-workflow.timer
```

## 验证配置

```bash
# 查看 cron 日志
tail -f /var/log/cron.log

# 查看工作流日志
tail -f /home/admin/.openclaw/workspace/stock_workflow/logs/cron.log

# 手动测试运行
cd /home/admin/.openclaw/workspace/stock_workflow
python3.8 scheduler.py
```

## 注意事项

1. **时区**：确保系统时区为 Asia/Shanghai
   ```bash
   timedatectl set-timezone Asia/Shanghai
   ```

2. **Python 路径**：确认 Python 路径正确
   ```bash
   which python3.8
   ```

3. **权限**：确保脚本有执行权限
   ```bash
   chmod +x workflow.py scheduler.py
   ```

4. **依赖**：确保所有依赖已安装
   ```bash
   pip3 install -r requirements.txt
   ```

5. **日志轮转**：配置 logrotate 防止日志过大
   ```bash
   sudo nano /etc/logrotate.d/stock-workflow
   ```
   
   ```
   /home/admin/.openclaw/workspace/stock_workflow/logs/*.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
   }
   ```
