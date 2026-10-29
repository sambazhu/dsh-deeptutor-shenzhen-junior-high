"""以双 fork + setsid 方式启动提醒守护进程，避免终端/工具进程退出时被一起终止。"""
import os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "run_reminders.sh"
LOG = HERE / "daemon.log"

def daemonize():
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    os.chdir(HERE)
    os.umask(0o022)
    logfd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, 0)
    os.dup2(logfd, 1)
    os.dup2(logfd, 2)
    os.close(logfd)
    os.close(devnull)

if not SCRIPT.exists():
    raise SystemExit(f"missing {SCRIPT}")
daemonize()
os.execv("/bin/bash", ["/bin/bash", str(SCRIPT)])
