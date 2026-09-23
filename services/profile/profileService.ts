import { z } from 'zod';
import { apiRequest } from '@/services/api/client';
import { USER_ROLES, type UserSummary } from '@/types/domain';

const userSchema = z.object({
  id: z.string().uuid(),
  display_name: z.string().min(1),
  email: z.string().email().nullable(),
  phone_number: z.string().nullable(),
  roles: z.array(z.enum(USER_ROLES)),
  city: z.string().nullable(),
  area: z.string().nullable(),
  is_verified: z.boolean(),
});

function mapUser(payload: unknown): UserSummary {
  const value = userSchema.parse(payload);
  return {
    id: value.id,
    displayName: value.display_name,
    email: value.email,
    phoneNumber: value.phone_number,
    roles: value.roles,
    city: value.city,
    area: value.area,
    isVerified: value.is_verified,
  };
}

export const profileService = {
  async updateDiscoveryArea(
    city: string,
    area: string,
    signal?: AbortSignal,
  ): Promise<UserSummary> {
    const response = await apiRequest<{ city: string; area: string }>({
      path: '/api/v1/users/me/location-preference',
      method: 'PUT',
      body: { city, area },
      signal,
      retry: false,
    });
    return mapUser(response.data);
  },
};
