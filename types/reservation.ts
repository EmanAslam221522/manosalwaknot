import type { FoodListingSummary } from './food';

export const RESERVATION_STATUSES = [
  'PENDING',
  'CONFIRMED',
  'READY',
  'PICKED_UP',
  'DELIVERED',
  'COMPLETED',
  'CANCELLED',
  'EXPIRED',
  'NO_SHOW',
  'DISPUTED',
] as const;

export type ReservationStatus = (typeof RESERVATION_STATUSES)[number];

export type ReservationSummary = {
  id: string;
  food: FoodListingSummary;
  quantity: number;
  status: ReservationStatus;
  pickupStart: string;
  pickupEnd: string;
  updatedAt: string;
};

export type ReservationEvent = {
  id: string;
  previousState: ReservationStatus | null;
  newState: ReservationStatus;
  occurredAt: string;
  actorLabel: string;
};

export type ReservationDetail = ReservationSummary & {
  pickupAddress: string | null;
  handoverInstructions: string | null;
  canDisplayHandoverQr: boolean;
  handoverToken: string | null;
  events: ReservationEvent[];
};
