#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> 检查内核参数 vm.max_map_count（SonarQube 需要 >= 262144）"
CURRENT_MAP_COUNT="$(sysctl -n vm.max_map_count 2>/dev/null || echo 0)"
if [ "$CURRENT_MAP_COUNT" -lt 262144 ]; then
  echo "    当前值: $CURRENT_MAP_COUNT，尝试提升（需要 sudo）..."
  if sudo sysctl -w vm.max_map_count=262144; then
    echo "    已临时设置为 262144"
    echo "    永久生效可执行: echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf"
  else
    echo "    无法自动设置，已启用 SONAR_ES_BOOTSTRAP_CHECKS_DISABLE，通常仍可启动"
  fi
else
  echo "    当前值: $CURRENT_MAP_COUNT，满足要求"
fi

echo "==> 拉取并启动 SonarQube 9.9 LTS + PostgreSQL ..."
docker compose up -d

echo ""
echo "SonarQube 9.9 正在启动，首次约需 2~4 分钟。"
echo "  Web UI   : http://localhost:9000"
echo "  数据库   : PostgreSQL 15（容器 sonarqube-db）"
echo "  默认账号 : admin / admin（首次登录会要求修改密码）"
echo ""
echo "查看日志: docker compose -f $SCRIPT_DIR/docker-compose.yml logs -f sonarqube"
echo "停止服务: docker compose -f $SCRIPT_DIR/docker-compose.yml down"
