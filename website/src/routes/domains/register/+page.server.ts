import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { eq } from 'drizzle-orm';
import { auth } from '$lib/auth';
import { PUBLIC_PRODUCT_ID_PREMIUM } from '$env/static/public';

export async function load({ request, fetch }) {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        throw redirect(302, '/login');
    }

    const [domains, subscriptionResponse] = await Promise.all([
        db.query.website.findMany({
            where: eq(website.userId, session.user.id)
        }),
        fetch('/api/auth/state')
    ]);

    let isActive = false;
    if (subscriptionResponse.ok) {
        const { activeSubscriptions } = await subscriptionResponse.json();
        isActive = activeSubscriptions?.some(
            (sub: { status: string; productId: string; }) =>
                sub.status === 'active' && sub.productId === PUBLIC_PRODUCT_ID_PREMIUM
        );
    }

    return {
        domainCount: domains.length,
        isPremium: isActive
    };
}
