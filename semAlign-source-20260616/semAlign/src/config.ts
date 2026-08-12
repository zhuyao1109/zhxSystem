/**
 * 应用配置
 */

const isDev = import.meta.env.DEV;

export const config = {
  // API 配置
  api: {
    // 后端 API 基础地址
    baseUrl: isDev ? 'http://localhost:8000/api' : '/api',
    // 是否使用真实 API（false 则使用 Mock 数据）
    useRealApi: true,
    // 请求超时时间（毫秒）
    timeout: 30000,
  },

  // 文件上传配置
  upload: {
    // 支持的文件格式
    allowedExtensions: ['.xlsx', '.xls', '.pdf'],
    // 最大文件大小（字节）
    maxFileSize: 20 * 1024 * 1024, // 20MB
  },
} as const;

export default config;
