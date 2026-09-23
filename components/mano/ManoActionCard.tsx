import { View } from 'react-native';
import { Card, Typography } from 'heroui-native';
import { AppButton } from '@/components/ui/AppButton';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { ManoSuggestedAction } from '@/types/mano';

export function ManoActionCard({
  action,
  isLoading,
  isCompleted,
  onPress,
}: {
  action: ManoSuggestedAction;
  isLoading: boolean;
  isCompleted: boolean;
  onPress: () => void;
}) {
  return (
    <Card className="border-border gap-3 border p-4" accessibilityLabel={action.label}>
      <View className="flex-row items-center justify-between gap-3">
        <Typography.Paragraph weight="semibold" className="flex-1">
          {action.label}
        </Typography.Paragraph>
        {action.requiresConfirmation ? (
          <StatusBadge
            label={isCompleted ? 'Confirmed' : 'Confirmation required'}
            tone={isCompleted ? 'success' : 'warning'}
          />
        ) : null}
      </View>
      {action.summary ? (
        <Typography.Paragraph color="muted">{action.summary}</Typography.Paragraph>
      ) : null}
      <AppButton
        label={action.requiresConfirmation ? (isCompleted ? 'Confirmed' : 'Confirm') : 'Open'}
        size="sm"
        variant={action.requiresConfirmation ? 'primary' : 'secondary'}
        isDisabled={isCompleted}
        isLoading={isLoading}
        onPress={onPress}
      />
    </Card>
  );
}
