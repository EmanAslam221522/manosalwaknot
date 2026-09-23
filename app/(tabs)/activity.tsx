import { useInfiniteQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo } from 'react';
import { FlatList } from 'react-native';
import { DeliveryTaskCard } from '@/components/delivery/DeliveryTaskCard';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { useAuthStore } from '@/hooks/auth/useAuthStore';
import { getActiveExperience, useExperienceStore } from '@/hooks/auth/useExperienceStore';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { deliveryService } from '@/services/delivery/deliveryService';

export default function ActivityScreen() {
  const user = useAuthStore((state) => state.user);
  const selectedRole = useExperienceStore((state) => state.selectedRole);
  const experience = getActiveExperience(user?.roles ?? [], selectedRole);
  const query = useInfiniteQuery({
    queryKey: ['deliveries', 'history'],
    initialPageParam: 1,
    queryFn: ({ pageParam, signal }) => deliveryService.listMine(pageParam, 'completed', signal),
    getNextPageParam: (lastPage) =>
      lastPage.meta.page < lastPage.meta.totalPages ? lastPage.meta.page + 1 : undefined,
    enabled: experience === 'VOLUNTEER',
  });
  const tasks = useMemo(() => query.data?.pages.flatMap((page) => page.items) ?? [], [query.data]);

  if (experience !== 'VOLUNTEER') {
    return (
      <Screen title="Activity">
        <StateView
          title="No completed activity yet"
          message="Completed pickups and verified impact will appear here from the server."
        />
      </Screen>
    );
  }
  return (
    <Screen title="Delivery history" scroll={false}>
      <FlatList
        data={tasks}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <DeliveryTaskCard
            task={item}
            onPress={() => router.push({ pathname: '/deliveries/[id]', params: { id: item.id } })}
          />
        )}
        contentContainerClassName="gap-4 pb-safe-or-6"
        onEndReached={() => {
          if (query.hasNextPage && !query.isFetchingNextPage) void query.fetchNextPage();
        }}
        ListEmptyComponent={
          query.isLoading ? (
            <StateView title="Loading history…" kind="loading" />
          ) : query.error ? (
            <StateView
              title="Could not load delivery history"
              message={getUserFacingErrorMessage(query.error)}
              actionLabel="Try again"
              onAction={() => void query.refetch()}
              kind="error"
            />
          ) : (
            <StateView title="No completed deliveries" />
          )
        }
      />
    </Screen>
  );
}
