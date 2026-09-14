#!/usr/bin/env bash
# 从 Git 历史恢复 Docker 运行所需的数据库与模型权重（无需重新导入 PDF）。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 首次全量 push 时写入运行数据的 commit
RUNTIME_COMMIT="${RUNTIME_DATA_COMMIT:-b199667}"

DB_FILE="semAlign_backend/data/semalign.db"
GTE_MODEL="semAlign_backend/models/gte-multilingual-base/model.safetensors"
MINILM_DIR="semAlign_backend/models/models--sentence-transformers--all-MiniLM-L6-v2"

runtime_ready() {
  [[ -f "$DB_FILE" && -f "$GTE_MODEL" && -d "$MINILM_DIR" ]]
}

restore_paths=(
  semAlign_backend/data/semalign.db
  semAlign_backend/data/bm25_chunks.pkl
  semAlign_backend/data/chroma_db
  semAlign_backend/data/texts
  semAlign_backend/data/images
  semAlign_backend/models/gte-multilingual-base
  semAlign_backend/models/models--sentence-transformers--all-MiniLM-L6-v2
)

if runtime_ready; then
  echo "==> 运行数据已就绪，跳过恢复。"
  exit 0
fi

if ! git rev-parse --verify "${RUNTIME_COMMIT}^{commit}" >/dev/null 2>&1; then
  cat <<EOF
错误: 找不到运行数据 commit (${RUNTIME_COMMIT})。

请使用完整 clone（不要用 --depth 1）:
  git clone git@github.com:zhuyao1109/zhxSystem.git
  cd zhxSystem
  ./deploy.sh

若仍失败，可在已有完整历史的仓库中手动执行:
  git checkout ${RUNTIME_COMMIT} -- semAlign_backend/data semAlign_backend/models/gte-multilingual-base semAlign_backend/models/models--sentence-transformers--all-MiniLM-L6-v2
EOF
  exit 1
fi

echo "==> 正在从 ${RUNTIME_COMMIT} 恢复数据库与模型（约 800MB，首次需数分钟）..."
mkdir -p semAlign_backend/data semAlign_backend/models

for path in "${restore_paths[@]}"; do
  if git cat-file -e "${RUNTIME_COMMIT}:${path}" 2>/dev/null || git ls-tree -d "${RUNTIME_COMMIT}" "${path}" >/dev/null 2>&1; then
    git archive "${RUNTIME_COMMIT}" "${path}" | tar -x -C "${ROOT_DIR}"
    echo "    + ${path}"
  fi
done

if ! runtime_ready; then
  echo "错误: 运行数据恢复不完整，请检查网络与 Git 历史是否完整。"
  exit 1
fi

echo "==> 运行数据恢复完成。"
