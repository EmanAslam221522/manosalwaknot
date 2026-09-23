import type { PaginatedResponse } from '@/types/domain';

export const REPORT_REASONS = [
  'UNSAFE_FOOD',
  'SPOILED_FOOD',
  'FAKE_LISTING',
  'INCORRECT_QUANTITY',
  'NO_SHOW',
  'MISLEADING_INFORMATION',
  'HARASSMENT_ABUSE',
  'OTHER',
] as const;
export type ReportReason = (typeof REPORT_REASONS)[number];
export type ReportStatus = 'OPEN' | 'UNDER_REVIEW' | 'RESOLVED' | 'DISMISSED';

export interface ReportRecord {
  id: string;
  reason: ReportReason;
  status: ReportStatus;
  createdAt: string;
  updatedAt: string;
}

export type VerificationType = 'PROVIDER' | 'ORGANIZATION' | 'VOLUNTEER';
export type VerificationStatus =
  | 'NOT_SUBMITTED'
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'NEEDS_INFORMATION';

export interface VerificationRecord {
  id: string | null;
  type: VerificationType;
  status: VerificationStatus;
  submittedAt: string | null;
  reviewerMessage: string | null;
}

export interface HandoverToken {
  token: string;
  expiresAt: string;
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  readAt: string | null;
  createdAt: string;
  route: string | null;
}

export type NotificationPage = PaginatedResponse<NotificationItem>;
