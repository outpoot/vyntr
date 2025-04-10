import { BANGS } from '$lib/bangs';

export function handleBangQuery(query: string): string | null {
    const words = query.split(' ');
    for (let i = 0; i < words.length; i++) {
        const word = words[i];
        if (word.startsWith('!')) {
            const bangTerm = word.slice(1).toLowerCase();
            const searchTerm = [...words.slice(0, i), ...words.slice(i + 1)].join(' ');

            const matchedBang = BANGS.find(b => b.t === bangTerm);
            if (matchedBang) {
                return matchedBang.u.replace('{{{s}}}', encodeURIComponent(searchTerm));
            }
        }
    }
    return null;
}
