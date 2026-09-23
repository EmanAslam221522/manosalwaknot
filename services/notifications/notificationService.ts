import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { z } from 'zod';
import { apiRequest } from '@/services/api/client';
import type { NotificationItem, NotificationPage } from '@/types/trust';

const notificationSchema = z.object({
  id: z.string().uuid(),
  type: z.string(),
  title: z.string(),
  body: z.string(),
  read_at: z.string().datetime({ offset: true }).nullable(),
  created_at: z.string().datetime({ offset: true }),
  route: z.string().nullable(),
});
const pageSchema = z.object({
  items: z.array(notificationSchema),
  meta: z.object({
    page: z.number().int(),
    page_size: z.number().int(),
    total: z.number().int(),
    total_pages: z.number().int(),
  }),
});
function mapItem(value: z.infer<typeof notificationSchema>): NotificationItem {
  return {
    id: value.id,
    type: value.type,
    title: value.title,
    body: value.body,
    readAt: value.read_at,
    createdAt: value.created_at,
    route: value.route,
  };
}

export const notificationService = {
  async list(page = 1, signal?: AbortSignal): Promise<NotificationPage> {
    const response = await apiRequest({
      path: '/api/v1/notifications',
      query: { page, page_size: 20 },
      signal,
    });
    const value = pageSchema.parse(response.data);
    return {
      items: value.items.map(mapItem),
      meta: {
        page: value.meta.page,
        pageSize: value.meta.page_size,
        totalItems: value.meta.total,
        totalPages: value.meta.total_pages,
      },
    };
  },
  async markRead(id: string): Promise<void> {
    await apiRequest({
      path: `/api/v1/notifications/${encodeURIComponent(id)}/read`,
      method: 'POST',
      retry: false,
    });
  },
  async enablePush(): Promise<'enabled' | 'denied' | 'unavailable'> {
    if (Platform.OS === 'web') return 'unavailable';
    const permission = await Notifications.requestPermissionsAsync();
    if (!permission.granted) return 'denied';
    const token = await Notifications.getExpoPushTokenAsync();
    await apiRequest<{ token: string; platform: string }>({
      path: '/api/v1/notifications/devices',
      method: 'POST',
      body: { token: token.data, platform: Platform.OS },
      retry: false,
    });
    return 'enabled';
  },
};
