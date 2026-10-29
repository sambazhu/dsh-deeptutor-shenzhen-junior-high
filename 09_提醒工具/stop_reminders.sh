#!/bin/bash
# 停止提醒守护进程
HERE="$(cd "$(dirname "$0")" && pwd)"
PIDF="$HERE/daemon.pid"
if [ -f "$PIDF" ]; then
  PID=$(cat "$PIDF")
  if kill -0 "$PID" 2>/dev/null; then
    kill -TERM "$PID" && echo "已停止守护进程 pid=$PID"
  else
    echo "pid 文件存在但进程已不在（pid=$PID），清理 pid 文件"
  fi
  rm -f "$PIDF"
else
  PIDS=$(pgrep -f "run_reminders.sh" 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "未找到 pid 文件，但发现进程：$PIDS，尝试停止"
    kill -TERM $PIDS && echo "已停止"
  else
    echo "没有正在运行的提醒守护进程"
  fi
fi
