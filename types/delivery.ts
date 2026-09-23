import type { LatLng } from '@/components/MapView.types';

export const DELIVERY_TASK_STATUSES = [
  'AVAILABLE',
  'ACCEPTED',
  'EN_ROUTE_TO_PICKUP',
  'ARRIVED_AT_PICKUP',
  'PICKED_UP',
  'EN_ROUTE_TO_DROPOFF',
  'DELIVERED',
  'COMPLETED',
  'CANCELLED',
] as const;

export type DeliveryTaskStatus = (typeof DELIVERY_TASK_STATUSES)[number];

export type DeliveryStop = {
  area: string;
  address: string | null;
  coordinate: LatLng | null;
  instructions: string | null;
};

export type DeliveryTaskSummary = {
  id: string;
  status: DeliveryTaskStatus;
  foodTitle: string;
  servings: number;
  pickupArea: string;
  dropoffArea: string;
  pickupStart: string;
  pickupEnd: string;
  distanceKm: number | null;
  updatedAt: string;
};

export type DeliveryTaskEvent = {
  id: string;
  previousState: DeliveryTaskStatus | null;
  newState: DeliveryTaskStatus;
  actorLabel: string;
  occurredAt: string;
};

export type DeliveryTaskDetail = DeliveryTaskSummary & {
  pickup: DeliveryStop;
  dropoff: DeliveryStop;
  allowedTransitions: DeliveryTaskStatus[];
  events: DeliveryTaskEvent[];
};
