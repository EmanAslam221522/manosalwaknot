import type { ExperienceRole } from '@/hooks/auth/useExperienceStore';

export const MANO_LANGUAGES = ['en', 'ur', 'ps', 'hno', 'pa'] as const;
export type ManoLanguage = (typeof MANO_LANGUAGES)[number];

export const MANO_ACTION_KINDS = [
  'OPEN_DISCOVER',
  'OPEN_FOOD_LISTING',
  'OPEN_RESERVATION',
  'OPEN_DELIVERY_TASK',
  'CREATE_FOOD_LISTING_DRAFT',
  'CREATE_COMMUNITY_REQUEST_DRAFT',
] as const;
export type ManoActionKind = (typeof MANO_ACTION_KINDS)[number];

export type ManoMessageRole = 'user' | 'assistant';

export type ManoReference = {
  resourceType: 'food_listing' | 'reservation' | 'delivery_task' | 'community_request';
  resourceId: string;
  label: string;
};

export type ManoMessage = {
  id: string;
  role: ManoMessageRole;
  content: string;
  createdAt: string;
  references: ManoReference[];
};

export type ManoSuggestedAction = {
  id: string;
  kind: ManoActionKind;
  label: string;
  summary: string | null;
  resourceId: string | null;
  requiresConfirmation: boolean;
  expiresAt: string | null;
};

export type SendManoMessageInput = {
  conversationId?: string;
  message: string;
  language: ManoLanguage;
  experience: ExperienceRole;
  clientMessageId: string;
  voiceInput: boolean;
};

export type ManoMessageResponse = {
  conversationId: string;
  message: ManoMessage;
  suggestedActions: ManoSuggestedAction[];
  requestId: string | null;
};

export type ManoActionResult = {
  actionId: string;
  status: 'COMPLETED' | 'REJECTED' | 'EXPIRED';
  message: ManoMessage;
  resourceType: ManoReference['resourceType'] | null;
  resourceId: string | null;
};

export type ManoTranscription = {
  text: string;
  detectedLanguage: ManoLanguage | null;
};

export type RecordedAudio = {
  uri: string;
  mimeType: 'audio/m4a' | 'audio/webm';
};
