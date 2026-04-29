import { create } from 'zustand';
import { authApi, userApi } from '../api/endpoints';
import { tokenStore } from '../api/client';
import type { UserOut } from '../types/api';

interface AuthState {
  user: UserOut | null;
  initialized: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, nickname?: string) => Promise<void>;
  logout: () => void;
  bootstrap: () => Promise<void>;
  setUser: (user: UserOut) => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  initialized: false,
  loading: false,

  login: async (username, password) => {
    set({ loading: true });
    try {
      const resp = await authApi.login({ username, password });
      tokenStore.set(resp.tokens.access_token, resp.tokens.refresh_token);
      set({ user: resp.user });
    } finally {
      set({ loading: false });
    }
  },

  register: async (username, email, password, nickname) => {
    set({ loading: true });
    try {
      const resp = await authApi.register({ username, email, password, nickname });
      tokenStore.set(resp.tokens.access_token, resp.tokens.refresh_token);
      set({ user: resp.user });
    } finally {
      set({ loading: false });
    }
  },

  logout: () => {
    tokenStore.clear();
    set({ user: null });
  },

  bootstrap: async () => {
    if (!tokenStore.getAccess()) {
      set({ initialized: true });
      return;
    }
    try {
      const user = await userApi.me();
      set({ user, initialized: true });
    } catch {
      tokenStore.clear();
      set({ user: null, initialized: true });
    }
  },

  setUser: (user) => set({ user }),
}));
