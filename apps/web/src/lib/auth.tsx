/**
 * Authentication state for the whole app.
 *
 * On start-up we silently try to refresh the session (the refresh cookie may
 * still be valid), then load the current user. Login/register store the
 * access token in memory; logout revokes the refresh token server-side.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  api,
  hasSessionMarker,
  markSession,
  refreshSession,
  request,
  setAccessToken,
  setSessionExpiredHandler,
} from "@/lib/api";
import type { TokenResponse, User } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();

  const loadUser = useCallback(async () => {
    const me = await api.get<User>("/auth/me");
    setUser(me);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (hasSessionMarker() && (await refreshSession())) await loadUser();
      } catch {
        setAccessToken(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadUser]);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setAccessToken(null);
      markSession(false);
      setUser(null);
      queryClient.clear();
    });
    return () => setSessionExpiredHandler(null);
  }, [queryClient]);

  const login = useCallback(
    async (email: string, password: string) => {
      const token = await authRequest<TokenResponse>("/auth/login", { email, password });
      setAccessToken(token.access_token);
      markSession(true);
      await loadUser();
    },
    [loadUser],
  );

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      const token = await authRequest<TokenResponse>("/auth/register", { email, password, name });
      setAccessToken(token.access_token);
      markSession(true);
      await loadUser();
    },
    [loadUser],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      setAccessToken(null);
      markSession(false);
      setUser(null);
      queryClient.clear();
    }
  }, [queryClient]);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser: loadUser }),
    [user, loading, login, register, logout, loadUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Auth endpoints are called without a Bearer token and must not trigger a refresh loop.
function authRequest<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body, auth: false, retryOn401: false });
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
