import { useMutation, useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';
import { Card, Typography } from 'heroui-native';
import { QRCodeView } from '@/components/reservation/QRCodeView';
import { AppButton } from '@/components/ui/AppButton';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { reservationService } from '@/services/reservations/reservationService';
import { handoverService } from '@/services/trust/handoverService';
import type { HandoverToken } from '@/types/trust';
import { formatPickupWindow } from '@/utils/formatting';

export default function ReservationDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [handover, setHandover] = useState<HandoverToken | null>(null);
  const query = useQuery({
    queryKey: ['reservation', id],
    queryFn: ({ signal }) => reservationService.getById(id, signal),
    enabled: Boolean(id),
  });
  const cancel = useMutation({
    mutationFn: () => reservationService.cancel(id),
    onSuccess: () => void query.refetch(),
  });
  const token = useMutation({
    mutationFn: () => handoverService.getToken(id),
    onSuccess: setHandover,
  });

  if (query.isLoading)
    return (
      <Screen>
        <StateView title="Loading reservation…" kind="loading" />
      </Screen>
    );
  if (query.error || !query.data)
    return (
      <Screen>
        <StateView
          title="Could not load this reservation"
          message={getUserFacingErrorMessage(query.error)}
          actionLabel="Back to reservations"
          onAction={() => router.dismissTo('/reservations')}
          kind="error"
        />
      </Screen>
    );

  const reservation = query.data;
  const canCancel = reservation.status === 'PENDING' || reservation.status === 'CONFIRMED';
  return (
    <Screen title="Reservation">
      <Card className="gap-3 p-5">
        <View className="flex-row items-start justify-between gap-3">
          <Typography.Heading type="h2" className="flex-1">
            {reservation.food.title}
          </Typography.Heading>
          <StatusBadge
            label={reservation.status.replaceAll('_', ' ')}
            tone={
              reservation.status === 'READY'
                ? 'warning'
                : reservation.status === 'COMPLETED'
                  ? 'success'
                  : 'neutral'
            }
          />
        </View>
        <Typography.Paragraph>
          {reservation.quantity} servings from {reservation.food.providerName}
        </Typography.Paragraph>
        <Typography.Paragraph>
          {formatPickupWindow(reservation.pickupStart, reservation.pickupEnd)}
        </Typography.Paragraph>
      </Card>

      <Card className="gap-2 p-4">
        <Typography.Heading type="h4">Pickup instructions</Typography.Heading>
        <Typography.Paragraph>
          {reservation.pickupAddress ??
            'Pickup address will be shown when the reservation is confirmed.'}
        </Typography.Paragraph>
        {reservation.handoverInstructions ? (
          <Typography.Paragraph color="muted">
            {reservation.handoverInstructions}
          </Typography.Paragraph>
        ) : null}
      </Card>

      {reservation.canDisplayHandoverQr ? (
        <Card className="gap-3 p-4">
          <Typography.Heading type="h4">Secure handover</Typography.Heading>
          {handover ? (
            <QRCodeView token={handover.token} expiresAt={handover.expiresAt} />
          ) : (
            <AppButton
              label="Generate pickup QR"
              onPress={() => token.mutate()}
              isLoading={token.isPending}
            />
          )}
          {token.error ? (
            <Typography.Paragraph className="text-danger" accessibilityRole="alert">
              {getUserFacingErrorMessage(token.error)}
            </Typography.Paragraph>
          ) : null}
        </Card>
      ) : null}

      <View className="gap-3">
        <Typography.Heading type="h4">Status history</Typography.Heading>
        {reservation.events.map((event) => (
          <View key={event.id} className="border-accent border-l-2 pl-3">
            <Typography.Paragraph weight="semibold">
              {event.newState.replaceAll('_', ' ')}
            </Typography.Paragraph>
            <Typography.Paragraph type="body-xs" color="muted">
              {event.actorLabel} · {new Date(event.occurredAt).toLocaleString('en-PK')}
            </Typography.Paragraph>
          </View>
        ))}
      </View>

      {canCancel ? (
        <AppButton
          label="Cancel reservation"
          variant="danger"
          onPress={() => cancel.mutate()}
          isLoading={cancel.isPending}
        />
      ) : null}
      <AppButton
        label="Report an issue"
        variant="ghost"
        onPress={() => router.push({ pathname: '/reports/new', params: { reservationId: id } })}
      />
      {cancel.error ? (
        <Typography.Paragraph className="text-danger" accessibilityRole="alert">
          {getUserFacingErrorMessage(cancel.error)}
        </Typography.Paragraph>
      ) : null}
    </Screen>
  );
}
