<script lang="ts">
	import SearchInput from '$lib/components/self/SearchInput.svelte';
	import SearchResults from '$lib/components/self/SearchResults.svelte';
	import DetailsPanelBliptext from '$lib/components/self/DetailsPanelBliptext.svelte';
	import DetailsPanelMath from '$lib/components/self/DetailsPanelMath.svelte';
	
	import { isMathExpression, evaluateMathExpression } from '$lib/mathUtils';
	import type { CalculatorSearchDetail } from '$lib/types/searchDetails';

	import { page } from '$app/state';

	let query = $state(page.url.searchParams.get('q') || '');
	let searchData = $state({ web: [], bliptext: null });
	let mathResult = $state<CalculatorSearchDetail | null>(null);
	let isLoading = $state(false);

	async function performSearch() {
		isLoading = true;
		mathResult = null;

		if (isMathExpression(query)) {
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

<div class="bg-sidebar-background min-h-screen w-full">
	<div class="sticky top-0 z-10 w-full">
		<div class="mx-auto flex max-w-2xl justify-center py-4">
			<SearchInput bind:value={query} enableAutocomplete={false} showTrailingButtons={false} />
		</div>
	</div>

	<div class="mx-auto max-w-[1200px] px-8">
		<div class="flex gap-8">
			<div class="flex-1">
				{#if !isLoading}
					{#if mathResult}
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
	</div>
</div>
