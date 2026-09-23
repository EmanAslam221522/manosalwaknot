import { useInfiniteQuery, useMutation } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { FlatList, View } from 'react-native';
import { Card, Typography } from 'heroui-native';
import { AppButton } from '@/components/ui/AppButton';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { notificationService } from '@/services/notifications/notificationService';

export default function NotificationsScreen() {
  const [pushMessage, setPushMessage] = useState<string | null>(null);
  const query = useInfiniteQuery({
    queryKey: ['notifications'],
    initialPageParam: 1,
    queryFn: ({ pageParam, signal }) => notificationService.list(pageParam, signal),
    getNextPageParam: (page) =>
      page.meta.page < page.meta.totalPages ? page.meta.page + 1 : undefined,
  });
  const push = useMutation({
    mutationFn: () => notificationService.enablePush(),
    onSuccess: (result) =>
      setPushMessage(
        result === 'enabled'
          ? 'Push notifications are enabled.'
          : result === 'denied'
            ? 'Permission was not granted. You can enable it in device settings.'
            : 'Push notifications are available in the Android app.',
      ),
  });
  const items = useMemo(() => query.data?.pages.flatMap((page) => page.items) ?? [], [query.data]);
  return (
    <Screen title="Notifications" scroll={false}>
      <View className="gap-2">
        <AppButton
          label="Enable push notifications"
          variant="secondary"
          onPress={() => push.mutate()}
          isLoading={push.isPending}
        />
        {pushMessage ? (
          <Typography.Paragraph type="body-sm" color="muted">
            {pushMessage}
          </Typography.Paragraph>
        ) : null}
      </View>
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        contentContainerClassName="gap-3 pb-safe-or-6"
        renderItem={({ item }) => (
          <Card className="gap-1 p-4">
            <Typography.Paragraph weight={item.readAt ? 'normal' : 'semibold'}>
              {item.title}
            </Typography.Paragraph>
            <Typography.Paragraph type="body-sm" color="muted">
              {item.body}
            </Typography.Paragraph>
            <Typography.Paragraph type="body-xs" color="muted">
              {new Date(item.createdAt).toLocaleString('en-PK')}
            </Typography.Paragraph>
          </Card>
        )}
        ListEmptyComponent={
          query.isLoading ? (
            <StateView title="Loading notifications…" kind="loading" />
          ) : query.error ? (
            <StateView
              title="Could not load notifications"
              message={getUserFacingErrorMessage(query.error)}
              kind="error"
            />
          ) : (
            <StateView title="No notifications" />
          )
        }
        onEndReached={() => {
          if (query.hasNextPage && !query.isFetchingNextPage) void query.fetchNextPage();
        }}
      />
    </Screen>
  );
}
