import { useInfiniteQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo } from 'react';
import { FlatList } from 'react-native';
import { Typography } from 'heroui-native';
import { ReservationCard } from '@/components/reservation/ReservationCard';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { reservationService } from '@/services/reservations/reservationService';
import { VolunteerTasksScreen } from '@/components/delivery/VolunteerTasksScreen';
import { useAuthStore } from '@/hooks/auth/useAuthStore';
import { getActiveExperience, useExperienceStore } from '@/hooks/auth/useExperienceStore';

export default function ReservationsScreen() {
  const user = useAuthStore((state) => state.user);
  const selectedRole = useExperienceStore((state) => state.selectedRole);
  const experience = getActiveExperience(user?.roles ?? [], selectedRole);
  if (experience === 'VOLUNTEER') return <VolunteerTasksScreen />;
  return <ReservationsList />;
}

function ReservationsList() {
  const query = useInfiniteQuery({
    queryKey: ['reservations'],
    initialPageParam: 1,
    queryFn: ({ pageParam, signal }) => reservationService.list(pageParam, signal),
    getNextPageParam: (lastPage) =>
      lastPage.meta.page < lastPage.meta.totalPages ? lastPage.meta.page + 1 : undefined,
  });
  const reservations = useMemo(
    () => query.data?.pages.flatMap((page) => page.items) ?? [],
    [query.data],
  );

  return (
    <Screen title="Reservations" scroll={false}>
      <FlatList
        data={reservations}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <ReservationCard
            reservation={item}
            onPress={() => router.push({ pathname: '/reservations/[id]', params: { id: item.id } })}
          />
        )}
        contentContainerClassName="gap-4 pb-safe-or-6"
        onEndReached={() => {
          if (query.hasNextPage && !query.isFetchingNextPage) void query.fetchNextPage();
        }}
        ListEmptyComponent={
          query.isLoading ? (
            <StateView title="Loading reservations…" kind="loading" />
          ) : query.error ? (
            <StateView
              title="Could not load reservations"
              message={getUserFacingErrorMessage(query.error)}
              actionLabel="Try again"
              onAction={() => void query.refetch()}
              kind="error"
            />
          ) : (
            <StateView
              title="No reservations yet"
              message="Reserve available food and it will appear here."
            />
          )
        }
        ListFooterComponent={
          query.isFetchingNextPage ? (
            <Typography.Paragraph align="center" color="muted">
              Loading more…
            </Typography.Paragraph>
          ) : null
        }
      />
    </Screen>
  );
}
