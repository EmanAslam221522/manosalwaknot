import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import { View } from 'react-native';
import { Card, Typography } from 'heroui-native';
import { AppButton } from '@/components/ui/AppButton';
import { Screen } from '@/components/ui/Screen';
import { useAuthStore } from '@/hooks/auth/useAuthStore';
import {
  getActiveExperience,
  getAvailableExperiences,
  useExperienceStore,
  type ExperienceRole,
} from '@/hooks/auth/useExperienceStore';
import { authService } from '@/services/auth/authService';
import { secureSessionStorage } from '@/services/storage/secureSessionStorage';

const roleLabels: Record<ExperienceRole, string> = {
  RECIPIENT: 'Receive food',
  FOOD_PROVIDER: 'Provide food',
  VOLUNTEER: 'Volunteer',
};

export default function ProfileScreen() {
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const selectedRole = useExperienceStore((state) => state.selectedRole);
  const selectRole = useExperienceStore((state) => state.selectRole);
  const available = getAvailableExperiences(user?.roles ?? []);
  const active = getActiveExperience(user?.roles ?? [], selectedRole);
  const signOut = useMutation({
    mutationFn: async () => {
      try {
        await authService.signOut();
      } finally {
        await secureSessionStorage.clear();
      }
    },
    onSettled: async () => {
      await clearSession();
      router.replace('/auth/sign-in');
    },
  });

  return (
    <Screen title="Profile">
      <Card className="gap-2 p-5">
        <Typography.Heading type="h3">{user?.displayName}</Typography.Heading>
        <Typography.Paragraph color="muted">
          {user?.email ?? user?.phoneNumber}
        </Typography.Paragraph>
        <Typography.Paragraph>
          {user?.area ?? user?.city ?? 'Location not selected'}
        </Typography.Paragraph>
      </Card>

      {available.length > 1 ? (
        <View className="gap-3">
          <Typography.Heading type="h4">Use ManOSalwaKnot as</Typography.Heading>
          <View className="gap-2">
            {available.map((role) => (
              <AppButton
                key={role}
                label={roleLabels[role]}
                variant={active === role ? 'primary' : 'secondary'}
                onPress={() => selectRole(role)}
              />
            ))}
          </View>
        </View>
      ) : null}

      <AppButton
        label="Verification"
        variant="secondary"
        onPress={() => router.push('/profile/verification')}
      />
      <AppButton
        label="Notifications"
        variant="secondary"
        onPress={() => router.push('/notifications')}
      />
      {active === 'FOOD_PROVIDER' ? (
        <AppButton
          label="Scan pickup QR"
          variant="secondary"
          onPress={() => router.push('/handover/scan')}
        />
      ) : null}
      <AppButton
        label="Location and privacy"
        variant="secondary"
        onPress={() => router.push('/location/select')}
      />
      <AppButton
        label="Sign out"
        variant="ghost"
        onPress={() => signOut.mutate()}
        isLoading={signOut.isPending}
      />
    </Screen>
  );
}
