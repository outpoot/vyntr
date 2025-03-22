import { error, json } from '@sveltejs/kit';
import { searchBliptext } from '$lib/server/bliptext';

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

export async function GET({ url }) {
    const query = url.searchParams.get('q');
    if (!query) {
        throw error(400, 'Query parameter "q" is required');
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
    // ========================================================

    return json({
        web: webResults,
        bliptext: bliptextDetail
    });
}