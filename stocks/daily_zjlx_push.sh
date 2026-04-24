#!/bin/bash
# 每日资金流排行推送脚本
# 使用方法: ./daily_zjlx_push.sh

STOCKS_DIR="/Users/taopeng/.openclaw/workspace/stocks"
DATA_DIR="$STOCKS_DIR/data"

echo "=========================================="
echo "📊 每日资金流排行推送"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 1. 获取资金流排行
cd "$STOCKS_DIR"
python3 zjlx_auto_fetcher.py --json > "$DATA_DIR/zjlx_today.json"

# 检查是否成功
if [ $? -ne 0 ]; then
    echo "❌ 获取失败，尝试读取缓存"
fi

# 2. 运行选股系统V4
python3 stock_selector_v4.py --no-fetch --json > "$DATA_DIR/selection_today.json"

# 3. 解析结果生成摘要
SUMMARY=$(python3 -c "
import json
import sys

# 读取选股结果
with open('$DATA_DIR/selection_today.json', 'r') as f:
    result = json.load(f)

# 生成摘要
msg = '📊 今日资金流排行分析\\n\\n'

# TOP5推荐
msg += '🔥 强烈推荐 TOP5:\\n'
for s in result.get('强烈推荐', [])[:5]:
    msg += f\"  {s.get('代码')} {s.get('名称')}\\n"
    msg += f\"  流入: {s.get('主力净流入')}, 占比: {s.get('主力占比')}\\n\\n"

# 止损提醒
need_stop = result.get('需止损股票', [])
if need_stop:
    msg += '🚨 止损提醒:\\n'
    for s in need_stop:
        msg += f\"  {s.get('代码')} {s.get('名称')}: {s.get('建议')}\\n"

print(msg)
")

# 4. 推送到企业微信/钉钉（如果有配置）
PUSH_CONFIG="$STOCKS_DIR/push_config.json"

if [ -f "$PUSH_CONFIG" ]; then
    echo "📤 推送消息..."
    
    # 使用之前的推送脚本
    python3 "$STOCKS_DIR/push_selection.py" "$DATA_DIR/selection_today.json"
    
    echo "✅ 推送完成"
else
    echo "⚠️ 无推送配置，仅保存数据"
    echo "$SUMMARY"
fi

echo "=========================================="
echo "✅ 任务完成"
echo "=========================================="

# 保存日志
echo "$(date '+%Y-%m-%d %H:%M:%S') - 资金流排行获取完成" >> "$STOCKS_DIR/zjlx_cron.log"