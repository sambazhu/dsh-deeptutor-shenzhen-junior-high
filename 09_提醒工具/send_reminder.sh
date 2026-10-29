#!/bin/bash
# 微信提醒发送器 —— 通过 DSH-IM 主动投递接口发一条微信文字，同时发一条 macOS 桌面通知作为后备
# 用法：./send_reminder.sh "要发送的文字"
# 依赖：本机 DSH 桌面应用在运行；微信机器人已保存投递目标（botId + targetId 见下方常量）
# 注意：日志留在本目录（工作区内），不写 ~/.dsh 或 ~/Library —— 实测这两处被沙箱禁止写入
set -uo pipefail

TEXT="${1:-}"
if [ -z "$TEXT" ]; then
  echo "用法: $0 \"要发送的文字\"" >&2
  exit 2
fi

BOT_ID="wx_300d95b7e71db673486ee36b"
TARGET_ID="tgt_5695856b51528348"
# 自动发现当前 DSH Host 的本地监听端口。DSH 升级/重启后端口可能变化，不能再写死 19387。
# 优先使用 DSH_WEB_PORT 环境变量；否则从 lsof 里找 DeepSeek 进程的 TCP 监听端口。
detect_dsh_port() {
  if [ -n "${DSH_WEB_PORT:-}" ]; then printf '%s' "$DSH_WEB_PORT"; return; fi
  local p
  p=$(/usr/sbin/lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null \
      | awk '$1 ~ /^DeepSeek/ {print $9}' \
      | sed -n 's/.*:\([0-9][0-9]*\)$/\1/p' \
      | head -n 1)
  if [ -n "$p" ]; then printf '%s' "$p"; else printf '19387'; fi
}
PORT="$(detect_dsh_port)"
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG="$HERE/sent.log"

# 1) 微信主动投递：用 python 生成 JSON，保证中文和引号安全
BODY=$(TEXT="$TEXT" BOT_ID="$BOT_ID" TARGET_ID="$TARGET_ID" python3 - <<'PY'
import json, os
print(json.dumps({
    "botId": os.environ["BOT_ID"],
    "targetId": os.environ["TARGET_ID"],
    "text": os.environ["TEXT"],
}, ensure_ascii=False))
PY
)
RESP=$(curl -s --max-time 20 -X POST "http://127.0.0.1:${PORT}/api/dsh-im/delivery/messages" \
  -H 'Content-Type: application/json' --data "$BODY" 2>&1) || RESP="curl-failed"

# 2) 桌面通知（后备；失败不影响主链路）
SAFE="${TEXT//\"/}"
osascript -e "display notification \"${SAFE}\" with title \"秋宇学习台账 · 提醒\"" >/dev/null 2>&1 || true

# 3) 记录（追加，不删除旧行）
printf '%s\t%s\t%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$RESP" "$TEXT" >> "$LOG"

echo "$RESP"
[ "$RESP" = '{"sent":true}' ]
