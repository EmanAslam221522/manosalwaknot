import { z } from 'zod';
import { apiRequest } from '@/services/api/client';
import { reservationService } from '@/services/reservations/reservationService';
import type { ReservationDetail } from '@/types/reservation';
import type { HandoverToken } from '@/types/trust';

const handoverTokenSchema = z.object({ token: z.string().min(24), expires_at: z.string() });
const confirmationSchema = z.object({ reservation_id: z.string().uuid() });

export const handoverService = {
  async getToken(reservationId: string, signal?: AbortSignal): Promise<HandoverToken> {
    const response = await apiRequest({
      path: `/api/v1/reservations/${encodeURIComponent(reservationId)}/handover-token`,
      method: 'POST',
      signal,
      retry: false,
    });
    const value = handoverTokenSchema.parse(response.data);
    return { token: value.token, expiresAt: value.expires_at };
  },

  async confirm(token: string, signal?: AbortSignal): Promise<ReservationDetail> {
    const response = await apiRequest<{ token: string }>({
      path: '/api/v1/handovers/confirm',
      method: 'POST',
      body: { token },
      signal,
      retry: false,
    });
    const confirmation = confirmationSchema.parse(response.data);
    return reservationService.getById(confirmation.reservation_id, signal);
  },
};
