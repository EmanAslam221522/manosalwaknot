import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Send } from 'lucide-react-native';
import { useMemo, useRef, useState } from 'react';
import { FlatList, ScrollView, View } from 'react-native';
import { Card, Typography, useThemeColor } from 'heroui-native';
import { ManoActionCard } from '@/components/mano/ManoActionCard';
import { ManoMessageBubble } from '@/components/mano/ManoMessageBubble';
import { VoiceInputButton } from '@/components/mano/VoiceInputButton';
import { AppButton } from '@/components/ui/AppButton';
import { AppTextField } from '@/components/ui/AppTextField';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { useAuthStore } from '@/hooks/auth/useAuthStore';
import { getActiveExperience, useExperienceStore } from '@/hooks/auth/useExperienceStore';
import { goBackOrReplace } from '@/lib/navigation';
import { ApiError, getUserFacingErrorMessage } from '@/services/api/ApiError';
import { manoService } from '@/services/mano/manoService';
import type {
  ManoActionResult,
  ManoLanguage,
  ManoMessage,
  ManoSuggestedAction,
  RecordedAudio,
} from '@/types/mano';

const LANGUAGE_OPTIONS: ReadonlyArray<{ code: ManoLanguage; label: string }> = [
  { code: 'en', label: 'English' },
  { code: 'ur', label: 'Urdu' },
  { code: 'ps', label: 'Pashto' },
  { code: 'hno', label: 'Hindko' },
  { code: 'pa', label: 'Punjabi' },
];
const STARTER_PROMPTS = [
  'Find free food near me',
  'Show my reservation status',
  'Find community requests in Haripur',
] as const;
let localMessageSequence = 0;

function createLocalId(prefix: string): string {
  localMessageSequence += 1;
  return `${prefix}-${Date.now()}-${localMessageSequence}`;
}

function navigateForAction(action: ManoSuggestedAction) {
  if (action.kind === 'OPEN_DISCOVER') {
    router.push('/discover');
    return;
  }
  if (!action.resourceId) return;
  if (action.kind === 'OPEN_FOOD_LISTING') {
    router.push({ pathname: '/food/[id]', params: { id: action.resourceId } });
  } else if (action.kind === 'OPEN_RESERVATION') {
    router.push({ pathname: '/reservations/[id]', params: { id: action.resourceId } });
  } else if (action.kind === 'OPEN_DELIVERY_TASK') {
    router.push({ pathname: '/deliveries/[id]', params: { id: action.resourceId } });
  }
}

export default function ManoScreen() {
  const user = useAuthStore((state) => state.user);
  const selectedRole = useExperienceStore((state) => state.selectedRole);
  const experience = getActiveExperience(user?.roles ?? [], selectedRole);
  const accent = useThemeColor('accent');
  const listRef = useRef<FlatList<ManoMessage>>(null);
  const [language, setLanguage] = useState<ManoLanguage>('en');
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string>();
  const [messages, setMessages] = useState<ManoMessage[]>([]);
  const [actions, setActions] = useState<ManoSuggestedAction[]>([]);
  const [completedActionIds, setCompletedActionIds] = useState<ReadonlySet<string>>(new Set());
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const sendMutation = useMutation({
    mutationFn: ({ message, voiceInput }: { message: string; voiceInput: boolean }) =>
      manoService.sendMessage({
        conversationId,
        message,
        language,
        experience,
        clientMessageId: createLocalId('client'),
        voiceInput,
      }),
    onSuccess: (response) => {
      setConversationId(response.conversationId);
      setMessages((current) => [...current, response.message]);
      setActions(response.suggestedActions);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: (actionId: string) => {
      if (!conversationId) throw new Error('A conversation is required before confirmation.');
      return manoService.confirmAction(actionId, conversationId);
    },
    onSuccess: (result: ManoActionResult) => {
      setCompletedActionIds((current) => new Set(current).add(result.actionId));
      setMessages((current) => [...current, result.message]);
    },
  });

  const transcriptionMutation = useMutation({
    mutationFn: (audio: RecordedAudio) =>
      manoService.transcribeAudio(audio.uri, audio.mimeType, language),
    onSuccess: (transcription) => {
      if (transcription.detectedLanguage) setLanguage(transcription.detectedLanguage);
      submitMessage(transcription.text, true);
    },
    onError: (error) => setVoiceError(getUserFacingErrorMessage(error)),
  });

  const isBusy = sendMutation.isPending || transcriptionMutation.isPending;
  const activeError = sendMutation.error ?? transcriptionMutation.error;
  const isAiUnavailable =
    activeError instanceof ApiError &&
    (activeError.code === 'MANO_UNAVAILABLE' || activeError.kind === 'SERVER');

  function submitMessage(rawMessage: string, voiceInput = false) {
    const message = rawMessage.trim();
    if (!message || isBusy) return;
    setVoiceError(null);
    sendMutation.reset();
    setMessages((current) => [
      ...current,
      {
        id: createLocalId('user'),
        role: 'user',
        content: message,
        createdAt: new Date().toISOString(),
        references: [],
      },
    ]);
    setInput('');
    sendMutation.mutate({ message, voiceInput });
  }

  const footer = useMemo(
    () => (
      <View className="gap-3 pt-3">
        {sendMutation.isPending ? (
          <StateView kind="loading" title="Mano is checking current platform data…" />
        ) : null}
        {actions.map((action) => (
          <ManoActionCard
            key={action.id}
            action={action}
            isCompleted={completedActionIds.has(action.id)}
            isLoading={confirmMutation.isPending && confirmMutation.variables === action.id}
            onPress={() =>
              action.requiresConfirmation
                ? confirmMutation.mutate(action.id)
                : navigateForAction(action)
            }
          />
        ))}
      </View>
    ),
    [actions, completedActionIds, confirmMutation, sendMutation.isPending],
  );

  return (
    <Screen
      title="Mano AI"
      scroll={false}
      action={
        <AppButton label="Back" size="sm" variant="ghost" onPress={() => goBackOrReplace('/')} />
      }
    >
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerClassName="gap-2"
      >
        {LANGUAGE_OPTIONS.map((option) => {
          const isSelected = language === option.code;
          return (
            <AppButton
              key={option.code}
              label={`${isSelected ? 'Selected: ' : ''}${option.label}`}
              size="sm"
              variant={isSelected ? 'primary' : 'secondary'}
              accessibilityState={{ selected: isSelected }}
              onPress={() => setLanguage(option.code)}
            />
          );
        })}
      </ScrollView>

      <FlatList
        ref={listRef}
        className="flex-1"
        contentContainerClassName="flex-grow gap-3 py-2"
        data={messages}
        keyExtractor={(message) => message.id}
        renderItem={({ item }) => <ManoMessageBubble message={item} language={language} />}
        ListEmptyComponent={
          <View className="flex-1 justify-center gap-3">
            <Typography.Heading type="h3" align="center">
              What can I help with?
            </Typography.Heading>
            {STARTER_PROMPTS.map((prompt) => (
              <AppButton
                key={prompt}
                label={prompt}
                variant="secondary"
                onPress={() => submitMessage(prompt)}
              />
            ))}
          </View>
        }
        ListFooterComponent={footer}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        keyboardShouldPersistTaps="handled"
        accessibilityLabel="Conversation with Mano AI"
      />

      {activeError || voiceError || confirmMutation.error ? (
        <Card className="border-danger gap-3 border p-4" accessibilityRole="alert">
          <Typography.Paragraph weight="semibold">
            {isAiUnavailable
              ? 'AI assistant is temporarily unavailable.'
              : 'Mano could not complete that request.'}
          </Typography.Paragraph>
          <Typography.Paragraph color="muted">
            {voiceError ?? getUserFacingErrorMessage(confirmMutation.error ?? activeError)}
          </Typography.Paragraph>
          {isAiUnavailable ? (
            <AppButton
              label="Use food search"
              variant="secondary"
              onPress={() => router.push('/discover')}
            />
          ) : null}
        </Card>
      ) : null}

      <View className="border-border gap-2 border-t pt-3">
        <AppTextField
          label="Message"
          value={input}
          onChangeText={setInput}
          placeholder="Ask Mano"
          multiline
          numberOfLines={2}
          maxLength={1000}
          isDisabled={isBusy}
          returnKeyType="send"
          onSubmitEditing={() => submitMessage(input)}
        />
        <View className="flex-row justify-between gap-2">
          <VoiceInputButton
            isDisabled={isBusy}
            onRecorded={(audio) => transcriptionMutation.mutate(audio)}
            onError={setVoiceError}
          />
          <AppButton
            label="Send"
            isLoading={sendMutation.isPending || transcriptionMutation.isPending}
            isDisabled={!input.trim()}
            onPress={() => submitMessage(input)}
          >
            <Send size={17} color={accent} />
          </AppButton>
        </View>
      </View>
    </Screen>
  );
}
