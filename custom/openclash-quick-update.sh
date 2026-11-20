#!/bin/sh
# OpenClash 模板订阅快速更新（在路由器本地运行）
# 用法: sh /root/oc-quick-update.sh [哨兵组名]
#   哨兵组名默认 WireGuard：更新完成后在运行内核中必须能找到该分组，否则判定失败
# 流程: 更新订阅 -> 等待配置重新生成 -> 重启内核 -> API 校验
# 说明: 全程约 10-30 秒，重启内核时代理中断数秒
# 依赖: /usr/share/openclash/openclash.sh（OpenClash 自带）、curl、uci
# 注意: 重刷固件后 overlay 会清空，需重新 scp 本脚本到 /root/ 并 chmod +x

set -u

SUB="OpenClash"
CFG="/etc/openclash/config/${SUB}.yaml"
SENTINEL="${1:-WireGuard}"
API="http://127.0.0.1:9090"
MARK="/tmp/.oc-update-mark"
LOG="/tmp/oc-update.log"

SECRET="$(uci -q get openclash.config.dashboard_password)"
[ -n "$SECRET" ] || { echo "错误：未取到 dashboard_password"; exit 1; }
[ -f "$CFG" ] || { echo "错误：配置不存在 $CFG"; exit 1; }

echo "[1/4] 更新订阅 $SUB"
rm -f "$MARK"; touch "$MARK"
# 后端（api.asailor.org）按 URL 缓存模板抓取结果，追加时间戳参数强制刷新
BASE_URL="$(uci -q get openclash.@config_subscribe[0].custom_template_url)"
if [ -n "$BASE_URL" ]; then
    CLEAN_URL="$(printf '%s\n' "$BASE_URL" | sed 's/[?&]v=[0-9]*//g')"
    uci set "openclash.@config_subscribe[0].custom_template_url=${CLEAN_URL}?v=$(date +%s)"
    uci commit openclash
    echo "  模板地址已加时间戳，绕过后端缓存"
fi
sh /usr/share/openclash/openclash.sh "$SUB" >"$LOG" 2>&1 || echo "  更新脚本返回非零（详见 $LOG），继续检查配置是否刷新"

echo "[2/4] 等待配置重新生成"
ok=""
i=0
while [ "$i" -lt 90 ]; do
    [ -n "$(find "$CFG" -newer "$MARK" 2>/dev/null)" ] && { ok=1; break; }
    sleep 2; i=$((i + 2))
done
if [ -z "$ok" ]; then
    echo "  配置 90 秒未刷新，终止。更新日志末尾："
    tail -n 5 "$LOG"
    exit 1
fi
echo "  配置已刷新"

echo "[3/4] 重启 OpenClash 内核"
/etc/init.d/openclash restart >/dev/null 2>&1

echo "[4/4] 校验运行内核"
R=""
i=0
while [ "$i" -lt 60 ]; do
    R="$(curl -s -H "Authorization: Bearer $SECRET" "$API/proxies" 2>/dev/null)"
    [ -n "$R" ] && break
    sleep 2; i=$((i + 2))
done
[ -n "$R" ] || { echo "  API 60 秒未就绪，请人工检查内核状态"; exit 1; }

CNT="$(printf '%s\n' "$R" | grep -o '"type":"\(Selector\|URLTest\|Fallback\|LoadBalance\)"' | wc -l)"
if printf '%s\n' "$R" | grep -q "$SENTINEL"; then
    echo "  完成：内核已加载新配置，运行分组 $CNT 个（含 GLOBAL），哨兵「$SENTINEL」在线"
    exit 0
else
    echo "  内核已重启但未找到哨兵「$SENTINEL」：模板可能未含该分组，检查模板地址/后端/转换参数"
    exit 1
fi
