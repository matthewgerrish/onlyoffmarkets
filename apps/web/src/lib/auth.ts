/* Auth client — magic-link sign-in + JWT session.
 *
 * Token lives in localStorage. apiHeaders() pulls it on every request
 * and sends `Authorization: Bearer <token>`. When the token isn't
 * present we still send X-User-Id so legacy anonymous flows keep
 * working — backend's identity.resolve_user_id() handles both.
 */
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001';

const TOKEN_KEY = 'oom_session_token_v1';
const USER_ID_KEY = 'oom_user_id_v1';

export interface SessionUser {
  user_id: string;
  email: string | null;
  session_exp?: number;
}

export function getSessionToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setSessionToken(token: string, userId: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  // Mirror the user_id so legacy code that reads it directly stays
  // consistent (TokenContext / wallet badges).
  localStorage.setItem(USER_ID_KEY, userId);
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  // Keep the legacy UUID so anonymous wallet/plan continues across
  // sign-out (lets users keep using the app after logout). To wipe
  // the device entirely, call `forgetDevice()` instead.
}

export function forgetDevice(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_ID_KEY);
}

export async function requestMagicLink(email: string): Promise<{
  ok: boolean;
  email: string;
  live_email: boolean;
  dev_link?: string;
  delivery_error?: string;
}> {
  const r = await fetch(`${API_BASE}/auth/magic-link`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      anon_user_id: localStorage.getItem(USER_ID_KEY) || undefined,
    }),
  });
  if (!r.ok) {
    const body = await r.text();
    throw new Error(`API ${r.status}: ${body}`);
  }
  return r.json();
}

export async function fetchMe(): Promise<SessionUser | null> {
  const tok = getSessionToken();
  if (!tok) return null;
  const r = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${tok}` },
  });
  if (r.status === 401) {
    clearSession();
    return null;
  }
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function logout(): Promise<void> {
  const tok = getSessionToken();
  if (tok) {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tok}` },
      });
    } catch {
      /* network is best-effort — token is invalidated locally regardless */
    }
  }
  clearSession();
}
