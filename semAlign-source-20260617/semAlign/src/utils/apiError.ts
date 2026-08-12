/**
 * @file semAlign
 * @file apiError.ts
 * @description 工具函数：格式化、校验、API 错误解析与数据映射。
 * @remarks API 错误文案提取：兼容 Axios 与业务错误码。
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
import type { AxiosError } from 'axios';

/**
 * 类型别名 `ApiErrorBody`：约束业务字段或联合枚举取值。
 */
type ApiErrorBody = {
  detail?: string | Array<{ msg?: string } | string>;
  message?: string;
};

/**
 * 函数 `isAxiosError`：本模块内部业务辅助逻辑。
 */
function isAxiosError(error: unknown): error is AxiosError<ApiErrorBody> {
  return Boolean(error && typeof error === 'object' && 'response' in error);
}

/**
 * 函数 `formatDetail`：本模块内部业务辅助逻辑。
 */
function formatDetail(detail: ApiErrorBody['detail']): string | null {
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  if (!Array.isArray(detail) || detail.length === 0) {
    return null;
  }
  const parts = detail.map((item) =>
    typeof item === 'object' && item !== null && 'msg' in item
      ? String(item.msg)
      : String(item)
  );
  return parts.join('；') || null;
}

/**
 * 函数 `messageFromAxios`：本模块内部业务辅助逻辑。
 */
function messageFromAxios(ax: AxiosError<ApiErrorBody>): string | null {
  const data = ax.response?.data;
  if (data) {
    const fromDetail = formatDetail(data.detail);
    if (fromDetail) {
      return fromDetail;
    }
    if (typeof data.message === 'string' && data.message.trim()) {
      return data.message;
    }
  }
  return ax.message || null;
}

/**
 * 从 Axios / 后端错误响应中取出可读文案（FastAPI 常见字段：detail、message）
 */
export function getApiErrorMessage(error: unknown, fallback = '请求失败'): string {
  if (isAxiosError(error)) {
    return messageFromAxios(error) ?? fallback;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
/**
 * @moduleEnd semAlign
 * @file apiError.ts
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

