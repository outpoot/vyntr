import { distance } from 'fastest-levenshtein';

// Key format: `${token}:${n}
const similarityCache: Record<string, string[]> = {};

// Common first character typos for English
const commonFirstCharTypos: Record<string, string[]> = {
	a: ['q', 'w', 's', 'z'],
	s: ['a', 'w', 'd', 'x', 'z'],
	b: ['v', 'g', 'h', 'n'],
	c: ['x', 'v', 'f', 'd'],
	d: ['s', 'e', 'f', 'c', 'x'],
	e: ['w', 'r', 'd', 's'],
	f: ['d', 'r', 'g', 'v', 'c'],
	g: ['f', 't', 'h', 'b', 'v'],
	h: ['g', 'y', 'j', 'n', 'b'],
	i: ['u', 'k', 'j', 'o'],
	j: ['h', 'u', 'k', 'm', 'n'],
	k: ['j', 'i', 'l', 'm'],
	l: ['k', 'o', 'p'],
	m: ['n', 'j', 'k'],
	n: ['b', 'h', 'j', 'm'],
	o: ['i', 'p', 'l'],
	p: ['o', 'l'],
	q: ['w', 'a'],
	r: ['e', 'f', 't', 'd'],
	t: ['r', 'g', 'y', 'f'],
	u: ['y', 'j', 'i', 'h'],
	v: ['c', 'f', 'g', 'b'],
	w: ['q', 'a', 's', 'e'],
	x: ['z', 's', 'd', 'c'],
	y: ['t', 'h', 'u', 'g'],
	z: ['a', 's', 'x']
};

/**
 * Returns the n most similar strings to the given token from a list of strings.
 * Uses caching for performance and applies heuristics to improve search speed.
 *
 * @param stringList - A large array of strings to search through
 * @param token - The target string to find similarities for
 * @param n - Number of similar strings to return
 * @param maxDistance - Optional maximum Levenshtein distance (default: 3)
 * @returns Array of the n most similar strings
 */
export function findMostSimilar(
	stringList: string[],
	token: string,
	n: number,
	maxDistance: number = 3
): string[] {
	const cacheKey = `${token}:${n}`;
	if (similarityCache[cacheKey]) {
		return similarityCache[cacheKey];
	}

	if (!token || stringList.length === 0 || n <= 0) {
		return [];
	}

	const exactMatch = stringList.find((s) => s === token);
	if (exactMatch) {
		return [exactMatch];
	}

	const normalizedToken = token.toLowerCase().trim();
	const tokenLength = normalizedToken.length;

	// Heuristic 1: Filter by length similarity first (much faster than full distance calculation)
	const lengthFilteredList = stringList.filter((s) => {
		const lengthDiff = Math.abs(s.length - tokenLength);
		return lengthDiff <= maxDistance;
	});

	// Heuristic 2: Filter by first character (optional, can improve performance for large lists)
	// Only consider strings that start with the same letter or a common typo of the first letter
	const firstChar = normalizedToken.charAt(0);

	let charactersToCheck = [firstChar];
	if (commonFirstCharTypos[firstChar]) {
		charactersToCheck = [...charactersToCheck, ...commonFirstCharTypos[firstChar]];
	}

	const characterFilteredList = lengthFilteredList.filter((s) =>
		charactersToCheck.includes(s.charAt(0).toLowerCase())
	);

	const listToProcess = characterFilteredList.length >= n ? characterFilteredList : lengthFilteredList;

	const withDistances = listToProcess.map((str) => ({
		string: str,
		distance: distance(normalizedToken, str.toLowerCase())
	}));

	withDistances.sort((a, b) => a.distance - b.distance);

	// Get top N results within maxDistance
	const results = withDistances
		.filter((item) => item.distance <= maxDistance)
		.slice(0, n)
		.map((item) => item.string);

	// Cache the results
	similarityCache[cacheKey] = results;

	return results;
}
