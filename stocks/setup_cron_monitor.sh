#!/bin/bash
# 数据源健康监控 - 快速配置脚本
# 监控间隔：1 小时

echo "=============================================="
echo "📋 数据源健康监控 - Cron 配置"
echo "=============================================="
echo ""

# 工作目录
WORK_DIR="/home/admin/.openclaw/workspace/stocks"
WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=76babaf7-4a40-4e24-b547-98e9798baff5"

echo "工作目录：$WORK_DIR"
echo "Webhook: $WEBHOOK"
echo ""

# 备份现有 crontab
echo "📦 备份现有 crontab..."
crontab -l > ~/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || echo "无现有 crontab"
echo "✅ 备份完成"
echo ""

# 创建新的 crontab 配置
echo "📝 创建新的 crontab 配置..."
TEMP_CRON=$(mktemp)

# 添加数据源监控任务
cat > $TEMP_CRON << EOF
# 数据源健康监控 - 每小时检查一次
0 * * * * cd $WORK_DIR && python3 datasource_health_monitor.py --check --webhook "$WEBHOOK" >> logs/health_check.log 2>&1

# 数据源健康监控 - 每日报告（每天早上 9 点）
0 9 * * * cd $WORK_DIR && python3 datasource_health_monitor.py --report --webhook "$WEBHOOK" >> logs/health_report.log 2>&1

# 日志轮转 - 每天凌晨 2 点
0 2 * * * find $WORK_DIR/cache -name "*.log" -size +10M -exec mv {} {}.bak \;
EOF

echo "✅ crontab 配置创建完成"
echo ""

# 显示配置内容
echo "📋 Crontab 配置内容:"
echo "-------------------------------------------"
cat $TEMP_CRON
echo "-------------------------------------------"
echo ""

# 询问是否应用
read -p "是否应用此配置？(y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 安装 crontab
    crontab $TEMP_CRON
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Cron 配置成功应用!"
        echo ""
        echo "📊 配置摘要:"
        echo "  - 检查频率：每小时一次（整点执行）"
        echo "  - 每日报告：每天早上 9 点"
        echo "  - 日志轮转：每天凌晨 2 点"
        echo ""
        echo "🔍 查看配置:"
        echo "  crontab -l"
        echo ""
        echo "📝 查看日志:"
        echo "  tail -f $WORK_DIR/logs/health_check.log"
        echo ""
        echo "🧪 手动测试:"
        echo "  cd $WORK_DIR && python3 datasource_health_monitor.py --check --webhook \"$WEBHOOK\""
        echo ""
    else
        echo "❌ Cron 配置失败!"
        exit 1
    fi
else
    echo "❌ 已取消配置"
    echo ""
    echo "手动配置方法:"
    echo "  1. 运行：crontab -e"
    echo "  2. 添加以下内容:"
    echo ""
    echo "0 * * * * cd $WORK_DIR && python3 datasource_health_monitor.py --check --webhook \"$WEBHOOK\" >> logs/health_check.log 2>&1"
    echo "0 9 * * * cd $WORK_DIR && python3 datasource_health_monitor.py --report --webhook \"$WEBHOOK\" >> logs/health_report.log 2>&1"
    echo ""
fi

# 清理临时文件
rm -f $TEMP_CRON

echo "=============================================="
echo "✅ 配置完成"
echo "=============================================="
