import { z } from 'zod';
import { apiRequest } from '@/services/api/client';
import type { PaginatedResponse } from '@/types/domain';
import {
  DELIVERY_TASK_STATUSES,
  type DeliveryStop,
  type DeliveryTaskDetail,
  type DeliveryTaskStatus,
  type DeliveryTaskSummary,
} from '@/types/delivery';

const coordinateSchema = z.object({ latitude: z.number(), longitude: z.number() });
const summarySchema = z.object({
  id: z.string().uuid(),
  status: z.enum(DELIVERY_TASK_STATUSES),
  food_title: z.string(),
  servings: z.number().int().positive(),
  pickup_area: z.string(),
  dropoff_area: z.string(),
  pickup_start: z.string(),
  pickup_end: z.string(),
  distance_km: z.number().nonnegative().nullable(),
  updated_at: z.string(),
});
const stopSchema = z.object({
  area: z.string(),
  address: z.string().nullable(),
  coordinate: coordinateSchema.nullable(),
  instructions: z.string().nullable(),
});
const detailSchema = summarySchema.extend({
  pickup: stopSchema,
  dropoff: stopSchema,
  allowed_transitions: z.array(z.enum(DELIVERY_TASK_STATUSES)),
  events: z.array(
    z.object({
      id: z.string().uuid(),
      previous_state: z.enum(DELIVERY_TASK_STATUSES).nullable(),
      new_state: z.enum(DELIVERY_TASK_STATUSES),
      actor_label: z.string(),
      occurred_at: z.string(),
    }),
  ),
});
const pageSchema = z.object({
  items: z.array(summarySchema),
  meta: z.object({
    page: z.number().int().positive(),
    page_size: z.number().int().positive(),
    total_items: z.number().int().nonnegative(),
    total_pages: z.number().int().nonnegative(),
  }),
});

function mapSummary(value: z.infer<typeof summarySchema>): DeliveryTaskSummary {
  return {
    id: value.id,
    status: value.status,
    foodTitle: value.food_title,
    servings: value.servings,
    pickupArea: value.pickup_area,
    dropoffArea: value.dropoff_area,
    pickupStart: value.pickup_start,
    pickupEnd: value.pickup_end,
    distanceKm: value.distance_km,
    updatedAt: value.updated_at,
  };
}

function mapStop(value: z.infer<typeof stopSchema>): DeliveryStop {
  return value;
}

function mapDetail(value: z.infer<typeof detailSchema>): DeliveryTaskDetail {
  return {
    ...mapSummary(value),
    pickup: mapStop(value.pickup),
    dropoff: mapStop(value.dropoff),
    allowedTransitions: value.allowed_transitions,
    events: value.events.map((event) => ({
      id: event.id,
      previousState: event.previous_state,
      newState: event.new_state,
      actorLabel: event.actor_label,
      occurredAt: event.occurred_at,
    })),
  };
}

function mapPage(value: z.infer<typeof pageSchema>): PaginatedResponse<DeliveryTaskSummary> {
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

export interface DeliveryService {
  listAvailable(
    page: number,
    signal?: AbortSignal,
  ): Promise<PaginatedResponse<DeliveryTaskSummary>>;
  listMine(
    page: number,
    status?: 'active' | 'completed',
    signal?: AbortSignal,
  ): Promise<PaginatedResponse<DeliveryTaskSummary>>;
  getById(id: string, signal?: AbortSignal): Promise<DeliveryTaskDetail>;
  accept(id: string, signal?: AbortSignal): Promise<DeliveryTaskDetail>;
  transition(
    id: string,
    status: DeliveryTaskStatus,
    signal?: AbortSignal,
  ): Promise<DeliveryTaskDetail>;
}

export const deliveryService: DeliveryService = {
  async listAvailable(page, signal) {
    const response = await apiRequest({
      path: '/api/v1/deliveries/available',
      query: { page, page_size: 20 },
      signal,
    });
    return mapPage(pageSchema.parse(response.data));
  },
  async listMine(page, status = 'active', signal) {
    const response = await apiRequest({
      path: '/api/v1/deliveries',
      query: { page, page_size: 20, status },
      signal,
    });
    return mapPage(pageSchema.parse(response.data));
  },
  async getById(id, signal) {
    const response = await apiRequest({
      path: `/api/v1/deliveries/${encodeURIComponent(id)}`,
      signal,
    });
    return mapDetail(detailSchema.parse(response.data));
  },
  async accept(id, signal) {
    const response = await apiRequest({
      path: `/api/v1/deliveries/${encodeURIComponent(id)}/accept`,
      method: 'POST',
      signal,
      retry: false,
    });
    return mapDetail(detailSchema.parse(response.data));
  },
  async transition(id, status, signal) {
    const response = await apiRequest<{ status: DeliveryTaskStatus }>({
      path: `/api/v1/deliveries/${encodeURIComponent(id)}/transitions`,
      method: 'POST',
      body: { status },
      signal,
      retry: false,
    });
    return mapDetail(detailSchema.parse(response.data));
  },
};
