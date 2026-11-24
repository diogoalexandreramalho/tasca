import { useQueryClient } from '@tanstack/react-query';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

import {
  clearSession,
  getSessionExpiry,
  getSessionRole,
  getToken,
  request,
  saveSession,
  setUnauthorizedHandler,
} from '@/lib/api';

type AuthState = {
  isAuthenticated: boolean;
  /** A read-only demo session: hide anything that changes data. */
  isGuest: boolean;
  login: (username: string, password: string) => Promise<void>;
  loginAsGuest: () => Promise<void>;
  logout: () => void;
};

type TokenResponse = { access_token: string; token_type: 'bearer'; expires_in: number };

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [isAuthenticated, setIsAuthenticated] = useState(() => getToken() !== null);
  const [isGuest, setIsGuest] = useState(() => getToken() !== null && getSessionRole() === 'guest');

  const logout = useCallback(() => {
    clearSession();
    queryClient.clear(); // drop cached admin data
    setIsAuthenticated(false);
    setIsGuest(false);
  }, [queryClient]);

  const login = useCallback(async (username: string, password: string) => {
    const { access_token, expires_in } = await request<TokenResponse>('/auth/token', {
      method: 'POST',
      form: new URLSearchParams({ username, password }),
      auth: false,
    });
    saveSession(access_token, expires_in, 'admin');
    setIsGuest(false);
    setIsAuthenticated(true);
  }, []);

  const loginAsGuest = useCallback(async () => {
    const { access_token, expires_in } = await request<TokenResponse>('/auth/guest', {
      method: 'POST',
      auth: false,
    });
    saveSession(access_token, expires_in, 'guest');
    setIsGuest(true);
    setIsAuthenticated(true);
  }, []);

  // A 401 from any request means the token is no longer valid.
  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  // Log out when the token expires, even if no request is made.
  useEffect(() => {
    if (!isAuthenticated) return;
    const expiresAt = getSessionExpiry();
    if (expiresAt === null) return;
    const timer = setTimeout(logout, Math.max(0, expiresAt - Date.now()));
    return () => clearTimeout(timer);
  }, [isAuthenticated, logout]);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isGuest, login, loginAsGuest, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
