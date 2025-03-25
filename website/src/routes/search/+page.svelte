<script lang="ts">
	import SearchInput from '$lib/components/self/SearchInput.svelte';
	import SearchResults from '$lib/components/self/SearchResults.svelte';
	import DetailsPanelBliptext from '$lib/components/self/DetailsPanelBliptext.svelte';
	import DetailsPanelMath from '$lib/components/self/DetailsPanelMath.svelte';
	import DetailsPanelTimer from '$lib/components/self/DetailsPanelTimer.svelte';

	import { isMathExpression, evaluateMathExpression } from '$lib/mathUtils';
	import { parseTimerQuery } from '$lib/timerUtils';
	import type { CalculatorSearchDetail } from '$lib/types/searchDetails';

	import { page } from '$app/state';

	let query = $state(page.url.searchParams.get('q') || '');
	let searchData = $state({ web: [], bliptext: null });
	let mathResult = $state<CalculatorSearchDetail | null>(null);
	let timerSeconds = $state<number | null>(null);
	let isLoading = $state(false);

	async function performSearch() {
		isLoading = true;
		mathResult = null;
		timerSeconds = null;

		// Check for timer request
		const timerDuration = parseTimerQuery(query);
		if (timerDuration !== null) {
			timerSeconds = timerDuration;
		}
		// Check for math expression if not a timer
		else if (isMathExpression(query)) {
			try {
				const result = await evaluateMathExpression(query);
				mathResult = {
					type: 'calculator',
					expression: query,
					result: result.result
				};
			} catch (err) {
				console.error('Math evaluation error:', err);
			}
		}

		try {
			const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
			const data = await response.json();
			searchData = data;
		} catch (err) {
			console.error('Search error:', err);
		} finally {
			isLoading = false;
		}
	}

	$effect(() => {
		performSearch();
	});
</script>

<svelte:head>
	<title>{query} - Vyntr Search</title>
</svelte:head>

<div class="px-8 md:ml-8 lg:ml-16 xl:ml-24">
	<div class="mt-4 flex flex-col justify-start gap-4 lg:max-w-[700px]">
		<SearchInput bind:value={query} enableAutocomplete={false} showTrailingButtons={false} />

		{#if !isLoading}
			{#if timerSeconds !== null}
				<div class="mb-6">
					<DetailsPanelTimer seconds={timerSeconds} />
				</div>
			{:else if mathResult}
				<div class="mb-6">
					<DetailsPanelMath details={mathResult} />
				</div>
			{/if}
			<SearchResults results={searchData.web} />
		{:else}
			<!-- skeleton here would be better i think -->
			<h1>Loading results</h1>
		{/if}
	</div>

	{#if searchData.bliptext}
		<DetailsPanelBliptext details={searchData.bliptext} />
	{/if}
</div>
