import { z } from 'zod';
import { apiRequest } from '@/services/api/client';
import {
  FOOD_STATUSES,
  type CreateFoodDraftInput,
  type FoodListingDetail,
  type FoodListingSummary,
  type FoodSearchParams,
} from '@/types/food';
import type { PaginatedResponse } from '@/types/domain';

const foodSummarySchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  provider_name: z.string(),
  provider_verified: z.boolean(),
  image_url: z.string().url().nullable(),
  servings_available: z.number().int().nonnegative(),
  is_free: z.boolean(),
  price: z.number().nonnegative().nullable(),
  currency: z.literal('PKR'),
  pickup_start: z.string(),
  pickup_end: z.string(),
  area: z.string(),
  approximate_distance_km: z.number().nonnegative().nullable(),
  status: z.enum(FOOD_STATUSES),
  dietary_information: z.array(z.string()),
});

const pageSchema = z.object({
  items: z.array(foodSummarySchema),
  meta: z.object({
    page: z.number().int().positive(),
    page_size: z.number().int().positive(),
    total_items: z.number().int().nonnegative(),
    total_pages: z.number().int().nonnegative(),
  }),
});

const detailSchema = foodSummarySchema.extend({
  description: z.string(),
  category_id: z.string().uuid(),
  quantity: z.number().nonnegative(),
  unit: z.string(),
  ingredients: z.array(z.string()),
  allergens: z.array(z.string()),
  storage_information: z.string().nullable(),
  expires_at: z.string(),
  exact_pickup_address: z.string().nullable(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
});

function mapSummary(value: z.infer<typeof foodSummarySchema>): FoodListingSummary {
  return {
    id: value.id,
    title: value.title,
    providerName: value.provider_name,
    providerVerified: value.provider_verified,
    imageUrl: value.image_url,
    servingsAvailable: value.servings_available,
    isFree: value.is_free,
    price: value.price,
    currency: value.currency,
    pickupStart: value.pickup_start,
    pickupEnd: value.pickup_end,
    area: value.area,
    approximateDistanceKm: value.approximate_distance_km,
    status: value.status,
    dietaryInformation: value.dietary_information,
  };
}

function mapPage(payload: unknown): PaginatedResponse<FoodListingSummary> {
  const value = pageSchema.parse(payload);
  return {
    items: value.items.map(mapSummary),
    meta: {
      page: value.meta.page,
      pageSize: value.meta.page_size,
      totalItems: value.meta.total_items,
      totalPages: value.meta.total_pages,
    },
  };
}

export interface FoodService {
  search(
    params: FoodSearchParams,
    signal?: AbortSignal,
  ): Promise<PaginatedResponse<FoodListingSummary>>;
  getById(id: string, signal?: AbortSignal): Promise<FoodListingDetail>;
  getMyListings(page: number, signal?: AbortSignal): Promise<PaginatedResponse<FoodListingSummary>>;
  createDraft(input: CreateFoodDraftInput, signal?: AbortSignal): Promise<FoodListingDetail>;
  publish(id: string, signal?: AbortSignal): Promise<FoodListingDetail>;
}

export const foodService: FoodService = {
  async search(params, signal) {
    const response = await apiRequest({
      path: '/api/v1/food',
      query: {
        q: params.search,
        city: params.city,
        area: params.area,
        lat: params.latitude,
        lng: params.longitude,
        radius_km: params.radiusKm,
        category_id: params.categoryId,
        price: params.price === 'ALL' ? undefined : params.price,
        dietary_type: params.dietaryType,
        pickup_after: params.pickupAfter,
        pickup_before: params.pickupBefore,
        delivery_available: params.deliveryAvailable,
        ending_soon: params.endingSoon,
        page: params.page,
        page_size: params.pageSize,
      },
      signal,
    });
    return mapPage(response.data);
  },

  async getById(id, signal) {
    const response = await apiRequest({ path: `/api/v1/food/${id}`, signal });
    const value = detailSchema.parse(response.data);
    return {
      ...mapSummary(value),
      description: value.description,
      categoryId: value.category_id,
      quantity: value.quantity,
      unit: value.unit,
      ingredients: value.ingredients,
      allergens: value.allergens,
      storageInformation: value.storage_information,
      expiresAt: value.expires_at,
      exactPickupAddress: value.exact_pickup_address,
      latitude: value.latitude,
      longitude: value.longitude,
    };
  },

  async getMyListings(page, signal) {
    const response = await apiRequest({
      path: '/api/v1/providers/me/food',
      query: { page, page_size: 20 },
      signal,
    });
    return mapPage(response.data);
  },

  async createDraft(input, signal) {
    const response = await apiRequest({
      path: '/api/v1/food',
      method: 'POST',
      body: {
        title: input.title,
        description: input.description,
        category_id: input.categoryId,
        quantity: input.quantity,
        servings: input.servings,
        unit: input.unit,
        price: input.price,
        is_free: input.isFree,
        pickup_start: input.pickupStart,
        pickup_end: input.pickupEnd,
        location_id: input.locationId,
        ingredients: input.ingredients,
        allergens: input.allergens,
        dietary_information: input.dietaryInformation,
        storage_information: input.storageInformation,
        preparation_time: input.preparationTime,
        provider_safety_confirmed: input.providerSafetyConfirmed,
      },
      signal,
      retry: false,
    });
    const value = detailSchema.parse(response.data);
    return {
      ...mapSummary(value),
      description: value.description,
      categoryId: value.category_id,
      quantity: value.quantity,
      unit: value.unit,
      ingredients: value.ingredients,
      allergens: value.allergens,
      dietaryInformation: value.dietary_information,
      storageInformation: value.storage_information,
      expiresAt: value.expires_at,
      exactPickupAddress: value.exact_pickup_address,
      latitude: value.latitude,
      longitude: value.longitude,
    };
  },

  async publish(id, signal) {
    const response = await apiRequest({
      path: `/api/v1/food/${id}/publish`,
      method: 'POST',
      signal,
      retry: false,
    });
    const value = detailSchema.parse(response.data);
    return {
      ...mapSummary(value),
      description: value.description,
      categoryId: value.category_id,
      quantity: value.quantity,
      unit: value.unit,
      ingredients: value.ingredients,
      allergens: value.allergens,
      storageInformation: value.storage_information,
      expiresAt: value.expires_at,
      exactPickupAddress: value.exact_pickup_address,
      latitude: value.latitude,
      longitude: value.longitude,
    };
  },
};
