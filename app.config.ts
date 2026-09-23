import type { ConfigContext, ExpoConfig } from '@expo/config';

type ExpoPlugins = NonNullable<ExpoConfig['plugins']>;

export default ({ config }: ConfigContext): ExpoConfig => {
  const nativePlugins: ExpoPlugins =
    process.env.EXPO_PLATFORM === 'native'
      ? [['expo-dev-client', { launchMode: 'most-recent' }]]
      : [];

  return {
    ...config,
    name: 'ManOSalwaKnot',
    slug: 'manosalwaknot',
    version: process.env.BILT_APP_VERSION ?? '1.0.0',
    orientation: 'portrait',
    userInterfaceStyle: 'automatic',
    scheme: 'manosalwaknot',
    runtimeVersion: {
      policy: 'appVersion',
    },
    assetBundlePatterns: ['**/*'],
    ios: {
      infoPlist: {
        ITSAppUsesNonExemptEncryption: false,
      },
      supportsTablet: true,
      bundleIdentifier: process.env.BILT_IOS_BUNDLE_ID ?? 'me.bilt.manosalwaknot',
    },
    android: {
      package: process.env.BILT_ANDROID_PACKAGE ?? 'me.bilt.manosalwaknot',
    },
    web: {
      bundler: 'metro',
      // 'single' = SPA export: one index.html + client routing, so edge serving
      // needs only a single 404→index.html fallback rule.
      output: 'single',
      favicon: './public/icons/icon-192.png',
    },
    extra: {
      appStoreAppId: process.env.BILT_APP_STORE_APP_ID,
    },
    plugins: [
      'expo-router',
      'expo-font',
      'expo-asset',
      'expo-splash-screen',
      'expo-secure-store',
      [
        'expo-location',
        {
          locationWhenInUsePermission:
            'Allow ManOSalwaKnot to use your location to find nearby food. Your exact location is not shown publicly.',
        },
      ],
      [
        'expo-camera',
        {
          cameraPermission: 'Allow ManOSalwaKnot to scan secure food handover QR codes.',
          barcodeScannerEnabled: true,
        },
      ],
      [
        'expo-audio',
        {
          microphonePermission:
            'Allow ManOSalwaKnot to record your voice when you choose voice input for Mano AI.',
        },
      ],
      'expo-notifications',
      ...nativePlugins,
    ],
    experiments: {
      typedRoutes: true,
      reactCompiler: true,
    },
  };
};
