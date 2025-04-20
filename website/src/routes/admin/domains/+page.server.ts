import { db } from '$lib/server/db';
import { website, user } from '$lib/server/schema';
import { error } from '@sveltejs/kit';
import { eq, inArray } from 'drizzle-orm';
import { auth } from '$lib/auth';
import { checkPremiumStatus } from '$lib/server/authHelper';

export const load = async ({ request }) => {
    const session = await auth.api.getSession({
        headers: request.headers
    });
    if (!session?.user?.isAdmin) throw error(403, 'Unauthorized');

    const domains = await db.select({
        id: website.id,
        domain: website.domain,
        description: website.description,
        category: website.category,
        tags: website.tags,
        status: website.status,
        createdAt: website.createdAt,
        updatedAt: website.updatedAt,
        userId: website.userId
    })
        .from(website)
        .leftJoin(user, eq(website.userId, user.id))
        .where(eq(website.status, 'pending'));

    const users = await db.select()
        .from(user)
        .where(
            inArray(user.id, domains.map(d => d.userId))
        );

    const premiumStatuses = await Promise.all(
        users.map(async (u) => ({
            userId: u.id,
            isPremium: await checkPremiumStatus(u.email)
        }))
    );

    const userMap = Object.fromEntries(
        users.map(u => [
            u.id,
            {
                ...u,
                isPremium: premiumStatuses.find(p => p.userId === u.id)?.isPremium ?? false
            }
        ])
    );

    return {
        domains: domains.map(domain => ({
            ...domain,
            user: userMap[domain.userId]
        }))
    };
};
