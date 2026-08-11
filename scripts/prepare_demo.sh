#!/usr/bin/env bash
# 一键检查 / 拉起 SemAlign 演示环境
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FRONTEND_PORT="${FRONTEND_PORT:-8080}"
HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
HOST_IP="${HOST_IP:-127.0.0.1}"

if [ ! -f .env ]; then
  cp .env.docker.example .env
  echo "已创建 .env，请按需填写 DEEPSEEK_API_KEY / SECRET_KEY"
fi

echo "==> 启动 SemAlign（前端 + 后端）..."
docker compose up -d

echo "==> 等待健康检查..."
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${FRONTEND_PORT}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "==> 验证登录..."
LOGIN_CODE="$(curl -s -o /tmp/semalign_login.json -w '%{http_code}' \
  -X POST "http://127.0.0.1:${FRONTEND_PORT}/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}')"

if [ "$LOGIN_CODE" != "200" ]; then
  echo "登录失败 (HTTP $LOGIN_CODE)，请检查后端日志: docker compose logs backend"
  exit 1
fi

echo ""
echo "============================================"
echo " SemAlign 演示环境已就绪"
echo "============================================"
echo " 本机访问 : http://localhost:${FRONTEND_PORT}  或  http://localhost"
echo " 局域网   : http://${HOST_IP}  或  http://${HOST_IP}:${FRONTEND_PORT}"
echo " 备用端口 : http://${HOST_IP}:18080"
echo " 账号密码 : admin / admin123"
echo " API 文档 : http://${HOST_IP}/docs"
echo ""
echo " 建议演示路径："
echo "  1. 工作台        /"
echo "  2. 标准数据库    /database"
echo "  3. 智能检索      /search   （关键词：数据交换）"
echo "  4. 标准对齐结果  /alignment/result?taskId=67"
echo "  5. 对齐助手对话  /alignment"
echo ""
echo " SonarQube（可选）: http://${HOST_IP}:9000  账号见 sonar 配置"
echo "============================================"
