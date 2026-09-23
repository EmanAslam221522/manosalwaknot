import { View } from 'react-native';
import { Typography } from 'heroui-native';
import type { ManoLanguage, ManoMessage } from '@/types/mano';

const RTL_LANGUAGES: ReadonlySet<ManoLanguage> = new Set(['ur']);

export function ManoMessageBubble({
  message,
  language,
}: {
  message: ManoMessage;
  language: ManoLanguage;
}) {
  const isUser = message.role === 'user';
  const isRtl = RTL_LANGUAGES.has(language);

  return (
    <View
      className={`max-w-[88%] gap-2 rounded-2xl px-4 py-3 ${
        isUser ? 'bg-accent self-end' : 'bg-surface border-border self-start border'
      }`}
      accessibilityLabel={`${isUser ? 'You' : 'Mano AI'}: ${message.content}`}
    >
      <Typography.Paragraph
        className={isUser ? 'text-accent-foreground' : 'text-foreground'}
        style={{ writingDirection: isRtl ? 'rtl' : 'auto' }}
      >
        {message.content}
      </Typography.Paragraph>
      {message.references.length > 0 ? (
        <View className="gap-1">
          <Typography.Paragraph
            type="body-xs"
            weight="semibold"
            className={isUser ? 'text-accent-foreground' : 'text-muted'}
          >
            Results used
          </Typography.Paragraph>
          {message.references.map((reference) => (
            <Typography.Paragraph
              key={`${reference.resourceType}:${reference.resourceId}`}
              type="body-xs"
              className={isUser ? 'text-accent-foreground' : 'text-muted'}
            >
              {reference.label}
            </Typography.Paragraph>
          ))}
        </View>
      ) : null}
    </View>
  );
}
