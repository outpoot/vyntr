import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { auth } from '$lib/auth';

export const DELETE: RequestHandler = async ({ request }) => {
  const session = await auth.api.getSession({ headers: request.headers });
  if (!session?.user) {
    throw error(401, 'Not authenticated');
  }

  try {
    await auth.api.deleteUser({ body: {}, headers: request.headers });

    return json(
      { success: true },
    );
  } catch (err) {
    console.error('Error deleting user:', err);
    throw error(500, 'Failed to delete account');
  }
};