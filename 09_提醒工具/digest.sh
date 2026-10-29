#!/bin/bash
# 今日摘要生成器（digest.sh）—— 微信短摘要，手机一屏可读完
# 结构：日期 → 今日剩余提醒（最多3条）→ 明天（最多2条）→ 今日复习1条 → 互动一句
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TODAY="$(date +%Y-%m-%d)"
TOMORROW="$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d '+1 day' +%Y-%m-%d)"
NOW_HM="$(date +%H:%M)"
PLAN="$ROOT/00_每日作业与待办/2026-11/学习计划_期中复习.md"
SUPP="$HERE/今日补充_${TODAY}.txt"

case "$(date +%u)" in
  1) WEEK="周一";; 2) WEEK="周二";; 3) WEEK="周三";; 4) WEEK="周四";;
  5) WEEK="周五";; 6) WEEK="周六";; *) WEEK="周日";;
esac

trim() {   # $1=text $2=max
  local s="$1" max="${2:-34}" head
  # 1) 若写了「短标题｜全文」，只取短标题
  if [ "${s#*‖}" != "$s" ]; then
    s="${s%%‖*}"
  else
    s="$(printf '%s' "$s" | sed -e 's/^[ ·	]*//' -e 's/。$//')"
    head="${s%%[。；;]*}"
    if [ -n "$head" ] && [ "${#head}" -le "$max" ]; then s="$head"; fi
  fi
  if [ "${#s}" -gt "$max" ]; then s="${s:0:$max}…"; fi
  printf '%s' "$s"
}

out=""
add() { out="${out}${1}"$'\n'; }

add "🌙 $(date '+%m-%d') ${WEEK} · 今日提醒"

if [ -f "$SUPP" ]; then
  n=0
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    [ "$n" -ge 2 ] && break
    add "📌 $(trim "$line" 42)"
    n=$((n+1))
  done < "$SUPP"
fi

# 今天剩余（最多 3 条）
today_items=""
if [ -f "$HERE/reminders.tsv" ]; then
  while IFS=$'\t' read -r when text; do
    case "$when" in \#*|""|"@daily"*) continue;; esac
    case "$when" in
      "$TODAY "*) hm="${when#* }";;
      *) continue;;
    esac
    [ "$hm" \< "$NOW_HM" ] && continue
    today_items="${today_items}${hm}§${text}"$'\n'
  done < "$HERE/reminders.tsv"
  today_items="$(printf '%s' "$today_items" | sort | head -3)"
fi

if [ -n "$today_items" ]; then
  add ""
  add "今天还有"
  while IFS='§' read -r hm text; do
    [ -z "$hm" ] && continue
    add "· ${hm} $(trim "$text")"
  done <<< "$today_items"
fi

# 明天（最多 2 条）
tom_items=""
if [ -f "$HERE/reminders.tsv" ]; then
  while IFS=$'\t' read -r when text; do
    case "$when" in \#*|""|"@daily"*) continue;; esac
    case "$when" in
      "$TOMORROW "*) :;;
      *) continue;;
    esac
    tom_items="${tom_items}${when#* }§${text}"$'\n'
  done < "$HERE/reminders.tsv"
  tom_items="$(printf '%s' "$tom_items" | sort | head -2)"
fi

if [ -n "$tom_items" ]; then
  add ""
  add "明天"
  while IFS='§' read -r hm text; do
    [ -z "$hm" ] && continue
    add "· ${hm} $(trim "$text")"
  done <<< "$tom_items"
fi

# 今日复习（1 条）—— 只取“每日复习安排”表里以「| 月-日 | 周X |」开头的那一行
if [ -f "$PLAN" ]; then
  md="${TODAY#*-}"
  line=$(grep -E "^\| ${md} \| 周" "$PLAN" | head -1)
  if [ -n "$line" ]; then
    subj=$(printf '%s' "$line" | awk -F'|' '{gsub(/^ +| +$/,"",$4); print $4}')
    task=$(printf '%s' "$line" | awk -F'|' '{gsub(/^ +| +$/,"",$5); print $5}')
    add ""
    add "📚 复习｜${subj}"
    add "· $(trim "$task" 44)"
  fi
fi

add ""
add "回一句就能补今天的通知"

printf '%s' "$out"
