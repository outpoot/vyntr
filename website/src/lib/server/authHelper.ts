import { error } from '@sveltejs/kit';
import { auth, polarClient } from '$lib/auth';
import type { RequestEvent } from '@sveltejs/kit';
import { PUBLIC_PRODUCT_ID_PREMIUM } from '$env/static/public';

export async function requireAdmin(event: RequestEvent) {
  const session = await auth.api.getSession({
    headers: event.request.headers
  });

  if (!session?.user) {
    throw error(401, 'Not authenticated');
  }

  if (!session.user.isAdmin) {
    throw error(403, 'Not authorized');
  }

  return session.user;
}

async function getCustomerIdbyEmail(email: string): Promise<string | null> {
  try {
    const customers = await polarClient.customers.list({ email });

    return customers.result.items[0]?.id;
  } catch (error) {
    console.error('Error retrieving customer:', error);
    throw error;
  }
}

export async function checkPremiumStatus(email: string): Promise<boolean> {
  const customerId = await getCustomerIdbyEmail(email);
  if (!customerId) {
    return false;
  }

  const subscriptionIterator = await polarClient.subscriptions.list({ customerId });

  for await (const page of subscriptionIterator) {
    for (const subscription of page.result.items) {

      if (
        subscription.status === 'active' &&
        subscription.productId === PUBLIC_PRODUCT_ID_PREMIUM
      ) {
        return true;
      }
    }
  }
  return false;
}