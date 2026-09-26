import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import { HandHeart } from 'lucide-react-native';
import { Controller, useForm } from 'react-hook-form';
import { useState } from 'react';
import { View } from 'react-native';
import { Card, Typography, useThemeColor } from 'heroui-native';
import { z } from 'zod';
import { AppButton } from '@/components/ui/AppButton';
import { AppTextField } from '@/components/ui/AppTextField';
import { Screen } from '@/components/ui/Screen';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import {
  authService,
  type RequestOtpInput,
  type VerifyOtpInput,
} from '@/services/auth/authService';
import { useAuthStore } from '@/hooks/auth/useAuthStore';

const passwordSchema = z.object({
  email: z.string().trim().email('Enter a valid email address.'),
  password: z.string().min(8, 'Password must be at least 8 characters.'),
});

const phoneSchema = z.object({
  phoneNumber: z
    .string()
    .trim()
    .regex(/^\+92\d{10}$/, 'Use Pakistan format, for example +923001234567.'),
  otp: z
    .string()
    .regex(/^\d{6}$/, 'Enter the 6-digit code.')
    .optional()
    .or(z.literal('')),
});

type PasswordValues = z.infer<typeof passwordSchema>;
type PhoneValues = z.infer<typeof phoneSchema>;
type SignInMode = 'phone' | 'password';

export default function SignInScreen() {
  const [mode, setMode] = useState<SignInMode>('phone');
  const [otpRequested, setOtpRequested] = useState(false);
  const accent = useThemeColor('accent');
  const completeSession = useAuthStore((state) => state.completeSession);

  const passwordForm = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { email: '', password: '' },
  });
  const phoneForm = useForm<PhoneValues>({
    resolver: zodResolver(phoneSchema),
    defaultValues: { phoneNumber: '+92', otp: '' },
  });

  const signInMutation = useMutation({
    mutationFn: (input: PasswordValues) => authService.signInWithPassword(input),
    onSuccess: async (session) => {
      await completeSession(session);
      router.replace('/');
    },
  });
  const requestOtpMutation = useMutation({
    mutationFn: (input: RequestOtpInput) => authService.requestOtp(input),
    onSuccess: () => setOtpRequested(true),
  });
  const verifyOtpMutation = useMutation({
    mutationFn: (input: VerifyOtpInput) => authService.verifyOtp(input),
    onSuccess: async (session) => {
      await completeSession(session);
      router.replace('/');
    },
  });

  const error = signInMutation.error ?? requestOtpMutation.error ?? verifyOtpMutation.error;
  const busy =
    signInMutation.isPending || requestOtpMutation.isPending || verifyOtpMutation.isPending;

  const submitPhone = phoneForm.handleSubmit((values) => {
    if (!otpRequested) {
      requestOtpMutation.mutate({ phoneNumber: values.phoneNumber });
      return;
    }
    if (!values.otp) {
      phoneForm.setError('otp', { message: 'Enter the 6-digit code.' });
      return;
    }
    verifyOtpMutation.mutate({ phoneNumber: values.phoneNumber, otp: values.otp });
  });

  return (
    <Screen>
      <View className="w-full max-w-md flex-1 justify-center gap-6 self-center py-8">
        <View className="items-center gap-3">
          <View className="bg-accent-soft h-16 w-16 items-center justify-center rounded-3xl">
            <HandHeart color={accent} size={34} />
          </View>
          <Typography.Heading type="h1" align="center">
            ManOSalwaKnot
          </Typography.Heading>
          <Typography.Paragraph color="muted" align="center">
            Rescue food. Support your community.
          </Typography.Paragraph>
        </View>

        <Card className="gap-5 p-5">
          <View className="flex-row gap-2" accessibilityRole="tablist">
            <AppButton
              className="flex-1"
              label="Phone"
              onPress={() => setMode('phone')}
              variant={mode === 'phone' ? 'primary' : 'secondary'}
              accessibilityRole="tab"
              accessibilityState={{ selected: mode === 'phone' }}
            />
            <AppButton
              className="flex-1"
              label="Email"
              onPress={() => setMode('password')}
              variant={mode === 'password' ? 'primary' : 'secondary'}
              accessibilityRole="tab"
              accessibilityState={{ selected: mode === 'password' }}
            />
          </View>

          {mode === 'phone' ? (
            <View className="gap-4">
              <Controller
                control={phoneForm.control}
                name="phoneNumber"
                render={({ field, fieldState }) => (
                  <AppTextField
                    label="Phone number"
                    value={field.value}
                    onChangeText={field.onChange}
                    onBlur={field.onBlur}
                    error={fieldState.error?.message}
                    keyboardType="phone-pad"
                    autoComplete="tel"
                    isRequired
                    editable={!otpRequested}
                  />
                )}
              />
              {otpRequested ? (
                <Controller
                  control={phoneForm.control}
                  name="otp"
                  render={({ field, fieldState }) => (
                    <AppTextField
                      label="Verification code"
                      value={field.value}
                      onChangeText={field.onChange}
                      onBlur={field.onBlur}
                      error={fieldState.error?.message}
                      keyboardType="number-pad"
                      autoComplete="one-time-code"
                      maxLength={6}
                      isRequired
                    />
                  )}
                />
              ) : null}
              <AppButton
                label={otpRequested ? 'Verify and continue' : 'Send verification code'}
                onPress={submitPhone}
                isLoading={busy}
              />
              {otpRequested ? (
                <AppButton
                  label="Use a different number"
                  variant="ghost"
                  onPress={() => {
                    setOtpRequested(false);
                    phoneForm.setValue('otp', '');
                  }}
                  isDisabled={busy}
                />
              ) : null}
            </View>
          ) : (
            <View className="gap-4">
              <Controller
                control={passwordForm.control}
                name="email"
                render={({ field, fieldState }) => (
                  <AppTextField
                    label="Email"
                    value={field.value}
                    onChangeText={field.onChange}
                    onBlur={field.onBlur}
                    error={fieldState.error?.message}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    autoComplete="email"
                    isRequired
                  />
                )}
              />
              <Controller
                control={passwordForm.control}
                name="password"
                render={({ field, fieldState }) => (
                  <AppTextField
                    label="Password"
                    value={field.value}
                    onChangeText={field.onChange}
                    onBlur={field.onBlur}
                    error={fieldState.error?.message}
                    secureTextEntry
                    autoComplete="current-password"
                    isRequired
                  />
                )}
              />
              <AppButton
                label="Sign in"
                onPress={passwordForm.handleSubmit((values) => signInMutation.mutate(values))}
                isLoading={busy}
              />
            </View>
          )}

          {error ? (
            <Typography.Paragraph className="text-danger" accessibilityRole="alert">
              {getUserFacingErrorMessage(error)}
            </Typography.Paragraph>
          ) : null}
        </Card>

        <Typography.Paragraph type="body-xs" color="muted" align="center">
          Your session is protected on this device. Authorization is always verified by the server.
        </Typography.Paragraph>
      </View>
    </Screen>
  );
}
