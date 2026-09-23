import { create } from 'zustand';
import type { AuthSession } from '@/services/auth/authService';
import { secureSessionStorage } from '@/services/storage/secureSessionStorage';
import { queryClient } from '@/services/api/queryClient';
import type { UserSummary } from '@/types/domain';

export type AuthStatus = 'initializing' | 'authenticated' | 'unauthenticated';

type AuthState = {
  status: AuthStatus;
  user: UserSummary | null;
  completeSession: (session: AuthSession) => Promise<void>;
  setAuthenticatedUser: (user: UserSummary) => void;
  setUnauthenticated: () => void;
  clearSession: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  status: 'initializing',
  user: null,

  async completeSession(session) {
    const previousUserId = useAuthStore.getState().user?.id;
    if (previousUserId && previousUserId !== session.user.id) queryClient.clear();
    await secureSessionStorage.set({
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
    });
    set({ status: 'authenticated', user: session.user });
  },

  setAuthenticatedUser(user) {
    set({ status: 'authenticated', user });
  },

  setUnauthenticated() {
    queryClient.clear();
    set({ status: 'unauthenticated', user: null });
  },

  async clearSession() {
    await secureSessionStorage.clear();
    queryClient.clear();
    set({ status: 'unauthenticated', user: null });
  },
}));
