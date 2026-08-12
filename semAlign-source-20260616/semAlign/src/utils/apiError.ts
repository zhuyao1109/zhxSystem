import type { AxiosError } from 'axios';

type ApiErrorBody = {
  detail?: string | Array<{ msg?: string } | string>;
  message?: string;
};

function isAxiosError(error: unknown): error is AxiosError<ApiErrorBody> {
  return Boolean(error && typeof error === 'object' && 'response' in error);
}

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
