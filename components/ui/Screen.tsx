import type { PropsWithChildren, ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, View } from 'react-native';
import { Typography } from 'heroui-native';

export function Screen({
  children,
  title,
  action,
  scroll = true,
}: PropsWithChildren<{ title?: string; action?: ReactNode; scroll?: boolean }>) {
  const content = (
    <View className="pb-safe-or-6 pt-safe-or-5 mx-auto w-full max-w-3xl flex-1 gap-5 px-5">
      {title ? (
        <View className="flex-row items-center justify-between gap-3">
          <Typography.Heading type="h2" className="flex-1">
            {title}
          </Typography.Heading>
          {action}
        </View>
      ) : null}
      {children}
    </View>
  );

  return (
    <KeyboardAvoidingView
      className="bg-background flex-1"
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      {scroll ? (
        <ScrollView
          className="flex-1"
          contentContainerClassName="flex-grow"
          keyboardShouldPersistTaps="handled"
        >
          {content}
        </ScrollView>
      ) : (
        content
      )}
    </KeyboardAvoidingView>
  );
}
