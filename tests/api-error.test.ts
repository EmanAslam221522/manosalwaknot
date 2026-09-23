import assert from 'node:assert/strict';
import test from 'node:test';
import {
  ApiError,
  apiErrorFromResponse,
  getUserFacingErrorMessage,
} from '../services/api/ApiError';

void test('normalizes the backend error envelope and request ID', () => {
  const error = apiErrorFromResponse(
    409,
    {
      error: {
        code: 'RESERVATION_QUANTITY_UNAVAILABLE',
        message: 'The requested quantity is no longer available.',
        request_id: 'request-from-body',
      },
    },
    'request-from-header',
  );

  assert.equal(error.kind, 'CONFLICT');
  assert.equal(error.code, 'RESERVATION_QUANTITY_UNAVAILABLE');
  assert.equal(error.requestId, 'request-from-body');
});

void test('maps authorization and rate limits to stable error kinds', () => {
  assert.equal(apiErrorFromResponse(403, null, null).kind, 'AUTHORIZATION');
  assert.equal(apiErrorFromResponse(429, null, null).kind, 'RATE_LIMIT');
});

void test('does not expose technical network and server details to users', () => {
  const network = new ApiError({
    code: 'NETWORK_ERROR',
    kind: 'NETWORK',
    message: 'fetch failed: socket details',
  });
  const server = new ApiError({
    code: 'HTTP_500',
    kind: 'SERVER',
    message: 'internal path and SQL details',
  });

  assert.equal(
    getUserFacingErrorMessage(network),
    'No internet connection. Check your connection and try again.',
  );
  assert.equal(
    getUserFacingErrorMessage(server),
    'The service is temporarily unavailable. Please try again.',
  );
});
