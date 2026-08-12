import config from '@/config';
import { Endpoints } from '@/api/endpoints';

export type StandardDownloadKind = 'original' | 'text';

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

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    try {
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
