import { db } from '$lib/server/db';
import { dictionary } from '$lib/server/schema';
import { findMostSimilar } from '$lib/server/heuristicsSpellingCorrectionFilter';

const SPECIAL_MISSPELLINGS: Record<string, { shown: string; replace: string }> = {
	guthib: { shown: 'You spelled it wrong', replace: 'github' }
} as const;

let dictionaryCache: { word: string; weight: number }[] | null = null;
let wordSet: string[] | null = null;
let wordWeights: Map<string, number> | null = null;

async function loadDictionary() {
	dictionaryCache = await db.select().from(dictionary).execute();
	wordSet = dictionaryCache?.map(({ word }) => word);
	wordWeights = new Map<string, number>();
	dictionaryCache?.forEach(({ word, weight }) => {
		wordWeights?.set(word, weight);
	});
}

export type SpellingCorrection = {
	newQuery: string;
	shownMessage: string | null;
};

function characterSimilarity(a: string, b: string) {
	let aChars = new Set(a.toLowerCase().split(''));
	let bChars = new Set(b.toLowerCase().split(''));
	let intersection = new Set([...aChars].filter((x) => bChars.has(x)));
	return intersection.size;
}

export async function tryCorrectSpelling(query: string): Promise<SpellingCorrection | null> {
	await loadDictionary();
	const tokens = query.split(' ');
	let message = null as string | null;
	let anythingChanged = false;
	const correctedTokens = tokens.map((token) => {
		const specialCorrection = SPECIAL_MISSPELLINGS[token.toLowerCase()];
		if (specialCorrection) {
			message = specialCorrection.shown;
			anythingChanged = true;
			return specialCorrection.replace;
		}

		if (wordSet?.includes(token.toLowerCase())) return token;

		const correctionTry = findMostSimilar(wordSet!, token, 5, 1)
			.map((word) => ({
				word,
				weight: (wordWeights?.get(word) || 0) + characterSimilarity(token, word) * 10
			}))
			.sort((a, b) => a.weight - b.weight)
			.map(({ word }) => word)
			.pop();

		if (correctionTry && correctionTry !== token) {
			anythingChanged = true;
			return correctionTry;
		}

		return token;
	});

	if (!anythingChanged) return null;

	return {
		newQuery: correctedTokens.join(' '),
		shownMessage: message
	};
}
