import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import {
  fetchMe,
  getSessionToken,
  setSessionToken,
  logout as logoutApi,
  SessionUser,
} from '../lib/auth';

interface AuthCtx {
  user: SessionUser | null;
  isAuthed: boolean;
  loading: boolean;
  /** Bootstrapped on every page load. Hits /auth/me when a token exists. */
  refresh: () => Promise<void>;
  /** Stash a freshly minted session (called after the verify-redirect lands). */
  signIn: (token: string, userId: string) => Promise<SessionUser | null>;
  signOut: () => Promise<void>;
  /** Convenience: open the LoginModal from anywhere via state in the provider. */
  loginOpen: boolean;
  openLogin: () => void;
  closeLogin: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function useAuth(): AuthCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth must be used within AuthProvider');
  return v;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [loginOpen, setLoginOpen] = useState(false);

  const refresh = useCallback(async () => {
    if (!getSessionToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await fetchMe();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(async (token: string, userId: string) => {
    setSessionToken(token, userId);
    await refresh();
    return user;
    // user from closure is fine for the immediate-after caller; the
    // canonical refresh hits /auth/me and updates state for the rest of
    // the tree.
  }, [refresh, user]);

  const signOut = useCallback(async () => {
    await logoutApi();
    setUser(null);
  }, []);

  const value: AuthCtx = {
    user,
    isAuthed: !!user,
    loading,
    refresh,
    signIn,
    signOut,
    loginOpen,
    openLogin: () => setLoginOpen(true),
    closeLogin: () => setLoginOpen(false),
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
