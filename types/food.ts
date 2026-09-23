export const FOOD_STATUSES = [
  'DRAFT',
  'PUBLISHED',
  'RESERVED',
  'READY',
  'COMPLETED',
  'EXPIRED',
  'CANCELLED',
  'FLAGGED',
] as const;

export type FoodStatus = (typeof FOOD_STATUSES)[number];
export type FoodPriceFilter = 'ALL' | 'FREE' | 'DISCOUNTED';

export type FoodListingSummary = {
  id: string;
  title: string;
  providerName: string;
  providerVerified: boolean;
  imageUrl: string | null;
  servingsAvailable: number;
  isFree: boolean;
  price: number | null;
  currency: 'PKR';
  pickupStart: string;
  pickupEnd: string;
  area: string;
  approximateDistanceKm: number | null;
  status: FoodStatus;
  dietaryInformation: string[];
};

export type FoodListingDetail = FoodListingSummary & {
  description: string;
  categoryId: string;
  quantity: number;
  unit: string;
  ingredients: string[];
  allergens: string[];
  storageInformation: string | null;
  expiresAt: string;
  exactPickupAddress: string | null;
  latitude: number | null;
  longitude: number | null;
};

export type FoodSearchParams = {
  search?: string;
  city?: string;
  area?: string;
  latitude?: number;
  longitude?: number;
  radiusKm?: number;
  categoryId?: string;
  price?: FoodPriceFilter;
  dietaryType?: string;
  pickupAfter?: string;
  pickupBefore?: string;
  deliveryAvailable?: boolean;
  endingSoon?: boolean;
  page: number;
  pageSize: number;
};

export type CreateFoodDraftInput = {
  title: string;
  description: string;
  categoryId: string;
  quantity: number;
  servings: number;
  unit: string;
  price: number | null;
  isFree: boolean;
  pickupStart: string;
  pickupEnd: string;
  locationId: string;
  ingredients: string[];
  allergens: string[];
  dietaryInformation: string[];
  storageInformation: string;
  preparationTime: string;
  providerSafetyConfirmed: boolean;
};
