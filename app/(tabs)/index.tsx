import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { MapPin, MessageCircle, Search } from 'lucide-react-native';
import { View } from 'react-native';
import { Card, Typography, useThemeColor } from 'heroui-native';
import { FoodCard } from '@/components/food/FoodCard';
import { AppButton } from '@/components/ui/AppButton';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { useAuthStore } from '@/hooks/auth/useAuthStore';
import { foodService } from '@/services/food/foodService';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';

export default function HomeScreen() {
  const user = useAuthStore((state) => state.user);
  const accent = useThemeColor('accent');
  const query = useQuery({
    queryKey: ['food', 'home', user?.city, user?.area],
    queryFn: ({ signal }) =>
      foodService.search(
        { city: user?.city ?? undefined, area: user?.area ?? undefined, page: 1, pageSize: 6 },
        signal,
      ),
    enabled: Boolean(user),
  });

  return (
    <Screen>
      <View className="gap-1 pt-2">
        <Typography.Paragraph color="muted">
          Welcome, {user?.displayName ?? 'neighbor'}
        </Typography.Paragraph>
        <Typography.Heading type="h1">Share food. Strengthen your community.</Typography.Heading>
      </View>

      <Card className="flex-row items-center gap-3 p-4">
        <View className="bg-accent-soft h-11 w-11 items-center justify-center rounded-2xl">
          <MapPin size={22} color={accent} accessibilityElementsHidden />
        </View>
        <View className="flex-1">
          <Typography.Paragraph type="body-xs" color="muted">
            Current area
          </Typography.Paragraph>
          <Typography.Paragraph weight="semibold">
            {user?.area ?? user?.city ?? 'Choose an area'}
          </Typography.Paragraph>
        </View>
        <AppButton
          label="Change"
          size="sm"
          variant="ghost"
          onPress={() => router.push('/location/select')}
        />
      </Card>

      <View className="flex-row gap-3">
        <AppButton
          className="flex-1"
          label="Search food"
          variant="secondary"
          onPress={() => router.push('/discover')}
        >
          <Search size={18} color={accent} />
        </AppButton>
        <AppButton className="flex-1" label="Ask Mano" onPress={() => router.push('/mano')}>
          <MessageCircle size={18} color={accent} />
        </AppButton>
      </View>

      <View className="gap-3">
        <View className="flex-row items-center justify-between">
          <Typography.Heading type="h3">Nearby food</Typography.Heading>
          <AppButton
            label="See all"
            size="sm"
            variant="ghost"
            onPress={() => router.push('/discover')}
          />
        </View>
        {query.isLoading ? <StateView title="Finding available food…" kind="loading" /> : null}
        {query.error ? (
          <StateView
            title="Could not load food"
            message={getUserFacingErrorMessage(query.error)}
            actionLabel="Try again"
            onAction={() => void query.refetch()}
            kind="error"
          />
        ) : null}
        {query.data?.items.length === 0 ? (
          <StateView
            title="No food is available nearby"
            message="Try another area or check again later."
          />
        ) : null}
        {query.data?.items.map((listing) => (
          <FoodCard
            key={listing.id}
            listing={listing}
            onPress={() => router.push({ pathname: '/food/[id]', params: { id: listing.id } })}
          />
        ))}
      </View>
    </Screen>
  );
}
