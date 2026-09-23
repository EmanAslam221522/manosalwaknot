import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Alert, Image, View } from 'react-native';
import { Card, Typography } from 'heroui-native';
import { useState } from 'react';
import { AppButton } from '@/components/ui/AppButton';
import { AppTextField } from '@/components/ui/AppTextField';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { foodService } from '@/services/food/foodService';
import { reservationService } from '@/services/reservations/reservationService';
import { formatPickupWindow, formatPrice } from '@/utils/formatting';

export default function FoodDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [quantity, setQuantity] = useState('1');
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['food', id],
    queryFn: ({ signal }) => foodService.getById(id, signal),
    enabled: Boolean(id),
  });
  const reserve = useMutation({
    mutationFn: () => reservationService.create(id, Number(quantity)),
    onSuccess: async (reservation) => {
      await queryClient.invalidateQueries({ queryKey: ['food'] });
      await queryClient.invalidateQueries({ queryKey: ['reservations'] });
      router.replace({ pathname: '/reservations/[id]', params: { id: reservation.id } });
    },
  });

  if (query.isLoading)
    return (
      <Screen>
        <StateView title="Loading food details…" kind="loading" />
      </Screen>
    );
  if (query.error || !query.data)
    return (
      <Screen>
        <StateView
          title="Could not load this listing"
          message={getUserFacingErrorMessage(query.error)}
          actionLabel="Go back"
          onAction={() => router.dismissTo('/discover')}
          kind="error"
        />
      </Screen>
    );

  const listing = query.data;
  const submitReservation = () => {
    const requested = Number(quantity);
    if (!Number.isInteger(requested) || requested < 1) {
      Alert.alert('Check quantity', 'Enter a whole number of servings.');
      return;
    }
    reserve.mutate();
  };

  return (
    <Screen>
      {listing.imageUrl ? (
        <Image
          source={{ uri: listing.imageUrl }}
          style={{ width: '100%', height: 230, borderRadius: 20 }}
          resizeMode="cover"
          accessibilityLabel={`Food listing: ${listing.title}`}
        />
      ) : null}
      <View className="gap-3">
        <View className="flex-row items-start justify-between gap-3">
          <Typography.Heading type="h1" className="flex-1">
            {listing.title}
          </Typography.Heading>
          <StatusBadge
            label={formatPrice(listing.isFree, listing.price)}
            tone={listing.isFree ? 'success' : 'warning'}
          />
        </View>
        <Typography.Paragraph color="muted">
          {listing.providerName} · {listing.area}
        </Typography.Paragraph>
        <Typography.Paragraph>{listing.description}</Typography.Paragraph>
      </View>

      <Card className="gap-2 p-4">
        <Typography.Heading type="h4">Pickup</Typography.Heading>
        <Typography.Paragraph>
          {formatPickupWindow(listing.pickupStart, listing.pickupEnd)}
        </Typography.Paragraph>
        <Typography.Paragraph color="muted">
          Exact pickup details are shared only with authorized participants.
        </Typography.Paragraph>
      </Card>

      <Card className="gap-3 p-4">
        <Typography.Heading type="h4">Food information</Typography.Heading>
        <Typography.Paragraph>
          {listing.servingsAvailable} servings currently available
        </Typography.Paragraph>
        <Typography.Paragraph>
          Allergens: {listing.allergens.length ? listing.allergens.join(', ') : 'None reported'}
        </Typography.Paragraph>
        <Typography.Paragraph>
          Storage: {listing.storageInformation ?? 'Not provided'}
        </Typography.Paragraph>
        <Typography.Paragraph type="body-xs" color="muted">
          Food safety information is provided by the provider and is not a safety certification.
        </Typography.Paragraph>
      </Card>

      <Card className="gap-4 p-4">
        <AppTextField
          label="Servings to reserve"
          value={quantity}
          onChangeText={setQuantity}
          keyboardType="number-pad"
          isRequired
        />
        <AppButton label="Reserve food" onPress={submitReservation} isLoading={reserve.isPending} />
        {reserve.error ? (
          <Typography.Paragraph className="text-danger" accessibilityRole="alert">
            {getUserFacingErrorMessage(reserve.error)}
          </Typography.Paragraph>
        ) : null}
        <Typography.Paragraph type="body-xs" color="muted">
          Availability is confirmed by the server when you reserve.
        </Typography.Paragraph>
      </Card>
    </Screen>
  );
}
