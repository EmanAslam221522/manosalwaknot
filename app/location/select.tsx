import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import { LocateFixed } from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';
import { Card, Typography, useThemeColor } from 'heroui-native';
import { AppButton } from '@/components/ui/AppButton';
import { AppTextField } from '@/components/ui/AppTextField';
import { Screen } from '@/components/ui/Screen';
import { useAuthStore } from '@/hooks/auth/useAuthStore';
import { getUserFacingErrorMessage } from '@/services/api/ApiError';
import { locationService } from '@/services/location/locationService';
import { profileService } from '@/services/profile/profileService';

export default function LocationSelectScreen() {
  const user = useAuthStore((state) => state.user);
  const setAuthenticatedUser = useAuthStore((state) => state.setAuthenticatedUser);
  const [city, setCity] = useState(user?.city ?? '');
  const [area, setArea] = useState(user?.area ?? '');
  const [permissionMessage, setPermissionMessage] = useState<string | null>(null);
  const accent = useThemeColor('accent');

  const save = useMutation({
    mutationFn: () => profileService.updateDiscoveryArea(city.trim(), area.trim()),
    onSuccess: (updatedUser) => {
      setAuthenticatedUser(updatedUser);
      router.dismissTo('/');
    },
  });
  const locate = useMutation({
    mutationFn: () => locationService.requestSearchLocation(),
    onSuccess: (result) => {
      if (result.status === 'granted')
        setPermissionMessage(
          'Location enabled for nearby search. Your exact position is not displayed publicly.',
        );
      else
        setPermissionMessage('Location was not enabled. You can continue using a city and area.');
    },
  });

  return (
    <Screen title="Location and privacy">
      <Card className="gap-3 p-4">
        <View className="flex-row items-center gap-3">
          <LocateFixed size={24} color={accent} accessibilityElementsHidden />
          <Typography.Heading type="h4" className="flex-1">
            Use current location
          </Typography.Heading>
        </View>
        <Typography.Paragraph color="muted">
          Used only to request nearby results from the server. Public listings show an area and
          approximate distance.
        </Typography.Paragraph>
        <AppButton
          label="Enable location"
          variant="secondary"
          onPress={() => locate.mutate()}
          isLoading={locate.isPending}
        />
        {permissionMessage ? (
          <Typography.Paragraph type="body-sm">{permissionMessage}</Typography.Paragraph>
        ) : null}
      </Card>

      <View className="gap-4">
        <Typography.Heading type="h4">Choose manually</Typography.Heading>
        <AppTextField label="City" value={city} onChangeText={setCity} isRequired />
        <AppTextField label="Area" value={area} onChangeText={setArea} isRequired />
        <AppButton
          label="Save area"
          onPress={() => save.mutate()}
          isLoading={save.isPending}
          isDisabled={!city.trim() || !area.trim()}
        />
        {save.error ? (
          <Typography.Paragraph className="text-danger" accessibilityRole="alert">
            {getUserFacingErrorMessage(save.error)}
          </Typography.Paragraph>
        ) : null}
      </View>
    </Screen>
  );
}
