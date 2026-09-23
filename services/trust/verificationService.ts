import { z } from 'zod';
import { apiRequest } from '@/services/api/client';
import type { VerificationRecord, VerificationType } from '@/types/trust';

const verificationSchema = z.object({
  id: z.string().uuid().nullable(),
  type: z.enum(['PROVIDER', 'ORGANIZATION', 'VOLUNTEER']),
  status: z.enum(['NOT_SUBMITTED', 'PENDING', 'APPROVED', 'REJECTED', 'NEEDS_INFORMATION']),
  submitted_at: z.string().datetime({ offset: true }).nullable(),
  reviewer_message: z.string().nullable(),
});

function mapVerification(value: z.infer<typeof verificationSchema>): VerificationRecord {
  return {
    id: value.id,
    type: value.type,
    status: value.status,
    submittedAt: value.submitted_at,
    reviewerMessage: value.reviewer_message,
  };
}

export const verificationService = {
  async getMine(signal?: AbortSignal): Promise<VerificationRecord[]> {
    const response = await apiRequest({ path: '/api/v1/verification-requests/me', signal });
    return z.array(verificationSchema).parse(response.data).map(mapVerification);
  },
  async submit(
    type: VerificationType,
    statement: string,
    signal?: AbortSignal,
  ): Promise<VerificationRecord> {
    const response = await apiRequest<{ type: VerificationType; statement: string }>({
      path: '/api/v1/verification-requests',
      method: 'POST',
      body: { type, statement },
      signal,
      retry: false,
    });
    return mapVerification(verificationSchema.parse(response.data));
  },
};
