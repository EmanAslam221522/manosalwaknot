import { Image, View } from 'react-native';
import { Card, PressableFeedback, Typography } from 'heroui-native';
import { MapPin, ShieldCheck } from 'lucide-react-native';
import type { FoodListingSummary } from '@/types/food';
import { formatDistance, formatPickupWindow, formatPrice } from '@/utils/formatting';
import { AppButton } from '@/components/ui/AppButton';
import { StatusBadge } from '@/components/ui/StatusBadge';

export function FoodCard({
  listing,
  onPress,
  onReserve,
}: {
  listing: FoodListingSummary;
  onPress: () => void;
  onReserve?: () => void;
}) {
  return (
    <PressableFeedback
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`View ${listing.title}`}
    >
      <Card className="overflow-hidden p-0">
        {listing.imageUrl ? (
          <Image
            source={{ uri: listing.imageUrl }}
            style={{ width: '100%', height: 156 }}
            resizeMode="cover"
            accessibilityLabel={`Food listing: ${listing.title}`}
          />
        ) : (
          <View className="bg-accent-soft h-28 items-center justify-center">
            <Typography.Paragraph color="muted">No image</Typography.Paragraph>
          </View>
        )}
        <View className="gap-3 p-4">
          <View className="flex-row items-start justify-between gap-3">
            <View className="flex-1 gap-1">
              <Typography.Heading type="h4" numberOfLines={2}>
                {listing.title}
              </Typography.Heading>
              <View className="flex-row items-center gap-1.5">
                <Typography.Paragraph type="body-sm" color="muted" numberOfLines={1}>
                  {listing.providerName}
                </Typography.Paragraph>
                {listing.providerVerified ? (
                  <ShieldCheck size={15} color="#26734d" accessibilityLabel="Verified provider" />
                ) : null}
              </View>
            </View>
            <StatusBadge
              label={formatPrice(listing.isFree, listing.price)}
              tone={listing.isFree ? 'success' : 'warning'}
            />
          </View>
          <View className="gap-1.5">
            <View className="flex-row items-center gap-2">
              <MapPin size={16} color="#5f6f64" />
              <Typography.Paragraph type="body-sm" color="muted">
                {listing.area} · {formatDistance(listing.approximateDistanceKm)}
              </Typography.Paragraph>
            </View>
            <Typography.Paragraph type="body-sm">
              {listing.servingsAvailable} servings ·{' '}
              {formatPickupWindow(listing.pickupStart, listing.pickupEnd)}
            </Typography.Paragraph>
          </View>
          {onReserve ? <AppButton label="Reserve" onPress={onReserve} /> : null}
        </View>
      </Card>
    </PressableFeedback>
  );
}
