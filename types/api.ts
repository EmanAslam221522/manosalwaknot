export type ApiErrorPayload = {
  error: {
    code: string;
    message: string;
    request_id?: string;
    details?: Record<string, unknown>;
  };
};

export type ApiMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export type ApiQueryValue = string | number | boolean | null | undefined;

type ApiRequestOptionsBase = {
  method?: ApiMethod;
  path: string;
  query?: Record<string, ApiQueryValue>;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeoutMs?: number;
  requiresAuth?: boolean;
  retry?: boolean;
};

export type ApiRequestOptions<TBody = unknown> =
  | (ApiRequestOptionsBase & {
      bodyEncoding: 'form-data';
      body: FormData;
    })
  | (ApiRequestOptionsBase & {
      bodyEncoding?: 'json';
      body?: TBody;
    });

export type ApiResponse<T> = {
  data: T;
  requestId: string | null;
  status: number;
};
