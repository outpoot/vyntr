import { error, json } from '@sveltejs/kit';
import { searchBliptext } from '$lib/server/bliptext';
import { parseDateQuery } from '$lib/utils/date';
import { formatTimeDifference, TIME_UNITS } from '$lib/utils/time';
import { searchWordnet } from '$lib/server/wordnet';
import { parseCurrencyQuery, performConversion } from '$lib/utils/currency';
import { parseUnitQuery } from '$lib/utils/unitParser';
import { convertUnit, UNITS } from '$lib/utils/units';
import { auth } from '$lib/auth';
import { db } from '$lib/server/db';
import { apiusage, apikey } from '$lib/server/schema';
import { eq, and } from 'drizzle-orm';

const MOCK_RESULTS = [
    {
        favicon: 'https://www.github.com/favicon.ico',
        title: "GitHub: Let's build from here",
        url: 'https://github.com',
        pageTitle: 'GitHub: Where the world builds software',
        date: new Date('2024-01-15'),
        preview:
            'GitHub is where over 100 million developers shape the future of software, together. Contribute to the open source community...'
    },
    {
        favicon: 'https://www.stackoverflow.com/favicon.ico',
        title: 'Stack Overflow - Where Developers Learn & Share',
        url: 'https://stackoverflow.com',
        pageTitle: 'Stack Overflow - Developer Q&A Platform',
        date: new Date('2024-01-14'),
        preview:
            'Stack Overflow is the largest, most trusted online community for developers to learn, share their knowledge, and build their careers.'
    },
    {
        favicon: 'https://www.reddit.com/favicon.ico',
        title: 'r/programming - Reddit',
        url: 'https://reddit.com/r/programming',
        pageTitle: 'Programming Discussions and News',
        date: new Date('2024-01-13'),
        preview:
            'r/programming is a community of developers sharing programming news, articles, and discussions about software development.'
    },
    {
        favicon: 'https://www.dev.to/favicon.ico',
        title: 'DEV Community',
        url: 'https://dev.to',
        pageTitle: 'DEV Community - Programming Tutorials and Stories',
        date: new Date('2024-01-12'),
        preview:
            'DEV is a community of software developers getting together to help one another out. The software industry relies on collaboration and...'
    },
    {
        favicon: 'https://medium.com/favicon.ico',
        title: 'Medium - Technology',
        url: 'https://medium.com/topic/technology',
        pageTitle: 'Technology Stories and Publications on Medium',
        date: new Date('2024-01-11'),
        preview:
            'Read stories about Technology on Medium. Discover expert insights, analyses, and tutorials about software development and tech trends.'
    },
    {
        favicon: 'https://www.mozilla.org/favicon.ico',
        title: 'MDN Web Docs',
        url: 'https://developer.mozilla.org',
        pageTitle: 'MDN Web Docs - Resources for Developers, by Developers',
        date: new Date('2024-01-10'),
        preview:
            'Resources for developers, by developers. Documentation for web technologies including HTML, CSS, JavaScript, and Web APIs.'
    },
    {
        favicon: 'https://www.youtube.com/favicon.ico',
        title: 'Fireship - JavaScript Tutorials',
        url: 'https://www.youtube.com/c/Fireship',
        pageTitle: 'Advanced JavaScript Concepts Explained',
        date: new Date('2024-01-09'),
        preview:
            'Learn modern JavaScript concepts with practical examples and coding tutorials. Perfect for both beginners and advanced developers.'
    },
    {
        favicon: 'https://www.svelte.dev/favicon.png',
        title: 'Svelte • Cybernetically enhanced web apps',
        url: 'https://svelte.dev',
        pageTitle: 'Svelte Documentation and Tutorials',
        date: new Date('2024-01-08'),
        preview:
            'Svelte is a radical new approach to building user interfaces. Learn how to build fast web applications with less code.'
    },
    {
        favicon: 'https://www.vercel.com/favicon.ico',
        title: 'Vercel: Develop. Preview. Ship.',
        url: 'https://vercel.com',
        pageTitle: 'Vercel: Deploy web projects with ease',
        date: new Date('2024-01-07'),
        preview:
            'Vercel combines the best developer experience with an obsessive focus on end-user performance.'
    },
    {
        favicon: 'https://www.netlify.com/favicon.ico',
        title: 'Netlify: Develop & deploy the best web experiences',
        url: 'https://www.netlify.com',
        pageTitle: 'Netlify: The fastest way to build the fastest sites',
        date: new Date('2024-01-06'),
        preview:
            'Netlify unites an entire ecosystem of modern tools and services into a single, simple workflow for building high performance sites.'
    },
    {
        favicon: 'https://www.digitalocean.com/favicon.ico',
        title: 'DigitalOcean – The Developer Cloud',
        url: 'https://www.digitalocean.com',
        pageTitle: 'Simple Cloud Hosting for Developers',
        date: new Date('2024-01-05'),
        preview:
            'DigitalOcean provides developers with cloud services that help to deploy and scale applications that run simultaneously on multiple computers.'
    }
];

export async function GET({ url, request }) {
    const authHeader = request.headers.get('Authorization');
    let userId = null;

    if (authHeader?.startsWith('Bearer ')) {
        const apiKeyStr = authHeader.substring(7);
        const { valid, error: verifyError, key } = await auth.api.verifyApiKey({ 
            body: { key: apiKeyStr } 
        });

        if (verifyError || !valid || !key) {
            throw error(401, 'Invalid API key');
        }

        // Get the user ID from the API key record
        const keyRecord = await db.select()
            .from(apikey)
            .where(eq(apikey.id, key.id))
            .limit(1);

        if (!keyRecord.length) {
            throw error(401, 'Invalid API key');
        }

        userId = keyRecord[0].userId;

        // Track API usage
        const today = new Date().toISOString().split('T')[0];
        try {
            const existingRecord = await db.select()
                .from(apiusage)
                .where(and(
                    eq(apiusage.date, today),
                    eq(apiusage.userId, userId)
                ))
                .limit(1);

            if (existingRecord.length > 0) {
                await db.update(apiusage)
                    .set({
                        count: existingRecord[0].count + 1,
                        updatedAt: new Date()
                    })
                    .where(eq(apiusage.id, existingRecord[0].id));
            } else {
                await db.insert(apiusage).values({
                    userId,
                    date: today,
                    count: 1,
                    createdAt: new Date(),
                    updatedAt: new Date()
                });
            }
        } catch (err) {
            console.error('Failed to track API usage:', err);
        }
    }

    const query = url.searchParams.get('q');
    if (!query) {
        throw error(400, 'Query parameter "q" is required');
    }

    // ==================== DATE ====================
    const dateResult = parseDateQuery(query);
    const dateDetail = dateResult ? {
        type: 'date',
        value: Number((dateResult.milliseconds * TIME_UNITS[dateResult.unit].multiplier).toFixed(TIME_UNITS[dateResult.unit].decimals)),
        description: dateResult.description,
        date: dateResult.date.toISOString(),
        unit: dateResult.unit,
        displayText: formatTimeDifference(dateResult.milliseconds, dateResult.unit)
    } : null;

    // ==================== UNIT CONVERSION ====================
    let unitConversionDetail = null;
    const unitMatch = parseUnitQuery(query);
    if (unitMatch) {
        const result = convertUnit(unitMatch.value, unitMatch.fromUnit, unitMatch.toUnit, unitMatch.category);
        if (result !== null) {
            unitConversionDetail = {
                type: 'unitConversion',
                ...unitMatch,
                result
            };
        }
    }

    // ==================== WEB SEARCH ====================
    // to-be replaced with actual search results
    const webResults = MOCK_RESULTS.map(result => ({
        ...result,
        date: result.date.toISOString()
    }));

    // ==================== BLIPTEXT SEARCH ====================
    const bliptextResults = await searchBliptext(query);
    const bliptextDetail = bliptextResults.bestMatch ? { type: 'bliptext', article: bliptextResults.bestMatch } : null;

    // ==================== WORD LOOKUP ====================
    let wordDetail = null;
    try {
        const matches = await searchWordnet(query);
        if (matches.length > 0) {
            const bestMatch = matches[0];
            wordDetail = bestMatch.entry;
        }
    } catch (err) {
        console.error('Word lookup error:', err);
    }

    // ==================== CURRENCY CONVERSION ====================
    let currencyDetail = null;
    const currencyMatch = await parseCurrencyQuery(query);
    if (currencyMatch) {
        currencyDetail = await performConversion(currencyMatch);
    }

    return json({
        web: webResults,
        bliptext: bliptextDetail,
        date: dateDetail,
        word: wordDetail,
        currency: currencyDetail,
        unitConversion: unitConversionDetail
    });
}