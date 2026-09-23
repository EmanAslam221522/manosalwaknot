import type { ApiErrorPayload } from '@/types/api';

export type ApiErrorKind =
  | 'AUTHENTICATION'
  | 'AUTHORIZATION'
  | 'CONFLICT'
  | 'CONFIGURATION'
  | 'NETWORK'
  | 'NOT_FOUND'
  | 'RATE_LIMIT'
  | 'SERVER'
  | 'TIMEOUT'
  | 'VALIDATION'
  | 'UNKNOWN';

export class ApiError extends Error {
  readonly code: string;
  readonly kind: ApiErrorKind;
  readonly requestId: string | null;
  readonly status: number | null;
  readonly details?: Record<string, unknown>;

  constructor(options: {
    code: string;
    kind: ApiErrorKind;
    message: string;
    requestId?: string | null;
    status?: number | null;
    details?: Record<string, unknown>;
  }) {
    super(options.message);
    this.name = 'ApiError';
    this.code = options.code;
    this.kind = options.kind;
    this.requestId = options.requestId ?? null;
    this.status = options.status ?? null;
    this.details = options.details;
  }
}

function kindForStatus(status: number): ApiErrorKind {
  if (status === 401) return 'AUTHENTICATION';
  if (status === 403) return 'AUTHORIZATION';
  if (status === 404) return 'NOT_FOUND';
  if (status === 409) return 'CONFLICT';
  if (status === 422 || status === 400) return 'VALIDATION';
  if (status === 429) return 'RATE_LIMIT';
  if (status >= 500) return 'SERVER';
  return 'UNKNOWN';
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function getErrorPayload(payload: unknown): Partial<ApiErrorPayload['error']> {
  if (!isRecord(payload) || !isRecord(payload.error)) return {};

  const { code, details, message, request_id: requestId } = payload.error;
  return {
    ...(typeof code === 'string' ? { code } : {}),
    ...(typeof message === 'string' ? { message } : {}),
    ...(typeof requestId === 'string' ? { request_id: requestId } : {}),
    ...(isRecord(details) ? { details } : {}),
  };
}

export function apiErrorFromResponse(
  status: number,
  payload: unknown,
  headerRequestId: string | null,
): ApiError {
  const error = getErrorPayload(payload);
  return new ApiError({
    code: error.code ?? `HTTP_${status}`,
    kind: kindForStatus(status),
    message: error.message ?? 'We could not complete your request.',
    requestId: error.request_id ?? headerRequestId,
    status,
    details: error.details,
  });
}

export function getUserFacingErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Something went wrong. Please try again.';
  if (error.kind === 'NETWORK')
    return 'No internet connection. Check your connection and try again.';
  if (error.kind === 'TIMEOUT') return 'The request took too long. Please try again.';
  if (error.kind === 'RATE_LIMIT') return 'Too many attempts. Please wait and try again.';
  if (error.kind === 'SERVER') return 'The service is temporarily unavailable. Please try again.';
  return error.message;
}
