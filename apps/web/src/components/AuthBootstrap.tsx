import { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { useToast } from './Toast';
import { useTokens } from './TokenContext';
import { useMembership } from './MembershipContext';

/** Mounted high in the tree. Reads the URL fragment after the API
 *  redirects to `/?auth=success#token=...&user_id=...&migrated=N`,
 *  stashes the session, refreshes wallet + plan, then strips the hash. */
export default function AuthBootstrap() {
  const { signIn } = useAuth();
  const tokens = useTokens();
  const membership = useMembership();
  const toast = useToast();
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;

    const status = params.get('auth');
    if (status === 'expired') {
      toast.info('That sign-in link expired — request a new one.');
      params.delete('auth');
      setParams(params, { replace: true });
      handled.current = true;
      return;
    }
    if (status === 'invalid') {
      toast.error('Sign-in link was invalid. Please request a new one.');
      params.delete('auth');
      setParams(params, { replace: true });
      handled.current = true;
      return;
    }
    if (status !== 'success') return;

    const hash = window.location.hash.replace(/^#/, '');
    if (!hash) return;
    const hp = new URLSearchParams(hash);
    const token = hp.get('token');
    const userId = hp.get('user_id');
    const migrated = parseInt(hp.get('migrated') || '0', 10);
    if (!token || !userId) return;

    handled.current = true;
    void (async () => {
      await signIn(token, userId);
      // Re-pull wallet + plan with the new identity in scope.
      await Promise.all([tokens.refresh(), membership.refresh()]);
      toast.success(
        migrated > 0
          ? `Signed in · device wallet migrated (${migrated} record${migrated === 1 ? '' : 's'})`
          : 'Signed in',
      );
      // Strip token from URL so it doesn't survive in browser history.
      params.delete('auth');
      setParams(params, { replace: true });
      nav(window.location.pathname, { replace: true });
    })();
  }, [params, setParams, signIn, tokens, membership, toast, nav]);

  return null;
}
