import { db } from '$lib/server/db';
import { website } from '$lib/server/schema';
import { eq } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

function calculateScore(site: any) {
    const age = (Date.now() - new Date(site.createdAt).getTime()) / (1000 * 60 * 60 * 24); // days
    const votes = site.upvotes - site.downvotes;
    const votesWeight = 1.5;
    const visitsWeight = 1.0;
    const featuredBonus = site.isFeatured ? 2.0 : 1.0;
    const decay = Math.pow(age + 2, -0.5); // Decay older posts slowly

    return (
        ((votes * votesWeight) + (site.monthlyVisits * visitsWeight)) * 
        featuredBonus * 
        decay
    );
}

export const load: PageServerLoad = async () => {
    const sites = await db.query.website.findMany({
        where: eq(website.status, 'public'),
        with: {
            user: true
        }
    });

    // Sort by engagement score
    const sortedSites = sites.sort((a, b) => calculateScore(b) - calculateScore(a));

    return { sites: sortedSites };
};