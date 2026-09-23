export const USER_ROLES = [
  'RECIPIENT',
  'FOOD_PROVIDER',
  'ORGANIZATION',
  'VOLUNTEER',
  'ADMIN',
  'SUPER_ADMIN',
] as const;

export type UserRole = (typeof USER_ROLES)[number];

export type UserSummary = {
  id: string;
  displayName: string;
  email: string | null;
  phoneNumber: string | null;
  roles: UserRole[];
  city: string | null;
  area: string | null;
  isVerified: boolean;
};

export type PageMeta = {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
};

export type PaginatedResponse<T> = {
  items: T[];
  meta: PageMeta;
};
