#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> 停止 SonarQube 9.9 与 PostgreSQL ..."
docker compose down

echo "服务已停止。数据仍保留在 Docker volume 中。"
echo "如需清空数据重新初始化: docker compose down -v"
