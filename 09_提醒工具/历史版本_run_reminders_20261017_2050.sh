#!/bin/bash
# 提醒守护进程（run_reminders.sh）
# 读取同目录 reminders.tsv，到点调用 send_reminder.sh 发微信。
# 时间列支持两种写法：
#   1) 一次性：YYYY-MM-DD HH:MM      （到点发一次，记录进 fired.log 去重）
#   2) 每天重复：@daily HH:MM        （每天到点发一次，当天只发一次，记录进 fired.log）
# 文字列支持：
#   普通文字            → 原样发送
#   @digest             → 调用同目录 digest.sh 动态生成“今日摘要”再发送（失败则回退到默认提醒）
# 特性：持续轮询、按分钟去重、失败重试 3 次、每 5 分钟心跳、记录进 fired.log / sent.log。
# 用法：nohup ./run_reminders.sh > daemon.log 2>&1 &
# 停止：./stop_reminders.sh
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SCHEDULE="$HERE/reminders.tsv"
SENDER="$HERE/send_reminder.sh"
DIGEST="$HERE/digest.sh"
FIRED="$HERE/fired.log"
HEARTBEAT="$HERE/heartbeat.txt"
PIDFILE="$HERE/daemon.pid"

echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"; echo "$(date "+%F %T")	daemon stopped" >> "$HEARTBEAT"; exit 0' TERM INT
echo "$(date "+%F %T")	daemon started pid=$$" >> "$HEARTBEAT"

send_with_retry() {   # $1=text
  local text="$1" ok=0
  for attempt in 1 2 3; do
    if "$SENDER" "$text" >/dev/null 2>&1; then ok=1; break; fi
    sleep 20
  done
  [ $ok -eq 1 ]
}

last_beat=0
while :; do
  now=$(date "+%s")
  now_min=$(date "+%Y-%m-%d %H:%M")
  now_hm=$(date "+%H:%M")
  today=$(date "+%Y-%m-%d")

  if [ $(( now - last_beat )) -ge 300 ]; then
    echo "$(date "+%F %T")	alive" >> "$HEARTBEAT"
    last_beat=$now
  fi

  if [ -f "$SCHEDULE" ]; then
    while IFS=$'\t' read -r when text; do
      [ -z "${when:-}" ] && continue
      case "$when" in \#*) continue;; esac
      [ -z "${text:-}" ] && continue

      due=0
      fired_key=""
      case "$when" in
        "@daily "*)
          hm="${when#@daily }"
          if [ "$hm" = "$now_hm" ]; then
            due=1
            fired_key="$today $hm"
          fi
          ;;
        *)
          if [ "$when" = "$now_min" ]; then
            due=1
            fired_key="$when"
          fi
          ;;
      esac

      [ $due -eq 1 ] || continue
      if grep -qF "${fired_key}"$'\t'"${text}" "$FIRED" 2>/dev/null; then continue; fi

      body="$text"
      if [ "$text" = "@digest" ]; then
        if [ -x "$DIGEST" ]; then
          body="$("$DIGEST" 2>/dev/null)"
        fi
        if [ -z "$body" ]; then
          body="【今日摘要】摘要生成失败（digest.sh 未产出内容）。请直接查看台账：00_每日作业与待办/$(date +%Y-%m)/$(date +%Y-%m-%d)_*.md"
        fi
      fi

      if send_with_retry "$body"; then
        printf '%s\t%s\t%s\n' "$fired_key" "$text" "sent" >> "$FIRED"
      else
        printf '%s\t%s\t%s\n' "$fired_key" "$text" "FAILED" >> "$FIRED"
      fi
    done < "$SCHEDULE"
  fi
  sleep 20
done
