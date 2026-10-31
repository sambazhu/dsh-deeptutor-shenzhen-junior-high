#!/usr/bin/env bash
# ==============================================================================
# 监听台账题库变动，自动同步到 DeepTutor 知识库 qiuyu-wrongbook
# ==============================================================================
set -euo pipefail

export PATH="/Users/zhuqiuyu/.local/bin:/Users/zhuqiuyu/.deeptutor-venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export DEEPTUTOR_HOME="/Users/zhuqiuyu/.deeptutor"
export DEEPTUTOR_LOCAL_BIN="/Users/zhuqiuyu/.local/bin/deeptutor"

LOG_DIR="/Users/zhuqiuyu/.deeptutor/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/ledger_sync.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 检测到台账题库更新，开始自动入库..." >> "${LOG_FILE}"

/Users/zhuqiuyu/.deeptutor-venv/bin/python /Users/zhuqiuyu/朱秋宇/朱秋宇初一学习台账/tools/sync_to_deeptutor.py --wrongbook >> "${LOG_FILE}" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 错题台账自动同步完成。" >> "${LOG_FILE}"
