import * as Location from 'expo-location';

export type SearchLocation = {
  latitude: number;
  longitude: number;
  accuracyMeters: number | null;
};

export type LocationPermissionResult =
  | { status: 'granted'; location: SearchLocation }
  | { status: 'denied' }
  | { status: 'unavailable' };

export const locationService = {
  async requestSearchLocation(): Promise<LocationPermissionResult> {
    const servicesEnabled = await Location.hasServicesEnabledAsync();
    if (!servicesEnabled) return { status: 'unavailable' };

    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== Location.PermissionStatus.GRANTED) return { status: 'denied' };

    const position = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
    return {
      status: 'granted',
      location: {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracyMeters: position.coords.accuracy,
      },
    };
  },
};
