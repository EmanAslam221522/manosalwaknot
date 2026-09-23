const rawApiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
const rawAppEnvironment = process.env.EXPO_PUBLIC_APP_ENV?.trim();

export type AppEnvironment = 'development' | 'staging' | 'production';

type PublicApiConfiguration = {
  apiBaseUrl?: string;
  appEnvironment?: string;
};

export class AppConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AppConfigurationError';
  }
}

export function resolveEnvironment(value: string | undefined): AppEnvironment {
  if (!value) return 'development';
  if (value === 'development' || value === 'staging' || value === 'production') return value;
  throw new AppConfigurationError(
    'EXPO_PUBLIC_APP_ENV must be development, staging, or production.',
  );
}

export function validatePublicApiConfiguration({
  apiBaseUrl,
  appEnvironment,
}: PublicApiConfiguration): string {
  const environment = resolveEnvironment(appEnvironment?.trim());
  const value = apiBaseUrl?.trim();
  if (!value) {
    throw new AppConfigurationError(
      'The API is not configured. Set EXPO_PUBLIC_API_BASE_URL for this build.',
    );
  }

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new AppConfigurationError('EXPO_PUBLIC_API_BASE_URL must be a valid URL.');
  }

  if (url.username || url.password || url.hash) {
    throw new AppConfigurationError('The API URL cannot contain credentials or a fragment.');
  }
  if (environment !== 'development' && url.protocol !== 'https:') {
    throw new AppConfigurationError('Staging and production API traffic must use HTTPS.');
  }
  if (url.protocol !== 'https:' && url.protocol !== 'http:') {
    throw new AppConfigurationError('The API URL must use HTTP or HTTPS.');
  }

  return value.replace(/\/$/, '');
}

export const appEnvironment = resolveEnvironment(rawAppEnvironment);
export const isApiConfigured = Boolean(rawApiBaseUrl);

export function getApiBaseUrl(): string {
  return validatePublicApiConfiguration({
    apiBaseUrl: rawApiBaseUrl,
    appEnvironment: appEnvironment,
  });
}
