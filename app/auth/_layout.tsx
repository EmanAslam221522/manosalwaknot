import { Stack } from 'expo-router';
import { useThemeColor } from 'heroui-native';

export default function AuthLayout() {
  const background = useThemeColor('background');
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: background } }} />
  );
}
