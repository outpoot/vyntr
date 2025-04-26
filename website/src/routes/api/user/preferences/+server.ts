import { error, json } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { userPreferences } from '$lib/server/schema';
import { auth } from '$lib/auth';
import { eq } from 'drizzle-orm';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ request }) => {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    const prefs = await db.query.userPreferences.findFirst({
        where: eq(userPreferences.userId, session.user.id)
    });

    return json(prefs || {});
};

export const PATCH: RequestHandler = async ({ request }) => {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        throw error(401, 'Not authenticated');
    }

    const updates = await request.json();
    const allowedFields = [
        'preferredLanguage',
        'safeSearch',
        'autocomplete',
        'instantResults',
        'aiSummarise',
        'anonymousQueries',
        'analyticsEnabled',
        'aiPersonalization',
        'excludeNsfw'
    ];

    // filter out invalid fields
    const validUpdates = Object.fromEntries(
        Object.entries(updates).filter(([key]) => allowedFields.includes(key))
    );

    if (Object.keys(validUpdates).length === 0) {
        throw error(400, 'No valid fields to update');
    }

    const result = await db
        .insert(userPreferences)
        .values({
            userId: session.user.id,
            ...validUpdates,
            updatedAt: new Date()
        })
        .onConflictDoUpdate({
            target: userPreferences.userId,
            set: {
                ...validUpdates,
                updatedAt: new Date()
            }
        })
        .returning();

    return json(result[0]);
};
