#!/bin/bash
# 股票数据获取进度 - 每 10 分钟自动汇报

LOG_FILE="/home/admin/.openclaw/workspace/stocks/fetch_continue.log"
DATA_DIR="/home/admin/.openclaw/workspace/stocks/data_tushare"

while true; do
    sleep 600  # 10 分钟
    
    # 获取进度
    PID=$(pgrep -f "python3 fetch_continue.py" | head -1)
    COUNT=$(ls "$DATA_DIR"/*.csv 2>/dev/null | wc -l)
    
    if [ -f "$LOG_FILE" ]; then
        PROGRESS=$(grep "进度：" "$LOG_FILE" | tail -1)
    else
        PROGRESS="无数据"
    fi
    
    SIZE=$(du -sh "$DATA_DIR" 2>/dev/null | cut -f1)
    
    # 发送汇报
    MESSAGE="📊 股票数据进度

✅ 进程：$([ -n "$PID" ] && echo "运行中 (PID: $PID)" || echo "已停止")
📈 已获取：$COUNT 只
$PROGRESS
💾 数据大小：$SIZE

(自动汇报)"
    
    # 通过 openclaw 发送消息 (需要配置 channel)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $MESSAGE" >> /home/admin/.openclaw/workspace/stocks/auto_reports.log
done
