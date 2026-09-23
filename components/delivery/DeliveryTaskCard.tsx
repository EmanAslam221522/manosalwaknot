import { Card, Typography } from 'heroui-native';
import { Pressable, View } from 'react-native';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { DeliveryTaskSummary } from '@/types/delivery';
import { formatPickupWindow } from '@/utils/formatting';

export function DeliveryTaskCard({
  task,
  onPress,
}: {
  task: DeliveryTaskSummary;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${task.foodTitle}, delivery from ${task.pickupArea} to ${task.dropoffArea}`}
    >
      <Card className="gap-3 p-4">
        <View className="flex-row items-start justify-between gap-3">
          <Typography.Heading type="h4" className="flex-1">
            {task.foodTitle}
          </Typography.Heading>
          <StatusBadge label={task.status.replaceAll('_', ' ')} tone="neutral" />
        </View>
        <Typography.Paragraph>
          {task.pickupArea} → {task.dropoffArea}
        </Typography.Paragraph>
        <Typography.Paragraph color="muted">
          {task.servings} servings · {formatPickupWindow(task.pickupStart, task.pickupEnd)}
        </Typography.Paragraph>
        {task.distanceKm !== null ? (
          <Typography.Paragraph type="body-sm" color="muted">
            Approximately {task.distanceKm.toFixed(1)} km
          </Typography.Paragraph>
        ) : null}
      </Card>
    </Pressable>
  );
}
