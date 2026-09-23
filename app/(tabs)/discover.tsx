import { useInfiniteQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { FlatList, View } from 'react-native';
import { Input, SearchField, Typography } from 'heroui-native';
import { FoodCard } from '@/components/food/FoodCard';
import { AppButton } from '@/components/ui/AppButton';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { foodService } from '@/services/food/foodService';
import type { FoodPriceFilter } from '@/types/food';
import { useAuthStore } from '@/hooks/auth/useAuthStore';
import { getActiveExperience, useExperienceStore } from '@/hooks/auth/useExperienceStore';

export default function DiscoverScreen() {
  const user = useAuthStore((state) => state.user);
  const selectedRole = useExperienceStore((state) => state.selectedRole);
  const experience = getActiveExperience(user?.roles ?? [], selectedRole);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [price, setPrice] = useState<FoodPriceFilter>('ALL');
  const isProvider = experience === 'FOOD_PROVIDER';

  const query = useInfiniteQuery({
    queryKey: ['food', isProvider ? 'mine' : 'discover', search, price, user?.city, user?.area],
    initialPageParam: 1,
    queryFn: ({ pageParam, signal }) =>
      isProvider
        ? foodService.getMyListings(pageParam, signal)
        : foodService.search(
            {
              search: search || undefined,
              price,
              city: user?.city ?? undefined,
              area: user?.area ?? undefined,
              page: pageParam,
              pageSize: 20,
            },
            signal,
          ),
    getNextPageParam: (lastPage) =>
      lastPage.meta.page < lastPage.meta.totalPages ? lastPage.meta.page + 1 : undefined,
  });

  const listings = useMemo(
    () => query.data?.pages.flatMap((page) => page.items) ?? [],
    [query.data],
  );

  return (
    <Screen
      title={isProvider ? 'Your listings' : 'Discover food'}
      scroll={false}
      action={
        isProvider ? (
          <AppButton
            label="Post food"
            size="sm"
            variant="secondary"
            isDisabled
            accessibilityHint="Listing creation becomes available when the required backend metadata endpoints are configured."
          />
        ) : undefined
      }
    >
      {!isProvider ? (
        <View className="gap-3">
          <SearchField value={searchInput} onChange={setSearchInput}>
            <SearchField.Group>
              <SearchField.SearchIcon />
              <Input
                placeholder="Search food or provider"
                returnKeyType="search"
                onSubmitEditing={() => setSearch(searchInput.trim())}
              />
              <SearchField.ClearButton />
            </SearchField.Group>
          </SearchField>
          <View className="flex-row gap-2">
            {(['ALL', 'FREE', 'DISCOUNTED'] as const).map((value) => (
              <AppButton
                key={value}
                label={value === 'ALL' ? 'All' : value === 'FREE' ? 'Free' : 'Discounted'}
                size="sm"
                variant={price === value ? 'primary' : 'secondary'}
                onPress={() => setPrice(value)}
              />
            ))}
          </View>
        </View>
      ) : null}

      <FlatList
        data={listings}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <FoodCard
            listing={item}
            onPress={() => router.push({ pathname: '/food/[id]', params: { id: item.id } })}
          />
        )}
        contentContainerClassName="gap-4 pb-safe-or-6"
        onEndReached={() => {
          if (query.hasNextPage && !query.isFetchingNextPage) void query.fetchNextPage();
        }}
        onEndReachedThreshold={0.4}
        ListEmptyComponent={
          query.isLoading ? (
            <StateView title="Loading listings…" kind="loading" />
          ) : query.error ? (
            <StateView
              title="Could not load listings"
              message={getUserFacingErrorMessage(query.error)}
              actionLabel="Try again"
              onAction={() => void query.refetch()}
              kind="error"
            />
          ) : (
            <StateView
              title={isProvider ? 'No listings yet' : 'No matching food'}
              message={
                isProvider
                  ? 'Post surplus food when it is ready for pickup.'
                  : 'Change your filters or search another area.'
              }
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
