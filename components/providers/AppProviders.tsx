import { useEffect, type PropsWithChildren } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { authService } from '@/services/auth/authService';
import { ApiError } from '@/services/api/ApiError';
import { queryClient } from '@/services/api/queryClient';
import { secureSessionStorage } from '@/services/storage/secureSessionStorage';
import { useAuthStore } from '@/hooks/auth/useAuthStore';

export function AppProviders({ children }: PropsWithChildren) {
  const setAuthenticatedUser = useAuthStore((state) => state.setAuthenticatedUser);
  const setUnauthenticated = useAuthStore((state) => state.setUnauthenticated);

  useEffect(() => {
    const controller = new AbortController();

    async function restoreSession() {
      const session = await secureSessionStorage.get();
      if (!session) {
        setUnauthenticated();
        return;
      }

      try {
        const user = await authService.getCurrentUser(controller.signal);
        setAuthenticatedUser(user);
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.kind === 'NETWORK') {
          setUnauthenticated();
          return;
        }
        await secureSessionStorage.clear();
        setUnauthenticated();
      }
    }

    void restoreSession();
    return () => controller.abort();
  }, [setAuthenticatedUser, setUnauthenticated]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
