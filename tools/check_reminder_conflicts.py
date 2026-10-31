#!/usr/bin/env python3
"""提醒表冲突检查：同刻重复 / 间隔过短 / 已过期。

用法：
    python3 tools/check_reminder_conflicts.py            # 检查全部
    python3 tools/check_reminder_conflicts.py --date 2026-11-01
    python3 tools/check_reminder_conflicts.py --today 2026-10-31

只读，不修改任何文件。退出码恒为 0，问题以标记列出。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REMINDERS = Path(__file__).resolve().parent.parent / "09_提醒工具" / "reminders.tsv"
MIN_GAP_MIN = 15  # 间隔小于该值视为过短

LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})\s+(.+)$")


def parse(path: Path) -> list[tuple[datetime, str]]:
    items: list[tuple[datetime, str]] = []
    if not path.exists():
        print(f"[ERR] 找不到提醒表：{path}")
        return items
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = LINE_RE.match(line)
        if not m:
            print(f"[WARN] 第 {lineno} 行格式无法解析，已跳过：{raw[:60]}")
            continue
        day, clock, body = m.groups()
        try:
            when = datetime.strptime(f"{day} {clock}", "%Y-%m-%d %H:%M")
        except ValueError:
            print(f"[WARN] 第 {lineno} 行时间非法，已跳过：{raw[:60]}")
            continue
        title = body.split("‖")[0].strip()
        items.append((when, title))
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="只检查某一天，如 2026-11-01")
    ap.add_argument("--today", help="用于判断过期的“今天”，默认取系统日期")
    args = ap.parse_args()

    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else datetime.now().date()
    items = parse(REMINDERS)

    by_day: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for when, title in items:
        if args.date and when.strftime("%Y-%m-%d") != args.date:
            continue
        by_day[when.strftime("%Y-%m-%d")].append((when, title))

    problems = 0

    # 1) 已过期
    expired = [(w, t) for w, t in items if w.date() < today]
    if expired and not args.date:
        problems += len(expired)
        print(f"[过期·不追 v0.13] {len(expired)} 条已过截止，无需处理（可清理）：")
        for w, t in expired[:5]:
            print(f"    {w:%Y-%m-%d %H:%M}  {t}")
        if len(expired) > 5:
            print(f"    ……另有 {len(expired) - 5} 条（不影响判断，已按 v0.13 视为不追）")

    # 2) 同日：同刻重复 + 间隔过短
    for day in sorted(by_day):
        rows = sorted(by_day[day], key=lambda x: x[0])
        for i in range(1, len(rows)):
            prev_t, prev_title = rows[i - 1]
            cur_t, cur_title = rows[i]
            gap = (cur_t - prev_t).total_seconds() / 60
            if gap == 0:
                problems += 1
                print(f"[同刻重复] {day} {cur_t:%H:%M}  「{prev_title}」 ↔ 「{cur_title}」")
            elif gap < MIN_GAP_MIN:
                problems += 1
                print(
                    f"[间隔过短] {day} {prev_t:%H:%M}→{cur_t:%H:%M} 仅 {gap:.0f} 分钟："
                    f"「{prev_title}」 ↔ 「{cur_title}」"
                )

    checked = sum(len(v) for v in by_day.values())
    if problems == 0:
        scope = f"{args.date} 当天 " if args.date else ""
        print(f"[OK] {scope}共检查 {checked} 条提醒，未发现同刻重复、间隔过短或过期项。")
    else:
        print(f"\n共发现 {problems} 处问题。建议：冲突项错开 ≥{MIN_GAP_MIN} 分钟；过期项按 v0.13 不追。")
    return 0


if __name__ == "__main__":
    sys.exit(main())