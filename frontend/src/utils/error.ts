import { AxiosError } from 'axios';

export function extractError(err: unknown, fallback = '操作失败'): string {
  if (err instanceof AxiosError) {
    const data = err.response?.data as { detail?: unknown } | undefined;
    const detail = data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
    if (err.response?.status === 401) return '未授权或已过期';
    if (err.response?.status === 409) return '已存在同名用户/邮箱';
    if (err.response?.status === 422) return '输入不符合要求';
  }
  return fallback;
}
