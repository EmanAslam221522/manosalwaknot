import { z } from 'zod';
import { apiRequest } from '@/services/api/client';
import { REPORT_REASONS, type ReportReason, type ReportRecord } from '@/types/trust';

const reportSchema = z.object({
  id: z.string().uuid(),
  reason: z.enum(REPORT_REASONS),
  status: z.enum(['OPEN', 'UNDER_REVIEW', 'RESOLVED', 'DISMISSED']),
  created_at: z.string().datetime({ offset: true }),
  updated_at: z.string().datetime({ offset: true }),
});

function mapReport(value: z.infer<typeof reportSchema>): ReportRecord {
  return {
    id: value.id,
    reason: value.reason,
    status: value.status,
    createdAt: value.created_at,
    updatedAt: value.updated_at,
  };
}

export const reportService = {
  async create(
    input: {
      foodListingId?: string;
      reservationId?: string;
      reason: ReportReason;
      details: string;
    },
    signal?: AbortSignal,
  ): Promise<ReportRecord> {
    const response = await apiRequest<{
      food_listing_id?: string;
      reservation_id?: string;
      reason: ReportReason;
      details: string;
    }>({
      path: '/api/v1/reports',
      method: 'POST',
      body: {
        food_listing_id: input.foodListingId,
        reservation_id: input.reservationId,
        reason: input.reason,
        details: input.details,
      },
      signal,
      retry: false,
    });
    return mapReport(reportSchema.parse(response.data));
  },
};
