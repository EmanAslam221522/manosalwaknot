import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

export type StoredSession = {
  accessToken: string;
  refreshToken: string;
};

const SESSION_KEY = 'manosalwaknot.session.v1';
let webMemorySession: StoredSession | null = null;

function isStoredSession(value: unknown): value is StoredSession {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<StoredSession>;
  return typeof candidate.accessToken === 'string' && typeof candidate.refreshToken === 'string';
}

export const secureSessionStorage = {
  async get(): Promise<StoredSession | null> {
    if (Platform.OS === 'web') return webMemorySession;

    const value = await SecureStore.getItemAsync(SESSION_KEY);
    if (!value) return null;

    try {
      const parsed: unknown = JSON.parse(value);
      return isStoredSession(parsed) ? parsed : null;
    } catch {
      await SecureStore.deleteItemAsync(SESSION_KEY);
      return null;
    }
  },

  async set(session: StoredSession): Promise<void> {
    if (Platform.OS === 'web') {
      webMemorySession = session;
      return;
    }

    await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(session), {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  },

  async clear(): Promise<void> {
    if (Platform.OS === 'web') {
      webMemorySession = null;
      return;
    }
    await SecureStore.deleteItemAsync(SESSION_KEY);
  },
};
