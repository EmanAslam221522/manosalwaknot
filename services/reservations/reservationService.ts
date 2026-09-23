import { z } from 'zod';
import { apiRequest } from '@/services/api/client';
import {
  RESERVATION_STATUSES,
  type ReservationDetail,
  type ReservationSummary,
} from '@/types/reservation';
import type { PaginatedResponse } from '@/types/domain';
import type { FoodListingSummary } from '@/types/food';

const reservationSummarySchema = z.object({
  id: z.string().uuid(),
  food: z.custom<FoodListingSummary>(),
  quantity: z.number().int().positive(),
  status: z.enum(RESERVATION_STATUSES),
  pickup_start: z.string(),
  pickup_end: z.string(),
  updated_at: z.string(),
});

const reservationDetailSchema = reservationSummarySchema.extend({
  pickup_address: z.string().nullable(),
  handover_instructions: z.string().nullable(),
  can_display_handover_qr: z.boolean(),
  handover_token: z.string().nullable(),
  events: z.array(
    z.object({
      id: z.string().uuid(),
      previous_state: z.enum(RESERVATION_STATUSES).nullable(),
      new_state: z.enum(RESERVATION_STATUSES),
      occurred_at: z.string(),
      actor_label: z.string(),
    }),
  ),
});

function mapSummary(value: z.infer<typeof reservationSummarySchema>): ReservationSummary {
  return {
    id: value.id,
    food: value.food,
    quantity: value.quantity,
    status: value.status,
    pickupStart: value.pickup_start,
    pickupEnd: value.pickup_end,
    updatedAt: value.updated_at,
  };
}

export interface ReservationService {
  list(page: number, signal?: AbortSignal): Promise<PaginatedResponse<ReservationSummary>>;
  getById(id: string, signal?: AbortSignal): Promise<ReservationDetail>;
  create(foodListingId: string, quantity: number, signal?: AbortSignal): Promise<ReservationDetail>;
  cancel(id: string, signal?: AbortSignal): Promise<ReservationDetail>;
}

export const reservationService: ReservationService = {
  async list(page, signal) {
    const response = await apiRequest({
      path: '/api/v1/reservations',
      query: { page, page_size: 20 },
      signal,
    });
    const value = z
      .object({
        items: z.array(reservationSummarySchema),
        meta: z.object({
          page: z.number(),
          page_size: z.number(),
          total_items: z.number(),
          total_pages: z.number(),
        }),
      })
      .parse(response.data);
    return {
      items: value.items.map(mapSummary),
      meta: {
        page: value.meta.page,
        pageSize: value.meta.page_size,
        totalItems: value.meta.total_items,
        totalPages: value.meta.total_pages,
      },
    };
  },

  async getById(id, signal) {
    const response = await apiRequest({ path: `/api/v1/reservations/${id}`, signal });
    const value = reservationDetailSchema.parse(response.data);
    return {
      ...mapSummary(value),
      pickupAddress: value.pickup_address,
      handoverInstructions: value.handover_instructions,
      canDisplayHandoverQr: value.can_display_handover_qr,
      handoverToken: value.handover_token,
      events: value.events.map((event) => ({
        id: event.id,
        previousState: event.previous_state,
        newState: event.new_state,
        occurredAt: event.occurred_at,
        actorLabel: event.actor_label,
      })),
    };
  },

  async create(foodListingId, quantity, signal) {
    const response = await apiRequest<{ food_listing_id: string; quantity: number }>({
      path: '/api/v1/reservations',
      method: 'POST',
      body: { food_listing_id: foodListingId, quantity },
      signal,
      retry: false,
    });
    const value = reservationDetailSchema.parse(response.data);
    return {
      ...mapSummary(value),
      pickupAddress: value.pickup_address,
      handoverInstructions: value.handover_instructions,
      canDisplayHandoverQr: value.can_display_handover_qr,
      handoverToken: value.handover_token,
      events: value.events.map((event) => ({
        id: event.id,
        previousState: event.previous_state,
        newState: event.new_state,
        occurredAt: event.occurred_at,
        actorLabel: event.actor_label,
      })),
    };
  },

  async cancel(id, signal) {
    const response = await apiRequest({
      path: `/api/v1/reservations/${id}/cancel`,
      method: 'POST',
      signal,
      retry: false,
    });
    const value = reservationDetailSchema.parse(response.data);
    return {
      ...mapSummary(value),
      pickupAddress: value.pickup_address,
      handoverInstructions: value.handover_instructions,
      canDisplayHandoverQr: value.can_display_handover_qr,
      handoverToken: value.handover_token,
      events: value.events.map((event) => ({
        id: event.id,
        previousState: event.previous_state,
        newState: event.new_state,
        occurredAt: event.occurred_at,
        actorLabel: event.actor_label,
      })),
    };
  },
};
