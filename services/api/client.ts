import { AppConfigurationError, getApiBaseUrl } from '@/lib/config/env';
import { secureSessionStorage, type StoredSession } from '@/services/storage/secureSessionStorage';
import type { ApiRequestOptions, ApiResponse } from '@/types/api';
import { ApiError, apiErrorFromResponse } from './ApiError';

const DEFAULT_TIMEOUT_MS = 15_000;
const REFRESH_TIMEOUT_MS = 15_000;
const RETRY_DELAYS_MS = [350, 900];
let refreshPromise: Promise<StoredSession | null> | null = null;

type RefreshResponse = {
  access_token: string;
  refresh_token: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function createClientRequestId(): string {
  return `mobile-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function isRefreshResponse(value: unknown): value is RefreshResponse {
  return (
    isRecord(value) &&
    typeof value.access_token === 'string' &&
    typeof value.refresh_token === 'string'
  );
}

function buildUrl(path: string, query?: ApiRequestOptions['query']): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(`${getApiBaseUrl()}${normalizedPath}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== null && value !== undefined) url.searchParams.set(key, String(value));
  }
  return url.toString();
}

function delay(durationMs: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(resolve, durationMs);
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(timeout);
        reject(signal.reason);
      },
      { once: true },
    );
  });
}

async function parsePayload(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type');
  if (!contentType?.includes('application/json')) return null;
  return response.json();
}

async function refreshSession(): Promise<StoredSession | null> {
  const current = await secureSessionStorage.get();
  if (!current) return null;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort('timeout'), REFRESH_TIMEOUT_MS);
  try {
    const response = await fetch(buildUrl('/api/v1/auth/refresh'), {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Client-Request-Id': createClientRequestId(),
      },
      body: JSON.stringify({ refresh_token: current.refreshToken }),
      signal: controller.signal,
    });
    if (!response.ok) {
      await secureSessionStorage.clear();
      return null;
    }
    const payload = await response.json();
    if (!isRefreshResponse(payload)) {
      await secureSessionStorage.clear();
      return null;
    }
    const rotated = { accessToken: payload.access_token, refreshToken: payload.refresh_token };
    await secureSessionStorage.set(rotated);
    return rotated;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

async function getRefreshedSession(): Promise<StoredSession | null> {
  refreshPromise ??= refreshSession().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

function shouldRetry(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.kind === 'NETWORK' || error.kind === 'TIMEOUT' || error.kind === 'SERVER')
  );
}

async function execute<TBody>(
  options: ApiRequestOptions<TBody>,
  accessToken?: string,
): Promise<ApiResponse<unknown>> {
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort('timeout'),
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  const abortFromCaller = () => controller.abort(options.signal?.reason);
  options.signal?.addEventListener('abort', abortFromCaller, { once: true });

  try {
    const isFormData = options.bodyEncoding === 'form-data';
    const response = await fetch(buildUrl(options.path, options.query), {
      method: options.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        'X-Client-Request-Id': createClientRequestId(),
        ...(options.body === undefined || isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...options.headers,
      },
      body:
        options.body === undefined
          ? undefined
          : options.bodyEncoding === 'form-data'
            ? options.body
            : JSON.stringify(options.body),
      signal: controller.signal,
    });
    const requestId = response.headers.get('x-request-id');
    const payload = await parsePayload(response);
    if (!response.ok) throw apiErrorFromResponse(response.status, payload, requestId);
    return { data: payload, requestId, status: response.status };
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof AppConfigurationError) {
      throw new ApiError({
        code: 'API_NOT_CONFIGURED',
        kind: 'CONFIGURATION',
        message: error.message,
      });
    }
    if (controller.signal.aborted && !options.signal?.aborted) {
      throw new ApiError({
        code: 'REQUEST_TIMEOUT',
        kind: 'TIMEOUT',
        message: 'The request timed out.',
      });
    }
    if (options.signal?.aborted) throw error;
    throw new ApiError({
      code: 'NETWORK_ERROR',
      kind: 'NETWORK',
      message: 'Network request failed.',
    });
  } finally {
    clearTimeout(timeout);
    options.signal?.removeEventListener('abort', abortFromCaller);
  }
}

export async function apiRequest<TBody = unknown>(
  options: ApiRequestOptions<TBody>,
): Promise<ApiResponse<unknown>> {
  const requiresAuth = options.requiresAuth ?? true;
  const method = options.method ?? 'GET';
  const session = requiresAuth ? await secureSessionStorage.get() : null;
  let activeSession = session;
  let attempts = 0;

  while (true) {
    try {
      return await execute(options, activeSession?.accessToken);
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.kind === 'AUTHENTICATION' &&
        requiresAuth &&
        attempts === 0
      ) {
        attempts += 1;
        activeSession = await getRefreshedSession();
        if (activeSession) continue;
      }

      const retryIndex = attempts;
      const canRetry = method === 'GET' && options.retry !== false && shouldRetry(error);
      if (!canRetry || retryIndex >= RETRY_DELAYS_MS.length) throw error;
      attempts += 1;
      await delay(RETRY_DELAYS_MS[retryIndex], options.signal);
    }
  }
}
