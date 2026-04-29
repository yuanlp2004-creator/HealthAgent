import { api } from './client';
import type { AuthResponse, TokenPair, UserOut } from '../types/api';

export const authApi = {
  register: (data: { username: string; email: string; password: string; nickname?: string }) =>
    api.post<AuthResponse>('/auth/register', data).then((r) => r.data),

  login: (data: { username: string; password: string }) =>
    api.post<AuthResponse>('/auth/login', data).then((r) => r.data),

  refresh: (refresh_token: string) =>
    api.post<TokenPair>('/auth/refresh', { refresh_token }).then((r) => r.data),
};

export const userApi = {
  me: () => api.get<UserOut>('/users/me').then((r) => r.data),

  updateProfile: (data: Partial<Pick<UserOut, 'nickname' | 'gender' | 'birth_date'>>) =>
    api.patch<UserOut>('/users/me', data).then((r) => r.data),

  changePassword: (data: { old_password: string; new_password: string }) =>
    api.post<void>('/users/me/password', data).then((r) => r.data),
};
