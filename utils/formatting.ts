export function formatPickupWindow(start: string, end: string): string {
  const startDate = new Date(start);
  const endDate = new Date(end);
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime()))
    return 'Pickup time unavailable';

  const date = new Intl.DateTimeFormat('en-PK', { day: 'numeric', month: 'short' }).format(
    startDate,
  );
  const time = new Intl.DateTimeFormat('en-PK', { hour: 'numeric', minute: '2-digit' });
  return `${date}, ${time.format(startDate)}–${time.format(endDate)}`;
}

export function formatDistance(distanceKm: number | null): string {
  if (distanceKm === null) return 'Distance unavailable';
  return distanceKm < 1
    ? `${Math.round(distanceKm * 1000)} m away`
    : `${distanceKm.toFixed(1)} km away`;
}

export function formatPrice(isFree: boolean, price: number | null): string {
  if (isFree) return 'Free';
  return price === null ? 'Price unavailable' : `Rs ${Math.round(price).toLocaleString('en-PK')}`;
}
