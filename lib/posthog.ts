import { Platform } from 'react-native';
import { appEnvironment } from '@/lib/config/env';

let initStarted = false;

function getAnalyticsConfiguration(): { key: string; host: string } | null {
  const key = process.env.EXPO_PUBLIC_POSTHOG_KEY?.trim();
  const hostValue = process.env.EXPO_PUBLIC_POSTHOG_HOST?.trim();
  if (!key || !hostValue) return null;

  try {
    const host = new URL(hostValue);
    if (host.username || host.password || host.hash) return null;
    if (appEnvironment !== 'development' && host.protocol !== 'https:') return null;
    if (host.protocol !== 'https:' && host.protocol !== 'http:') return null;
    return { key, host: hostValue.replace(/\/$/, '') };
  } catch {
    return null;
  }
}

export function initPostHog(): void {
  if (
    initStarted ||
    Platform.OS !== 'web' ||
    typeof window === 'undefined' ||
    window === window.parent
  ) {
    return;
  }

  const configuration = getAnalyticsConfiguration();
  if (!configuration) return;

  initStarted = true;

  void import('posthog-js')
    .then(({ posthog }) => {
      posthog.init(configuration.key, {
        api_host: configuration.host,
        autocapture: false,
        capture_pageview: false,
        capture_pageleave: false,
        disable_session_recording: true,
      });
    })
    .catch(() => {
      initStarted = false;
    });
}
