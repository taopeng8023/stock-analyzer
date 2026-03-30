#!/bin/bash
# 安装定时任务脚本

echo "=== 安装每日数据更新定时任务 ==="
echo ""

# 检查配置文件
if [ ! -f /home/admin/.openclaw/workspace/stocks/push_config.json ]; then
    echo "⚠️  配置文件不存在，请复制模板并编辑:"
    echo "   cp /home/admin/.openclaw/workspace/stocks/push_config.template.json /home/admin/.openclaw/workspace/stocks/push_config.json"
    echo "   vim /home/admin/.openclaw/workspace/stocks/push_config.json"
    echo ""
fi

# 创建日志目录
mkdir -p /home/admin/.openclaw/workspace/stocks/logs

# 添加定时任务
echo "添加定时任务..."
(crontab -l 2>/dev/null | grep -v "update_daily_data.py"; echo "30 15 * * 1-5 cd /home/admin/.openclaw/workspace/stocks && python3 update_daily_data.py >> logs/update_cron.log 2>&1") | crontab -

echo ""
echo "✅ 定时任务已添加"
echo ""
echo "当前定时任务列表:"
crontab -l | grep update_daily_data

echo ""
echo "=== 使用说明 ==="
echo ""
echo "1. 定时任务：每个交易日 15:30 自动执行"
echo "2. 日志文件：/home/admin/.openclaw/workspace/stocks/logs/update_cron.log"
echo "3. 手动执行：cd /home/admin/.openclaw/workspace/stocks && python3 update_daily_data.py"
echo ""
echo "4. 查看定时任务：crontab -l"
echo "5. 删除定时任务：crontab -e (删除对应行)"
echo ""
echo "⚠️  请确保 push_config.json 中配置了微信推送地址"
