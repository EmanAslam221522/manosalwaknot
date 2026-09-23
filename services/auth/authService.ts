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

const sessionSchema = z.object({
  access_token: z.string().min(1),
  refresh_token: z.string().min(1),
  user: userSchema,
});

export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  user: UserSummary;
};

export type PasswordSignInInput = { email: string; password: string };
export type RequestOtpInput = { phoneNumber: string };
export type VerifyOtpInput = { phoneNumber: string; otp: string };

function mapUser(value: z.infer<typeof userSchema>): UserSummary {
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

function mapSession(payload: unknown): AuthSession {
  const value = sessionSchema.parse(payload);
  return {
    accessToken: value.access_token,
    refreshToken: value.refresh_token,
    user: mapUser(value.user),
  };
}

export interface AuthService {
  signInWithPassword(input: PasswordSignInInput, signal?: AbortSignal): Promise<AuthSession>;
  requestOtp(input: RequestOtpInput, signal?: AbortSignal): Promise<void>;
  verifyOtp(input: VerifyOtpInput, signal?: AbortSignal): Promise<AuthSession>;
  getCurrentUser(signal?: AbortSignal): Promise<UserSummary>;
  signOut(signal?: AbortSignal): Promise<void>;
}

export const authService: AuthService = {
  async signInWithPassword(input, signal) {
    const response = await apiRequest<{ email: string; password: string }>({
      path: '/api/v1/auth/login/password',
      method: 'POST',
      body: input,
      signal,
      requiresAuth: false,
      retry: false,
    });
    return mapSession(response.data);
  },

  async requestOtp(input, signal) {
    await apiRequest<{ phone_number: string }>({
      path: '/api/v1/auth/otp/request',
      method: 'POST',
      body: { phone_number: input.phoneNumber },
      signal,
      requiresAuth: false,
      retry: false,
    });
  },

  async verifyOtp(input, signal) {
    const response = await apiRequest<{ phone_number: string; otp: string }>({
      path: '/api/v1/auth/otp/verify',
      method: 'POST',
      body: { phone_number: input.phoneNumber, otp: input.otp },
      signal,
      requiresAuth: false,
      retry: false,
    });
    return mapSession(response.data);
  },

  async getCurrentUser(signal) {
    const response = await apiRequest({ path: '/api/v1/auth/me', signal });
    return mapUser(userSchema.parse(response.data));
  },

  async signOut(signal) {
    await apiRequest({
      path: '/api/v1/auth/logout',
      method: 'POST',
      signal,
      retry: false,
    });
  },
};
