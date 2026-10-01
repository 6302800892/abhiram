import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { api, setToken } from "./api";
import type { Role, Session } from "./types";

const STORAGE_KEY = "medicard.session";

export const HOME_BY_ROLE: Record<Role, string> = {
  CUSTOMER: "/customer",
  HOSPITAL: "/hospital",
  INSURER: "/insurer",
  ADMIN: "/admin",
};

interface AuthState {
  session: Session | null;
  signIn: (username: string, password: string) => Promise<Session>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function loadSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    const session = raw ? (JSON.parse(raw) as Session) : null;
    setToken(session?.token ?? null);
    return session;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadSession);

  const signIn = useCallback(async (username: string, password: string) => {
    const result = await api.post<Session>("/api/auth/login", { username, password });
    setToken(result.token);
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result));
    } catch {
      /* storage unavailable: session lives in memory only */
    }
    setSession(result);
    return result;
  }, []);

  const signOut = useCallback(() => {
    setToken(null);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setSession(null);
  }, []);

  const value = useMemo(() => ({ session, signIn, signOut }), [session, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
