import { View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';
import { Typography, useThemeColor } from 'heroui-native';

export function QRCodeView({ token, expiresAt }: { token: string; expiresAt: string }) {
  const foreground = useThemeColor('foreground');
  const background = useThemeColor('background');
  return (
    <View
      className="bg-background items-center gap-3 rounded-3xl p-5"
      accessible
      accessibilityLabel="Secure handover QR code"
    >
      <QRCode
        value={`manosalwaknot://handover?token=${encodeURIComponent(token)}`}
        size={220}
        color={foreground}
        backgroundColor={background}
      />
      <Typography.Paragraph type="body-sm" align="center">
        Show this code to the provider
      </Typography.Paragraph>
      <Typography.Paragraph type="body-xs" color="muted">
        Expires{' '}
        {new Date(expiresAt).toLocaleTimeString('en-PK', { hour: 'numeric', minute: '2-digit' })}
      </Typography.Paragraph>
    </View>
  );
}
