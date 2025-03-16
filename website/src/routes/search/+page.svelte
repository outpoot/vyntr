<script lang="ts">
	import SearchInput from '$lib/components/self/SearchInput.svelte';
	import SearchResults from '$lib/components/self/SearchResults.svelte';

	import { page } from '$app/state';

	let query = $state(page.url.searchParams.get('q') || '');
</script>

<svelte:head>
	<title>Vyntr: {query}</title>
</svelte:head>

<div class="min-h-screen w-full bg-sidebar-background">
	<div class="sticky top-0 z-10 w-full">
		<div class="mx-auto flex max-w-2xl justify-center py-4">
			<SearchInput bind:value={query} enableAutocomplete={false} showTrailingButtons={false} />
		</div>
	</div>

	<div class="w-full">
		<div class="mx-auto max-w-2xl py-4 px-8">
			<SearchResults />
		</div>
	</div>
</div>