#!/bin/sh
# OpenClash 订阅更新（在路由器本地运行）
# 用法: sh /root/oc-quick-update.sh [检查分组名]
#   更新完成后，内核里必须能找到这个分组，找不到就说明新配置没生效。默认 WireGuard。
# 流程: 更新订阅 -> 等配置重新生成 -> 重启内核 -> 核对分组
# 全程 10-30 秒，重启内核时代理会断几秒。
# 提醒: 重刷固件会清空覆盖层，脚本要重新放回 /root/ 并 chmod +x。

set -u
mkdir -p /tmp/lock  # OpenClash 加锁要写这个目录；tmpfs 清空后缺失会让订阅流程悄悄退出

SUB="OpenClash"
CFG="/etc/openclash/config/${SUB}.yaml"
CHECK_GROUP="${1:-WireGuard}"
API="http://127.0.0.1:9090"
MARK="/tmp/.oc-update-mark"
LOG="/tmp/oc-update.log"
START="$(date +%s)"

line() { printf '%s\n' "──────────────────────────────"; }
elapsed() { echo $(( $(date +%s) - START )); }

echo "OpenClash 订阅更新（检查分组：${CHECK_GROUP}）"
line

SECRET="$(uci -q get openclash.config.dashboard_password)"
[ -n "$SECRET" ] || { echo "没取到 OpenClash 控制台密码，先确认 OpenClash 正常运行。"; exit 1; }
[ -f "$CFG" ] || { echo "找不到订阅文件：$CFG"; echo "先在 OpenClash 里添加这个订阅，再跑一次。"; exit 1; }

printf '1/4  更新订阅    '
rm -f "$MARK"; touch "$MARK"
BASE_URL="$(uci -q get openclash.@config_subscribe[0].custom_template_url)"
if [ -n "$BASE_URL" ]; then
    CLEAN_URL="$(printf '%s\n' "$BASE_URL" | sed 's/[?&]v=[0-9]*//g')"
    uci set "openclash.@config_subscribe[0].custom_template_url=${CLEAN_URL}?v=$(date +%s)"
    uci commit openclash
    echo "好了（已让转换服务重新拉模板）"
else
    echo "好了"
fi

printf '2/4  生成配置    '
sh /usr/share/openclash/openclash.sh "$SUB" >"$LOG" 2>&1 || true
ok=""
i=0
while [ "$i" -lt 90 ]; do
    [ -n "$(find "$CFG" -newer "$MARK" 2>/dev/null)" ] && { ok=1; break; }
    sleep 2; i=$((i + 2))
done
if [ -z "$ok" ]; then
    echo "等太久了"
    line
    echo "90 秒过去，配置文件还是旧的。多半是订阅转换那边出了问题，日志最后几行："
    tail -n 5 "$LOG"
    exit 1
fi
echo "好了（等了 ${i} 秒）"

printf '3/4  重启内核    '
/etc/init.d/openclash restart >/dev/null 2>&1
echo "好了（刚才代理断了几秒）"

printf '4/4  核对分组    '
R=""
i=0
while [ "$i" -lt 60 ]; do
    R="$(curl -s -H "Authorization: Bearer $SECRET" "$API/proxies" 2>/dev/null)"
    [ -n "$R" ] && break
    sleep 2; i=$((i + 2))
done
if [ -z "$R" ]; then
    echo "没应答"
    line
    echo "内核重启后 60 秒还没回应，去 OpenClash 面板看一眼状态。"
    exit 1
fi

CNT="$(printf '%s\n' "$R" | grep -o '"type":"\(Selector\|URLTest\|Fallback\|LoadBalance\)"' | wc -l)"
if printf '%s\n' "$R" | grep -q "$CHECK_GROUP"; then
    echo "共 ${CNT} 个分组，${CHECK_GROUP} 在里面"
    line
    echo "更新完成，用时 $(elapsed) 秒。可以正常上网了。"
    exit 0
else
    echo "少了 ${CHECK_GROUP}"
    line
    echo "内核起来了，但找不到「${CHECK_GROUP}」这个分组。"
    echo "模板可能没带上它，检查订阅地址和转换参数。"
    exit 1
fi
