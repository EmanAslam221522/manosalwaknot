import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { View } from 'react-native';
import { Card, Typography } from 'heroui-native';
import { AppButton } from '@/components/ui/AppButton';
import { AppTextField } from '@/components/ui/AppTextField';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { verificationService } from '@/services/trust/verificationService';
import type { VerificationType } from '@/types/trust';

export default function VerificationScreen() {
  const [type, setType] = useState<VerificationType>('PROVIDER');
  const [statement, setStatement] = useState('');
  const query = useQuery({
    queryKey: ['verification', 'me'],
    queryFn: ({ signal }) => verificationService.getMine(signal),
  });
  const submit = useMutation({
    mutationFn: () => verificationService.submit(type, statement.trim()),
    onSuccess: () => void query.refetch(),
  });
  return (
    <Screen title="Verification">
      {query.isLoading ? <StateView title="Loading verification…" kind="loading" /> : null}
      {query.error ? (
        <StateView
          title="Could not load verification"
          message={getUserFacingErrorMessage(query.error)}
          actionLabel="Try again"
          onAction={() => void query.refetch()}
          kind="error"
        />
      ) : null}
      {query.data?.map((item) => (
        <Card key={item.type} className="gap-2 p-4">
          <View className="flex-row items-center justify-between">
            <Typography.Heading type="h4">{item.type.toLowerCase()}</Typography.Heading>
            <StatusBadge
              label={item.status.replaceAll('_', ' ')}
              tone={
                item.status === 'APPROVED'
                  ? 'success'
                  : item.status === 'REJECTED'
                    ? 'danger'
                    : 'warning'
              }
            />
          </View>
          {item.reviewerMessage ? (
            <Typography.Paragraph color="muted">{item.reviewerMessage}</Typography.Paragraph>
          ) : null}
        </Card>
      ))}
      <View className="gap-3">
        <Typography.Heading type="h4">Request verification</Typography.Heading>
        <View className="flex-row flex-wrap gap-2">
          {(['PROVIDER', 'ORGANIZATION', 'VOLUNTEER'] as const).map((value) => (
            <AppButton
              key={value}
              label={value.toLowerCase()}
              size="sm"
              variant={type === value ? 'primary' : 'secondary'}
              onPress={() => setType(value)}
            />
          ))}
        </View>
        <AppTextField
          label="Tell us about your work"
          value={statement}
          onChangeText={setStatement}
          multiline
          numberOfLines={5}
          maxLength={1000}
          isRequired
        />
        <AppButton
          label="Submit request"
          onPress={() => submit.mutate()}
          isLoading={submit.isPending}
          isDisabled={statement.trim().length < 20}
        />
        {submit.error ? (
          <Typography.Paragraph className="text-danger" accessibilityRole="alert">
            {getUserFacingErrorMessage(submit.error)}
          </Typography.Paragraph>
        ) : null}
      </View>
    </Screen>
  );
}
