import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { RequireAuth } from '../components/RequireAuth';
import { useAuth } from '../store/auth';

function Protected() {
  return <div>PROTECTED</div>;
}

function Login() {
  return <div>LOGIN_PAGE</div>;
}

function renderAt(initial: string) {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/me"
          element={
            <RequireAuth>
              <Protected />
            </RequireAuth>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

const sampleUser = {
  id: 1,
  username: 'alice',
  email: 'a@x.com',
  nickname: null,
  gender: null,
  birth_date: null,
  created_at: '2026-04-19T00:00:00',
};

describe('RequireAuth', () => {
  beforeEach(() => {
    useAuth.setState({ user: null, initialized: false, loading: false });
  });

  it('shows loading before bootstrap finishes', () => {
    renderAt('/me');
    expect(screen.queryByText('PROTECTED')).toBeNull();
    expect(screen.queryByText('LOGIN_PAGE')).toBeNull();
  });

  it('redirects to /login when not authenticated', () => {
    useAuth.setState({ initialized: true, user: null });
    renderAt('/me');
    expect(screen.getByText('LOGIN_PAGE')).toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    useAuth.setState({ initialized: true, user: sampleUser });
    renderAt('/me');
    expect(screen.getByText('PROTECTED')).toBeInTheDocument();
  });
});
