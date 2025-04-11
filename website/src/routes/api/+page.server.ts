import { error } from '@sveltejs/kit';
import { auth } from '$lib/auth';
import { db } from '$lib/server/db';
import { apiusage } from '$lib/server/schema';
import { eq, and, desc, gte } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
    const session = await auth.api.getSession({ headers: event.request.headers });

    if (!session?.user) {
        return { apiKey: null, usageData: {} };
    }

    const [key] = await auth.api.listApiKeys({ headers: event.request.headers });

    let usageData = {};

    if (key) {
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

        const usage = await db.select()
            .from(apiusage)
            .where(and(
                eq(apiusage.userId, session.user.id),
                gte(apiusage.date, thirtyDaysAgo.toISOString().split('T')[0])
            ))
            .orderBy(desc(apiusage.date))
            .limit(30);

        usageData = Object.fromEntries(
            usage.map(record => [record.date, record.count])
        );
    }

    return {
        apiKey: key,
        usageData
    };
};
