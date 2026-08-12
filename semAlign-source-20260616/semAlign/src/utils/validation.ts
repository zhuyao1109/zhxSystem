/**
 * 校验工具函数
 */

// 必填校验
export function required(value: unknown, message: string = '必填'): string | undefined {
  if (value === null || value === undefined || value === '') {
    return message;
  }
  return undefined;
}

// 邮箱校验
export function isEmail(value: string): boolean {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(value);
}

// 手机号校验
export function isPhone(value: string): boolean {
  const regex = /^1[3-9]\d{9}$/;
  return regex.test(value);
}
