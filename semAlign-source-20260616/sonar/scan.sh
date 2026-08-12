#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SONAR_HOST="${SONAR_HOST:-http://localhost:9000}"
# Linux 下 scanner 使用 --network host，应连 localhost；host.docker.internal 通常不可用
if [[ "$SONAR_HOST" == *"host.docker.internal"* ]]; then
  SONAR_HOST="http://localhost:9000"
fi
SONAR_TOKEN="${SONAR_TOKEN:-}"
SONAR_ADMIN_USER="${SONAR_ADMIN_USER:-admin}"
SONAR_ADMIN_PASS="${SONAR_ADMIN_PASS:-admin}"

if [ -z "$SONAR_TOKEN" ]; then
  echo "==> 未设置 SONAR_TOKEN，尝试用 admin 账号自动生成..."
  TOKEN_RESP=$(curl -s -u "${SONAR_ADMIN_USER}:${SONAR_ADMIN_PASS}" \
    -X POST "${SONAR_HOST}/api/user_tokens/generate?name=semalign-scan-$(date +%s)")
  SONAR_TOKEN=$(echo "$TOKEN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || true)
  if [ -z "$SONAR_TOKEN" ]; then
    echo "错误: 无法自动生成 Token，请手动设置 SONAR_TOKEN"
    echo "  或检查 SONAR_ADMIN_USER / SONAR_ADMIN_PASS（默认 admin/admin）"
    exit 1
  fi
fi

echo "==> 使用 SonarScanner 扫描 SemAlign ..."
echo "    SonarQube: $SONAR_HOST"
echo "    项目根目录: $REPO_ROOT"

if [ -f "$REPO_ROOT/semAlign_backend/coverage.xml" ]; then
  python3 "$SCRIPT_DIR/fix_coverage_paths.py"
else
  echo "    警告: 未找到 semAlign_backend/coverage.xml，Sonar 覆盖率将为 0%"
  echo "    请先在 semAlign_backend 目录执行: pytest --cov=. --cov-report=xml"
fi

docker run --rm --network host \
  -e SONAR_HOST_URL="$SONAR_HOST" \
  -v "$REPO_ROOT:/usr/src" \
  -v "$SCRIPT_DIR/sonar-project.properties:/usr/src/sonar-project.properties:ro" \
  sonarsource/sonar-scanner-cli:latest \
  -Dsonar.projectKey=semalign \
  -Dsonar.host.url="$SONAR_HOST" \
  -Dsonar.login="$SONAR_TOKEN"

echo ""
echo "扫描完成，查看报告: ${SONAR_HOST%/}/dashboard?id=semalign"
