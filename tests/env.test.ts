import assert from 'node:assert/strict';
import test from 'node:test';
import {
  AppConfigurationError,
  resolveEnvironment,
  validatePublicApiConfiguration,
} from '../lib/config/env';

void test('environment defaults to development only when unset', () => {
  assert.equal(resolveEnvironment(undefined), 'development');
  assert.equal(resolveEnvironment('staging'), 'staging');
  assert.throws(() => resolveEnvironment('prod'), AppConfigurationError);
});

void test('staging and production reject insecure API transport', () => {
  assert.throws(
    () =>
      validatePublicApiConfiguration({
        apiBaseUrl: 'http://api.example.test',
        appEnvironment: 'production',
      }),
    /must use HTTPS/,
  );
  assert.equal(
    validatePublicApiConfiguration({
      apiBaseUrl: 'https://api.example.test/',
      appEnvironment: 'staging',
    }),
    'https://api.example.test',
  );
});

void test('API URL rejects credentials, fragments, and unsupported schemes', () => {
  assert.throws(
    () =>
      validatePublicApiConfiguration({
        apiBaseUrl: 'https://user:password@api.example.test',
        appEnvironment: 'production',
      }),
    /cannot contain credentials/,
  );
  assert.throws(
    () =>
      validatePublicApiConfiguration({
        apiBaseUrl: 'https://api.example.test/#debug',
        appEnvironment: 'production',
      }),
    /cannot contain credentials or a fragment/,
  );
  assert.throws(
    () =>
      validatePublicApiConfiguration({
        apiBaseUrl: 'file:///tmp/api',
        appEnvironment: 'development',
      }),
    /must use HTTP or HTTPS/,
  );
});
