import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuth } from '../store/auth';
import { tokenStore } from '../api/client';
import * as endpoints from '../api/endpoints';

const sampleUser = {
  id: 1,
  username: 'alice',
  email: 'a@x.com',
  nickname: null,
  gender: null,
  birth_date: null,
  created_at: '2026-04-19T00:00:00',
};

const tokens = { access_token: 'A', refresh_token: 'R', token_type: 'bearer' as const };

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuth.setState({ user: null, initialized: false, loading: false });
  });

  it('login stores tokens and user', async () => {
    const spy = vi.spyOn(endpoints.authApi, 'login').mockResolvedValue({ user: sampleUser, tokens });
    await useAuth.getState().login('alice', 'secret123');
    expect(spy).toHaveBeenCalledWith({ username: 'alice', password: 'secret123' });
    expect(tokenStore.getAccess()).toBe('A');
    expect(tokenStore.getRefresh()).toBe('R');
    expect(useAuth.getState().user?.username).toBe('alice');
  });

  it('register stores tokens and user', async () => {
    vi.spyOn(endpoints.authApi, 'register').mockResolvedValue({ user: sampleUser, tokens });
    await useAuth.getState().register('alice', 'a@x.com', 'secret123');
    expect(tokenStore.getAccess()).toBe('A');
    expect(useAuth.getState().user?.username).toBe('alice');
  });

  it('logout clears tokens and user', () => {
    tokenStore.set('A', 'R');
    useAuth.setState({ user: sampleUser });
    useAuth.getState().logout();
    expect(tokenStore.getAccess()).toBeNull();
    expect(useAuth.getState().user).toBeNull();
  });

  it('bootstrap without token marks initialized and leaves user null', async () => {
    await useAuth.getState().bootstrap();
    expect(useAuth.getState().initialized).toBe(true);
    expect(useAuth.getState().user).toBeNull();
  });

  it('bootstrap with valid token loads user', async () => {
    tokenStore.set('A', 'R');
    vi.spyOn(endpoints.userApi, 'me').mockResolvedValue(sampleUser);
    await useAuth.getState().bootstrap();
    expect(useAuth.getState().user?.username).toBe('alice');
    expect(useAuth.getState().initialized).toBe(true);
  });

  it('bootstrap with invalid token clears tokens', async () => {
    tokenStore.set('A', 'R');
    vi.spyOn(endpoints.userApi, 'me').mockRejectedValue(new Error('401'));
    await useAuth.getState().bootstrap();
    expect(useAuth.getState().user).toBeNull();
    expect(tokenStore.getAccess()).toBeNull();
    expect(useAuth.getState().initialized).toBe(true);
  });

  it('login failure leaves state clean and propagates error', async () => {
    vi.spyOn(endpoints.authApi, 'login').mockRejectedValue(new Error('nope'));
    await expect(useAuth.getState().login('a', 'b')).rejects.toThrow('nope');
    expect(useAuth.getState().loading).toBe(false);
    expect(useAuth.getState().user).toBeNull();
  });
});
