import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { View } from 'react-native';
import { Card, Typography } from 'heroui-native';
import MapView from '@/components/MapView';
import { AppButton } from '@/components/ui/AppButton';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { useAuthStore } from '@/hooks/auth/useAuthStore';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { deliveryService } from '@/services/delivery/deliveryService';
import type { DeliveryTaskStatus } from '@/types/delivery';
import { formatPickupWindow } from '@/utils/formatting';

const ACTION_LABELS: Partial<Record<DeliveryTaskStatus, string>> = {
  EN_ROUTE_TO_PICKUP: 'Start pickup trip',
  ARRIVED_AT_PICKUP: 'Arrived at pickup',
  PICKED_UP: 'Confirm pickup',
  EN_ROUTE_TO_DROPOFF: 'Start delivery trip',
  DELIVERED: 'Confirm delivery',
  COMPLETED: 'Complete task',
  CANCELLED: 'Cancel task',
};

export default function DeliveryTaskDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const user = useAuthStore((state) => state.user);
  const roles = user?.roles ?? [];
  const queryClient = useQueryClient();
  const [showMap, setShowMap] = useState(true);
  const query = useQuery({
    queryKey: ['delivery', id],
    queryFn: ({ signal }) => deliveryService.getById(id, signal),
    enabled: Boolean(id) && roles.includes('VOLUNTEER'),
  });
  const accept = useMutation({
    mutationFn: () => deliveryService.accept(id),
    onSuccess: (task) => {
      queryClient.setQueryData(['delivery', id], task);
      void queryClient.invalidateQueries({ queryKey: ['deliveries'] });
    },
  });
  const transition = useMutation({
    mutationFn: (status: DeliveryTaskStatus) => deliveryService.transition(id, status),
    onSuccess: (task) => {
      queryClient.setQueryData(['delivery', id], task);
      void queryClient.invalidateQueries({ queryKey: ['deliveries'] });
    },
  });
  const markers = useMemo(() => {
    if (!query.data) return [];
    return [
      query.data.pickup.coordinate
        ? {
            id: 'pickup',
            coordinate: query.data.pickup.coordinate,
            title: 'Pickup',
            color: 'orange' as const,
          }
        : null,
      query.data.dropoff.coordinate
        ? {
            id: 'dropoff',
            coordinate: query.data.dropoff.coordinate,
            title: 'Drop-off',
            color: 'green' as const,
          }
        : null,
    ].filter((marker) => marker !== null);
  }, [query.data]);

  if (!roles.includes('VOLUNTEER')) {
    return (
      <Screen>
        <StateView
          title="Volunteer access required"
          message="Your account is not authorized for delivery tasks."
          kind="error"
        />
      </Screen>
    );
  }
  if (query.isLoading)
    return (
      <Screen>
        <StateView title="Loading task…" kind="loading" />
      </Screen>
    );
  if (query.error || !query.data) {
    return (
      <Screen>
        <StateView
          title="Could not load this task"
          message={getUserFacingErrorMessage(query.error)}
          actionLabel="Back to tasks"
          onAction={() => router.dismissTo('/reservations')}
          kind="error"
        />
      </Screen>
    );
  }

  const task = query.data;
  const transitionError = accept.error ?? transition.error;
  return (
    <Screen title="Delivery task">
      <Card className="gap-3 p-5">
        <View className="flex-row items-start justify-between gap-3">
          <Typography.Heading type="h3" className="flex-1">
            {task.foodTitle}
          </Typography.Heading>
          <StatusBadge
            label={task.status.replaceAll('_', ' ')}
            tone={task.status === 'COMPLETED' ? 'success' : 'neutral'}
          />
        </View>
        <Typography.Paragraph>{task.servings} servings</Typography.Paragraph>
        <Typography.Paragraph color="muted">
          {formatPickupWindow(task.pickupStart, task.pickupEnd)}
        </Typography.Paragraph>
      </Card>

      <Card className="gap-3 p-4">
        <Typography.Heading type="h4">Pickup</Typography.Heading>
        <Typography.Paragraph>{task.pickup.address ?? task.pickup.area}</Typography.Paragraph>
        {task.pickup.instructions ? (
          <Typography.Paragraph color="muted">{task.pickup.instructions}</Typography.Paragraph>
        ) : null}
        <Typography.Heading type="h4">Drop-off</Typography.Heading>
        <Typography.Paragraph>{task.dropoff.address ?? task.dropoff.area}</Typography.Paragraph>
        {task.dropoff.instructions ? (
          <Typography.Paragraph color="muted">{task.dropoff.instructions}</Typography.Paragraph>
        ) : null}
      </Card>

      {markers.length > 0 ? (
        <Card className="gap-3 p-4">
          <View className="flex-row items-center justify-between">
            <Typography.Heading type="h4">Route</Typography.Heading>
            <AppButton
              label={showMap ? 'Show list only' : 'Show map'}
              variant="ghost"
              onPress={() => setShowMap((value) => !value)}
            />
          </View>
          {showMap ? (
            <MapView
              initialRegion={{
                latitude: markers[0].coordinate.latitude,
                longitude: markers[0].coordinate.longitude,
                latitudeDelta: 0.08,
                longitudeDelta: 0.08,
              }}
              markers={markers}
              polylines={
                markers.length === 2
                  ? [{ id: 'route', coordinates: markers.map((marker) => marker.coordinate) }]
                  : []
              }
              style={{ height: 260, width: '100%' }}
            />
          ) : null}
          <Typography.Paragraph color="muted">
            The address list remains available if maps or location services are unavailable.
          </Typography.Paragraph>
        </Card>
      ) : null}

      <View className="gap-3">
        {task.status === 'AVAILABLE' ? (
          <AppButton
            label="Accept task"
            onPress={() => accept.mutate()}
            isLoading={accept.isPending}
          />
        ) : null}
        {task.allowedTransitions.map((status) => (
          <AppButton
            key={status}
            label={ACTION_LABELS[status] ?? status.replaceAll('_', ' ')}
            variant={status === 'CANCELLED' ? 'danger' : 'primary'}
            onPress={() => transition.mutate(status)}
            isLoading={transition.isPending && transition.variables === status}
            isDisabled={accept.isPending || transition.isPending}
          />
        ))}
        {transitionError ? (
          <Typography.Paragraph className="text-danger" accessibilityRole="alert">
            {getUserFacingErrorMessage(transitionError)}
          </Typography.Paragraph>
        ) : null}
      </View>

      <View className="gap-3">
        <Typography.Heading type="h4">Task history</Typography.Heading>
        {task.events.map((event) => (
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
    </Screen>
  );
}
