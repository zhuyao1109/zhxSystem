#!/bin/bash
set -euo pipefail

mkdir -p /app/data/uploads /app/data/texts /app/data/images /app/data/chroma_db

# 首次启动时创建默认管理员（admin / admin123），已存在则跳过
python scripts/init_user.py || true

exec gunicorn main:app \
  --workers 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 180 \
  --access-logfile - \
  --error-logfile -
