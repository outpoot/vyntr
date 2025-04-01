<script lang="ts">
	import SearchInput from '$lib/components/self/SearchInput.svelte';
	import SearchResults from '$lib/components/self/SearchResults.svelte';
	import DetailsPanelBliptext from '$lib/components/self/DetailsPanelBliptext.svelte';
	import DetailsPanelMath from '$lib/components/self/DetailsPanelMath.svelte';
	import DetailsPanelTimer from '$lib/components/self/DetailsPanelTimer.svelte';
	import DetailsPanelDate from '$lib/components/self/DetailsPanelDate.svelte';
	import DetailsPanelWord from '$lib/components/self/DetailsPanelWord.svelte';
	import DetailsPanelCurrency from '$lib/components/self/DetailsPanelCurrency.svelte';

	import { isMathExpression, evaluateMathExpression } from '$lib/utils/math';
	import { parseTimerQuery } from '$lib/utils/timer';
	import type { CalculatorSearchDetail, SearchResponse } from '$lib/types/searchDetails';

	import { page } from '$app/state';
	import DetailsPanelUnitConversion from '$lib/components/self/DetailsPanelUnitConversion.svelte';
	import { Separator } from '$lib/components/ui/separator';

	let query = $state(page.url.searchParams.get('q') || '');
	let searchData = $state<SearchResponse>({
		web: [],
		bliptext: null,
		date: null,
		word: null,
		currency: null,
		unitConversion: null
	});
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

<div class="px-8">
	<div class="mt-4 flex flex-col items-start gap-4">
		<div class="w-full lg:w-[700px]">
			<SearchInput bind:value={query} enableAutocomplete={false} showTrailingButtons={false} />
		</div>

		<div class="flex flex-row gap-4">
			<div class="min-w-0 flex-1 lg:max-w-[700px]">
				{#if !isLoading}
					{#if searchData.unitConversion || searchData.currency || searchData.word || searchData.date || timerSeconds !== null || mathResult}
						<div class="mb-6">
							{#if searchData.unitConversion}
								<DetailsPanelUnitConversion details={searchData.unitConversion} />
							{:else if searchData.currency}
								<DetailsPanelCurrency details={searchData.currency} />
							{:else if searchData.word}
								<DetailsPanelWord details={searchData.word} />
							{:else if searchData.date}
								<DetailsPanelDate {...searchData.date} />
							{:else if timerSeconds !== null}
								<DetailsPanelTimer seconds={timerSeconds} />
							{:else if mathResult}
								<DetailsPanelMath details={mathResult} />
							{/if}
						</div>
					{/if}

					<SearchResults results={searchData.web} />
				{:else}
					<!-- skeleton here would be better i think -->
					<h1>Loading results</h1>
				{/if}
			</div>

			{#if searchData.bliptext}
				<div class="hidden w-64 flex-shrink-0 lg:block">
					<DetailsPanelBliptext details={searchData.bliptext} />
				</div>
			{/if}
		</div>
	</div>
</div>
