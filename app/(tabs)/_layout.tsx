import { Tabs } from 'expo-router';
import { Activity, ClipboardList, Home, Search, UserRound } from 'lucide-react-native';
import { StatusBar } from 'react-native';
import { useEffect } from 'react';
import { useThemeColor } from 'heroui-native';
import { getActiveExperience, useExperienceStore } from '@/hooks/auth/useExperienceStore';
import { useAuthStore } from '@/hooks/auth/useAuthStore';

export default function TabsLayout() {
  const user = useAuthStore((state) => state.user);
  const selectedRole = useExperienceStore((state) => state.selectedRole);
  const experience = getActiveExperience(user?.roles ?? [], selectedRole);
  const background = useThemeColor('background');
  const foreground = useThemeColor('foreground');
  const muted = useThemeColor('muted');
  const accent = useThemeColor('accent');
  const isProvider = experience === 'FOOD_PROVIDER';
  const isVolunteer = experience === 'VOLUNTEER';

  useEffect(() => {
    StatusBar.setBarStyle('dark-content');
  }, []);

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: accent,
        tabBarInactiveTintColor: muted,
        tabBarStyle: {
          backgroundColor: background,
          borderTopColor: muted,
          shadowColor: foreground,
          shadowOpacity: 0.06,
          shadowRadius: 8,
          elevation: 4,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, size }) => <Home color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="discover"
        options={{
          title: isProvider ? 'Listings' : 'Discover',
          tabBarIcon: ({ color, size }) => <Search color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="reservations"
        options={{
          title: isVolunteer ? 'Tasks' : isProvider ? 'Orders' : 'Reservations',
          tabBarIcon: ({ color, size }) => <ClipboardList color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="activity"
        options={{
          title: isVolunteer ? 'History' : 'Activity',
          tabBarIcon: ({ color, size }) => <Activity color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color, size }) => <UserRound color={color} size={size} />,
        }}
      />
    </Tabs>
  );
}
