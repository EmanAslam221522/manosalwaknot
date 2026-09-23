import { View } from 'react-native';
import { Typography } from 'heroui-native';

const toneClasses = {
  neutral: 'border-border bg-background-secondary text-foreground',
  success: 'border-success bg-success-soft text-success-soft-foreground',
  warning: 'border-warning bg-warning-soft text-warning-soft-foreground',
  danger: 'border-danger bg-danger-soft text-danger-soft-foreground',
} as const;

export function StatusBadge({
  label,
  tone = 'neutral',
}: {
  label: string;
  tone?: keyof typeof toneClasses;
}) {
  return (
    <View className={`self-start rounded-full border px-2.5 py-1 ${toneClasses[tone]}`}>
      <Typography.Paragraph type="body-xs" weight="semibold" className={toneClasses[tone]}>
        {label.replaceAll('_', ' ')}
      </Typography.Paragraph>
    </View>
  );
}
