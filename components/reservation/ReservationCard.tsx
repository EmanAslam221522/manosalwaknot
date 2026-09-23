import { PressableFeedback, Card, Typography } from 'heroui-native';
import { View } from 'react-native';
import type { ReservationSummary } from '@/types/reservation';
import { formatPickupWindow } from '@/utils/formatting';
import { StatusBadge } from '@/components/ui/StatusBadge';

function toneForStatus(
  status: ReservationSummary['status'],
): 'neutral' | 'success' | 'warning' | 'danger' {
  if (status === 'COMPLETED' || status === 'DELIVERED' || status === 'PICKED_UP') return 'success';
  if (
    status === 'CANCELLED' ||
    status === 'EXPIRED' ||
    status === 'NO_SHOW' ||
    status === 'DISPUTED'
  )
    return 'danger';
  if (status === 'READY') return 'warning';
  return 'neutral';
}

export function ReservationCard({
  reservation,
  onPress,
}: {
  reservation: ReservationSummary;
  onPress: () => void;
}) {
  return (
    <PressableFeedback
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`View reservation for ${reservation.food.title}`}
    >
      <Card className="gap-3 p-4">
        <View className="flex-row items-start justify-between gap-3">
          <Typography.Heading type="h4" className="flex-1">
            {reservation.food.title}
          </Typography.Heading>
          <StatusBadge label={reservation.status} tone={toneForStatus(reservation.status)} />
        </View>
        <Typography.Paragraph type="body-sm" color="muted">
          {reservation.quantity} servings · {reservation.food.providerName}
        </Typography.Paragraph>
        <Typography.Paragraph type="body-sm">
          {formatPickupWindow(reservation.pickupStart, reservation.pickupEnd)}
        </Typography.Paragraph>
      </Card>
    </PressableFeedback>
  );
}
