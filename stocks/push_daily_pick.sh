#!/bin/bash
# 每日选股推送脚本 - 极简策略
# 运行时间: 每个交易日 20:00

cd /home/admin/.openclaw/workspace/stocks

# 运行选股
output=$(python3 daily_stock_pick.py 2>/dev/null)

# 提取推送消息（从 PUSH_MESSAGE 开始）
msg=$(echo "$output" | sed -n '/^📊 极简策略选股/,/^⚠️ 风险提示/p')

# 推送到微信
if [ -n "$msg" ]; then
    openclaw message send \
        --to "o9cq809xA2SNsQbJ5C02yWacjepU@im.wechat" \
        --channel "openclaw-weixin" \
        --message "$msg"
    
    echo "推送成功: $(date)"
else
    echo "无消息推送"
fi