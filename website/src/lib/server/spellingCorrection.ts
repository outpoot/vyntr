import { db } from '$lib/server/db';
import { spellingCorrections } from '$lib/server/schema';

const SPECIAL_MISSPELLINGS: Record<string, {shown: string, replace: string}> = {
	"guthib": { shown: "You spelled it wrong", replace: "github" }
} as const;

let corrections: {source: string, target: string}[] = []

async function loadSpellingCorrections() {
	if (corrections.length != 0) return
	corrections = await db.select()
		.from(spellingCorrections)
		.execute()
}

export type SpellingCorrection = {
	newQuery: string,
	shownMessage: string | null
}

export async function tryCorrectSpelling(query: string): Promise<SpellingCorrection | null> {
	await loadSpellingCorrections()
	const tokens = query.split(" ")
	let message = null as string | null
	let anythingChanged = false
	const correctedTokens = tokens.map(token => {
		const specialCorrection = SPECIAL_MISSPELLINGS[token.toLowerCase()]
		if (specialCorrection) {
			message = specialCorrection.shown
			anythingChanged = true
			return specialCorrection.replace
		}

		const correction = corrections.find(c => c.source === token)
		if (correction) {
			anythingChanged = true
			return correction.target
		}


		return token
	})

	if (!anythingChanged) return null

	const correctedQuery = correctedTokens.join(" ")
	return {
		newQuery: correctedQuery,
		shownMessage: message
	}
}