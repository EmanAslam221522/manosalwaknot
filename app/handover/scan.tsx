import { CameraView, useCameraPermissions } from 'expo-camera';
import { router } from 'expo-router';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { View } from 'react-native';
import { Typography } from 'heroui-native';
import { AppButton } from '@/components/ui/AppButton';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { handoverService } from '@/services/trust/handoverService';

function extractToken(data: string): string {
  try {
    const url = new URL(data);
    return url.searchParams.get('token') ?? data;
  } catch {
    return data;
  }
}

export default function HandoverScanScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const mutation = useMutation({
    mutationFn: (value: string) => handoverService.confirm(extractToken(value)),
    onSuccess: (reservation) =>
      router.replace({ pathname: '/reservations/[id]', params: { id: reservation.id } }),
    onError: () => setScanned(false),
  });

  if (!permission)
    return (
      <Screen>
        <StateView title="Checking camera access…" kind="loading" />
      </Screen>
    );
  if (!permission.granted)
    return (
      <Screen title="Scan handover">
        <StateView
          title="Camera access is needed"
          message="The camera is used only to scan the recipient's short-lived pickup QR code."
          actionLabel="Allow camera"
          onAction={() => void requestPermission()}
        />
      </Screen>
    );

  return (
    <Screen title="Scan handover">
      <View className="overflow-hidden rounded-3xl" style={{ height: 420 }}>
        <CameraView
          style={{ flex: 1 }}
          barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
          onBarcodeScanned={
            scanned
              ? undefined
              : ({ data }) => {
                  setScanned(true);
                  mutation.mutate(data);
                }
          }
        />
      </View>
      <Typography.Paragraph align="center" color="muted">
        The server verifies the token, reservation, provider authorization, expiry, and repeated
        scans.
      </Typography.Paragraph>
      {mutation.isPending ? <StateView title="Verifying handover…" kind="loading" /> : null}
      {mutation.error ? (
        <StateView
          title="Could not confirm handover"
          message={getUserFacingErrorMessage(mutation.error)}
          actionLabel="Scan again"
          onAction={() => setScanned(false)}
          kind="error"
        />
      ) : null}
      <AppButton label="Cancel" variant="ghost" onPress={() => router.back()} />
    </Screen>
  );
}
