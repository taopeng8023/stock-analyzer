#!/bin/bash
# 每 10 分钟汇报数据获取进度

LOG_FILE="/home/admin/.openclaw/workspace/stocks/fetch_continue.log"
DATA_DIR="/home/admin/.openclaw/workspace/stocks/data_tushare"

while true; do
    # 等待 10 分钟
    sleep 600
    
    # 获取最新进度
    if [ -f "$LOG_FILE" ]; then
        LATEST=$(tail -5 "$LOG_FILE" | grep "进度：" | tail -1)
        COUNT=$(ls "$DATA_DIR"/*.csv 2>/dev/null | wc -l)
        
        if [ -n "$LATEST" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 进度汇报：$LATEST (文件数：$COUNT)" >> /home/admin/.openclaw/workspace/stocks/progress_reports.log
        fi
    fi
done
