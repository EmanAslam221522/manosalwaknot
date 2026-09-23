import { useMutation } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Select, Typography } from 'heroui-native';
import { AppButton } from '@/components/ui/AppButton';
import { AppTextField } from '@/components/ui/AppTextField';
import { Screen } from '@/components/ui/Screen';
import { StateView } from '@/components/ui/StateView';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { reportService } from '@/services/trust/reportService';
import { REPORT_REASONS, type ReportReason } from '@/types/trust';

const labels: Record<ReportReason, string> = {
  UNSAFE_FOOD: 'Unsafe food',
  SPOILED_FOOD: 'Spoiled food',
  FAKE_LISTING: 'Fake listing',
  INCORRECT_QUANTITY: 'Incorrect quantity',
  NO_SHOW: 'No-show',
  MISLEADING_INFORMATION: 'Misleading information',
  HARASSMENT_ABUSE: 'Harassment or abuse',
  OTHER: 'Other issue',
};

function isReportReason(value: string): value is ReportReason {
  return REPORT_REASONS.some((reason) => reason === value);
}

export default function NewReportScreen() {
  const params = useLocalSearchParams<{ foodListingId?: string; reservationId?: string }>();
  const [reason, setReason] = useState<ReportReason | null>(null);
  const [details, setDetails] = useState('');
  const mutation = useMutation({
    mutationFn: () =>
      reportService.create({
        foodListingId: params.foodListingId,
        reservationId: params.reservationId,
        reason: reason!,
        details: details.trim(),
      }),
  });
  if (mutation.isSuccess)
    return (
      <Screen>
        <StateView
          title="Report submitted"
          message="The trust team will review it. Administrative actions are recorded by the server."
          actionLabel="Done"
          onAction={() => router.back()}
        />
      </Screen>
    );

  return (
    <Screen title="Report an issue">
      <Typography.Paragraph type="body-sm">Issue</Typography.Paragraph>
      <Select
        value={reason ? { value: reason, label: labels[reason] } : undefined}
        onValueChange={(option) => {
          if (option && isReportReason(option.value)) setReason(option.value);
        }}
      >
        <Select.Trigger>
          <Select.Value placeholder="Choose an issue" />
          <Select.TriggerIndicator />
        </Select.Trigger>
        <Select.Portal>
          <Select.Overlay />
          <Select.Content presentation="popover">
            {REPORT_REASONS.map((item) => (
              <Select.Item key={item} value={item} label={labels[item]} />
            ))}
          </Select.Content>
        </Select.Portal>
      </Select>
      <AppTextField
        label="What happened?"
        value={details}
        onChangeText={setDetails}
        multiline
        numberOfLines={5}
        maxLength={1000}
        isRequired
      />
      <Typography.Paragraph type="body-xs" color="muted">
        Do not include passwords, codes, or unnecessary private information.
      </Typography.Paragraph>
      <AppButton
        label="Submit report"
        onPress={() => mutation.mutate()}
        isLoading={mutation.isPending}
        isDisabled={!reason || details.trim().length < 10}
      />
      {mutation.error ? (
        <Typography.Paragraph className="text-danger" accessibilityRole="alert">
          {getUserFacingErrorMessage(mutation.error)}
        </Typography.Paragraph>
      ) : null}
    </Screen>
  );
}
