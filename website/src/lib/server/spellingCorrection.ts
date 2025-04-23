import { db } from '$lib/server/db';
import { spellingCorrections } from '$lib/server/schema';

const SPECIAL_MISSPELLINGS: Record<string, { shown: string, replace: string }> = {
	"guthib": { shown: "You spelled it wrong", replace: "github" }
} as const;

let correctionsCache: { source: string, target: string }[] | null = null;

async function loadSpellingCorrections() {
	if (correctionsCache !== null) return;
	correctionsCache = await db.select()
		.from(spellingCorrections)
		.execute();
}

export type SpellingCorrection = {
	newQuery: string,
	shownMessage: string | null
}

export async function tryCorrectSpelling(query: string): Promise<SpellingCorrection | null> {
	await loadSpellingCorrections();
	const tokens = query.split(" ");
	let message = null as string | null;
	let anythingChanged = false;
	const correctedTokens = tokens.map(token => {
		const specialCorrection = SPECIAL_MISSPELLINGS[token.toLowerCase()];
		if (specialCorrection) {
			message = specialCorrection.shown;
			anythingChanged = true;
			return specialCorrection.replace;
		}

		const correction = correctionsCache!.find(c => c.source === token);
		if (correction) {
			anythingChanged = true;
			return correction.target;
		}

		return token;
	});

	if (!anythingChanged) return null;

	return {
		newQuery: correctedTokens.join(" "),
		shownMessage: message
	};
}
