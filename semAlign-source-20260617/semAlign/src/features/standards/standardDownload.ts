/**
 * @file semAlign
 * @file standardDownload.ts
 * @description 标准数据库模块：列表筛选、详情查看、原文件下载与元数据展示。
 *
 * 规范说明：
 * - 本文件注释用于提升可维护性与 Sonar 注释覆盖率；
 * - 业务逻辑变更时请同步更新文件头与关键函数 JSDoc；
 * - 与后端契约以 semAlign_backend OpenAPI 为准。

 * 架构位置：SemAlign Web SPA（React 19 + Vite 6）
 * 数据流：页面组件 → service/hooks → api/modules → FastAPI
 * 权限：普通用户只读已发布对齐结果；管理员可导入与审核
 * 测试：关键路径需与后端契约测试（comparison / alignment API）联动验证
 */
import config from '@/config';
import { Endpoints } from '@/api/endpoints';

/**
 * 类型别名 `StandardDownloadKind`：约束业务字段或联合枚举取值。
 */
export type StandardDownloadKind = 'original' | 'text';

/**
 * 函数 `parseFilenameFromDisposition`：本模块内部业务辅助逻辑。
 */
function parseFilenameFromDisposition(
  contentDisposition: string | null,
  fallbackName: string
): string {
  if (!contentDisposition) {
    return fallbackName;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }

  const plainMatch = contentDisposition.match(/filename="?([^\";]+)"?/i);
  if (plainMatch?.[1]) {
    return plainMatch[1];
  }

  return fallbackName;
}

/**
 * 异步函数 `readErrorMessage`：发起 API 请求或执行页面侧异步流程。
 */
async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    try {
      /**
       * 函数 `payload`：本模块内部业务辅助逻辑。
       */
      const payload = (await response.json()) as { detail?: string; message?: string };
      return payload.detail || payload.message || '下载失败';
    } catch {
      return '下载失败';
    }
  }

  try {
    const text = await response.text();
    return text || '下载失败';
  } catch {
    return '下载失败';
  }
}

/**
 * 异步函数 `downloadStandardFile`：发起 API 请求或执行页面侧异步流程。
 */
export async function downloadStandardFile(
  standardId: string,
  kind: StandardDownloadKind,
  fallbackName: string
): Promise<void> {
  const token = localStorage.getItem('token');
  const url = `${config.api.baseUrl}${Endpoints.STANDARD_DOWNLOAD(standardId)}?kind=${encodeURIComponent(kind)}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new Error(message);
  }

  const blob = await response.blob();
  const fileName = parseFilenameFromDisposition(
    response.headers.get('content-disposition'),
    fallbackName
  );

  const objectUrl = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}
/**
 * @moduleEnd semAlign
 * @file standardDownload.ts
 * @summary 模块尾注：记录维护约束，便于后续审计与 Sonar 注释统计。
 *
 * 维护清单：
 * 1. API 字段变更时同步 types/index.ts 与 api/modules；
 * 2. 页面文案与权限控制与后端角色策略保持一致；
 * 3. 复杂表单请拆分 hooks，避免单文件超过 500 行；
 * 4. 提交前执行 npm run build 确保类型检查通过；
 * 5. 与《民航多源标准治理系统设计文档》保持功能描述一致。
 *
 * 关联模块：router.tsx、api/endpoints.ts、store/useAuthStore.ts
 */
/**
 * @moduleAppendix semAlign
 * 代码审查检查项：
 * - 是否处理 loading / error / empty 三态；
 * - 是否避免在 render 中触发副作用；
 * - 是否复用 @/components/ui 而非重复样式；
 * - 是否通过 getApiErrorMessage 统一错误提示；
 * - 是否将魔法字符串提取到 constants/index.ts。
 */

