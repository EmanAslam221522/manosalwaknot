import { View } from 'react-native';
import { Alert, Spinner, Typography } from 'heroui-native';
import { AppButton } from './AppButton';

type StateViewProps = {
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  kind?: 'empty' | 'error' | 'loading';
};

export function StateView({
  title,
  message,
  actionLabel,
  onAction,
  kind = 'empty',
}: StateViewProps) {
  if (kind === 'loading') {
    return (
      <View
        className="flex-1 items-center justify-center gap-3 p-8"
        accessibilityRole="progressbar"
      >
        <Spinner />
        <Typography.Paragraph color="muted">{title}</Typography.Paragraph>
      </View>
    );
  }

  return (
    <Alert status={kind === 'error' ? 'danger' : 'default'}>
      <Alert.Content>
        <Alert.Title>{title}</Alert.Title>
        {message ? <Alert.Description>{message}</Alert.Description> : null}
        {actionLabel && onAction ? (
          <View className="mt-3 self-start">
            <AppButton label={actionLabel} onPress={onAction} size="sm" variant="secondary" />
          </View>
        ) : null}
      </Alert.Content>
    </Alert>
  );
}
