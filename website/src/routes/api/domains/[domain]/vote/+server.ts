import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { website, websiteVote } from '$lib/server/schema';
import { and, eq } from 'drizzle-orm';
import { auth } from '$lib/auth';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, params }) => {
    const session = await auth.api.getSession({ headers: request.headers });
    if (!session?.user) throw error(401, 'Not authenticated');

    const { type } = await request.json();
    if (!['up', 'down', 'none'].includes(type)) {
        throw error(400, 'Invalid vote type');
    }

    const domain = `https://${params.domain}`;

    const result = await db.transaction(async (tx) => {
        // get current site and user's vote
        const site = await tx.query.website.findFirst({
            where: and(
                eq(website.domain, domain),
                eq(website.status, 'public')
            )
        });

        if (!site) throw error(404, 'Website not found or not public');

        const currentVote = await tx.query.websiteVote.findFirst({
            where: and(
                eq(websiteVote.website, domain),
                eq(websiteVote.userId, session.user.id)
            )
        });

        // calculate vote changes
        let upvotesDelta = 0;
        let downvotesDelta = 0;

        if (currentVote) {
            // remove existing vote
            if (currentVote.type === 'up') upvotesDelta--;
            if (currentVote.type === 'down') downvotesDelta--;
            
            await tx.delete(websiteVote)
                .where(and(
                    eq(websiteVote.website, domain),
                    eq(websiteVote.userId, session.user.id)
                ));
        }

        // add new vote if not 'none'
        if (type !== 'none') {
            if (type === 'up') upvotesDelta++;
            if (type === 'down') downvotesDelta++;
            
            await tx.insert(websiteVote)
                .values({
                    website: domain,
                    userId: session.user.id,
                    type: type as 'up' | 'down'
                });
        }

        // update vote counts
        const updated = await tx.update(website)
            .set({
                upvotes: site.upvotes + upvotesDelta,
                downvotes: site.downvotes + downvotesDelta,
            })
            .where(eq(website.domain, domain))
            .returning();

        return updated[0];
    });

    return new Response(JSON.stringify(result));
};

export const GET: RequestHandler = async ({ params, request }) => {
    const session = await auth.api.getSession({
        headers: request.headers
    });

    if (!session?.user) {
        return new Response(JSON.stringify({ vote: null }));
    }

    const vote = await db.query.websiteVote.findFirst({
        where: and(
            eq(websiteVote.website, `https://${params.domain}`),
            eq(websiteVote.userId, session.user.id)
        )
    });

    return new Response(JSON.stringify({ vote: vote?.type || null }));
};
