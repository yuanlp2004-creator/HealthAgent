import axios, { AxiosError, AxiosRequestConfig } from 'axios';

const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1';

export const ACCESS_KEY = 'ha.access';
export const REFRESH_KEY = 'ha.refresh';

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export const api = axios.create({ baseURL: BASE });

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return null;
  try {
    const resp = await axios.post(`${BASE}/auth/refresh`, { refresh_token: refresh });
    const { access_token, refresh_token } = resp.data as { access_token: string; refresh_token: string };
    tokenStore.set(access_token, refresh_token);
    return access_token;
  } catch {
    tokenStore.clear();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && original && !original._retry && original.url !== '/auth/refresh') {
      original._retry = true;
      refreshing ??= doRefresh().finally(() => {
        refreshing = null;
      });
      const newAccess = await refreshing;
      if (newAccess) {
        original.headers = { ...(original.headers ?? {}), Authorization: `Bearer ${newAccess}` };
        return api.request(original);
      }
    }
    return Promise.reject(error);
  },
);
