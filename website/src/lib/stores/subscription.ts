import { writable } from 'svelte/store';
import { PUBLIC_PRODUCT_ID_PREMIUM } from '$env/static/public';

function createSubscriptionStore() {
  const { subscribe, set } = writable({ isActive: false });

  return {
    subscribe,
    checkStatus: async () => {
      try {
        const response = await fetch('/api/auth/state')

        if (response.status === 404) {
          set({ isActive: false });
          return;
        }

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const { activeSubscriptions } = await response.json();

        const hasActiveSubscription = activeSubscriptions?.some(
          (sub: { status: string; productId: string; }) =>
            sub.status === 'active' && sub.productId === PUBLIC_PRODUCT_ID_PREMIUM
        );

        set({ isActive: hasActiveSubscription });
      } catch (error) {
        console.error('Error checking subscription status:', error);
        set({ isActive: false });
      }
    }
  };
}

export const subscriptionStore = createSubscriptionStore();