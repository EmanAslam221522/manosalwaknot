import { useInfiniteQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { FlatList, View } from 'react-native';
import { Tabs, Typography } from 'heroui-native';
import { DeliveryTaskCard } from '@/components/delivery/DeliveryTaskCard';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { deliveryService } from '@/services/delivery/deliveryService';

export function VolunteerTasksScreen() {
  const [scope, setScope] = useState<'available' | 'mine'>('available');
  const query = useInfiniteQuery({
    queryKey: ['deliveries', scope],
    initialPageParam: 1,
    queryFn: ({ pageParam, signal }) =>
      scope === 'available'
        ? deliveryService.listAvailable(pageParam, signal)
        : deliveryService.listMine(pageParam, 'active', signal),
    getNextPageParam: (lastPage) =>
      lastPage.meta.page < lastPage.meta.totalPages ? lastPage.meta.page + 1 : undefined,
  });
  const tasks = useMemo(() => query.data?.pages.flatMap((page) => page.items) ?? [], [query.data]);

  return (
    <Screen title="Delivery tasks" scroll={false}>
      <Tabs
        value={scope}
        onValueChange={(value) => {
          if (value === 'available' || value === 'mine') setScope(value);
        }}
      >
        <Tabs.List>
          <Tabs.Trigger value="available">
            <Tabs.Label>Available</Tabs.Label>
          </Tabs.Trigger>
          <Tabs.Trigger value="mine">
            <Tabs.Label>My tasks</Tabs.Label>
          </Tabs.Trigger>
        </Tabs.List>
      </Tabs>
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
            <StateView title="Loading delivery tasks…" kind="loading" />
          ) : query.error ? (
            <StateView
              title="Could not load delivery tasks"
              message={getUserFacingErrorMessage(query.error)}
              actionLabel="Try again"
              onAction={() => void query.refetch()}
              kind="error"
            />
          ) : (
            <StateView title={scope === 'available' ? 'No tasks nearby' : 'No active tasks'} />
          )
        }
        ListFooterComponent={
          query.isFetchingNextPage ? (
            <View>
              <Typography.Paragraph align="center" color="muted">
                Loading more…
              </Typography.Paragraph>
            </View>
          ) : null
        }
      />
    </Screen>
  );
}
