#!/bin/bash
# 安装舆情监测定时任务

echo "=========================================="
echo "  安装市场舆情监测定时任务"
echo "=========================================="
echo ""

# 检查配置文件
if [ ! -f /home/admin/.openclaw/workspace/stocks/push_config.json ]; then
    echo "❌ 配置文件不存在"
    exit 1
fi

# 检查 webhook 配置
WEBHOOK=$(python3 -c "import json; c=json.load(open('/home/admin/.openclaw/workspace/stocks/push_config.json')); print(c.get('wecom',{}).get('webhook',''))" 2>/dev/null)
if [ -z "$WEBHOOK" ]; then
    echo "❌ 未配置企业微信 webhook"
    exit 1
fi
echo "✅ 企业微信配置已验证"

# 创建日志目录
mkdir -p /home/admin/.openclaw/workspace/stocks/logs
echo "✅ 日志目录已创建"

# 添加定时任务
echo ""
echo "添加定时任务..."
(crontab -l 2>/dev/null | grep -v "sentiment_monitor_simple.py"; \
echo "0 9 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 sentiment_monitor_simple.py >> logs/sentiment.log 2>&1"; \
echo "0 12 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 sentiment_monitor_simple.py >> logs/sentiment.log 2>&1"; \
echo "30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 sentiment_monitor_simple.py >> logs/sentiment.log 2>&1"; \
echo "0 20 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 sentiment_monitor_simple.py >> logs/sentiment.log 2>&1") | crontab -

echo "✅ 定时任务已添加"
echo ""
echo "当前定时任务列表:"
crontab -l | grep sentiment_monitor
echo ""
echo "=========================================="
echo "  安装完成！"
echo "=========================================="
echo ""
echo "监测时间:"
echo "  - 09:00 (盘前)"
echo "  - 12:00 (午间)"
echo "  - 15:30 (盘后)"
echo "  - 20:00 (晚间)"
echo ""
echo "日志文件：/home/admin/.openclaw/workspace/stocks/logs/sentiment.log"
echo ""
echo "测试推送:"
echo "  cd /home/admin/.openclaw/workspace/stocks"
echo "  python3 sentiment_monitor_simple.py --symbols 000001"
echo ""
