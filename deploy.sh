#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo "未找到 .env，从模板创建..."
  cp .env.docker.example .env
  echo "请编辑 .env 中的 SECRET_KEY 后重新运行。"
fi

echo "==> 构建并启动 SemAlign ..."
docker compose up -d --build

echo ""
echo "部署完成。"
echo "  访问地址 : http://localhost:${FRONTEND_PORT:-8080}"
echo "  默认账号 : admin / admin123"
echo "  API 文档 : http://localhost:${FRONTEND_PORT:-8080}/docs"
echo ""
echo "查看日志 : docker compose logs -f"
echo "停止服务 : docker compose down"
