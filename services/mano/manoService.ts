import { File } from 'expo-file-system';
import { Platform } from 'react-native';
import { z } from 'zod';
import { apiRequest } from '@/services/api/client';
import {
  MANO_ACTION_KINDS,
  MANO_LANGUAGES,
  type ManoActionResult,
  type ManoMessage,
  type ManoMessageResponse,
  type ManoTranscription,
  type SendManoMessageInput,
} from '@/types/mano';

const referenceSchema = z.object({
  resource_type: z.enum(['food_listing', 'reservation', 'delivery_task', 'community_request']),
  resource_id: z.string().uuid(),
  label: z.string().min(1),
});
const messageSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  created_at: z.string(),
  references: z.array(referenceSchema).default([]),
});
const actionSchema = z.object({
  id: z.string().uuid(),
  kind: z.enum(MANO_ACTION_KINDS),
  label: z.string().min(1),
  summary: z.string().nullable().default(null),
  resource_id: z.string().uuid().nullable().default(null),
  requires_confirmation: z.boolean(),
  expires_at: z.string().nullable().default(null),
});
const messageResponseSchema = z.object({
  conversation_id: z.string().uuid(),
  message: messageSchema,
  suggested_actions: z.array(actionSchema).default([]),
});
const actionResultSchema = z.object({
  action_id: z.string().uuid(),
  status: z.enum(['COMPLETED', 'REJECTED', 'EXPIRED']),
  message: messageSchema,
  resource_type: z
    .enum(['food_listing', 'reservation', 'delivery_task', 'community_request'])
    .nullable()
    .default(null),
  resource_id: z.string().uuid().nullable().default(null),
});
const transcriptionSchema = z.object({
  text: z.string().min(1),
  detected_language: z.enum(MANO_LANGUAGES).nullable().default(null),
});

function mapMessage(value: z.infer<typeof messageSchema>): ManoMessage {
  return {
    id: value.id,
    role: value.role,
    content: value.content,
    createdAt: value.created_at,
    references: value.references.map((reference) => ({
      resourceType: reference.resource_type,
      resourceId: reference.resource_id,
      label: reference.label,
    })),
  };
}

export interface ManoService {
  sendMessage(input: SendManoMessageInput, signal?: AbortSignal): Promise<ManoMessageResponse>;
  confirmAction(
    actionId: string,
    conversationId: string,
    signal?: AbortSignal,
  ): Promise<ManoActionResult>;
  transcribeAudio(
    uri: string,
    mimeType: 'audio/m4a' | 'audio/webm',
    language: (typeof MANO_LANGUAGES)[number],
    signal?: AbortSignal,
  ): Promise<ManoTranscription>;
}

export const manoService: ManoService = {
  async sendMessage(input, signal) {
    const response = await apiRequest({
      path: '/api/v1/ai/mano/messages',
      method: 'POST',
      body: {
        conversation_id: input.conversationId ?? null,
        message: input.message,
        language: input.language,
        experience: input.experience,
        client_message_id: input.clientMessageId,
        voice_input: input.voiceInput,
      },
      signal,
      retry: false,
      timeoutMs: 30_000,
    });
    const value = messageResponseSchema.parse(response.data);
    return {
      conversationId: value.conversation_id,
      message: mapMessage(value.message),
      suggestedActions: value.suggested_actions.map((action) => ({
        id: action.id,
        kind: action.kind,
        label: action.label,
        summary: action.summary,
        resourceId: action.resource_id,
        requiresConfirmation: action.requires_confirmation,
        expiresAt: action.expires_at,
      })),
      requestId: response.requestId,
    };
  },

  async confirmAction(actionId, conversationId, signal) {
    const response = await apiRequest({
      path: `/api/v1/ai/mano/actions/${encodeURIComponent(actionId)}/confirm`,
      method: 'POST',
      body: {
        conversation_id: conversationId,
        confirmation: true,
        idempotency_key: `${conversationId}:${actionId}`,
      },
      signal,
      retry: false,
      timeoutMs: 30_000,
    });
    const value = actionResultSchema.parse(response.data);
    return {
      actionId: value.action_id,
      status: value.status,
      message: mapMessage(value.message),
      resourceType: value.resource_type,
      resourceId: value.resource_id,
    };
  },

  async transcribeAudio(uri, mimeType, language, signal) {
    const formData = new FormData();
    if (Platform.OS === 'web') {
      const blob = await fetch(uri, { signal }).then((response) => response.blob());
      formData.append('audio', blob, 'mano-message.webm');
    } else {
      formData.append('audio', new File(uri), 'mano-message.m4a');
    }
    formData.append('language', language);

    const response = await apiRequest({
      path: '/api/v1/ai/voice/transcriptions',
      method: 'POST',
      body: formData,
      bodyEncoding: 'form-data',
      signal,
      retry: false,
      timeoutMs: 45_000,
    });
    const value = transcriptionSchema.parse(response.data);
    return { text: value.text, detectedLanguage: value.detected_language };
  },
};
