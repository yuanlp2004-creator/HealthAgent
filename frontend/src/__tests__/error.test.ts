import { describe, it, expect } from 'vitest';
import { AxiosError } from 'axios';
import { extractError } from '../utils/error';

function axiosErrorWith(status: number, data: unknown): AxiosError {
  const err = new AxiosError('x');
  err.response = { status, data, statusText: '', headers: {}, config: {} as never } as never;
  return err;
}

describe('extractError', () => {
  it('returns fallback for non-axios errors', () => {
    expect(extractError(new Error('boom'), 'fb')).toBe('fb');
  });

  it('uses string detail', () => {
    const e = axiosErrorWith(400, { detail: '旧密码错误' });
    expect(extractError(e)).toBe('旧密码错误');
  });

  it('uses first msg from list detail (pydantic)', () => {
    const e = axiosErrorWith(422, { detail: [{ msg: '字段不合法' }] });
    expect(extractError(e)).toBe('字段不合法');
  });

  it('maps 409 when no detail', () => {
    const e = axiosErrorWith(409, {});
    expect(extractError(e)).toBe('已存在同名用户/邮箱');
  });

  it('maps 401 when no detail', () => {
    const e = axiosErrorWith(401, {});
    expect(extractError(e)).toBe('未授权或已过期');
  });
});
