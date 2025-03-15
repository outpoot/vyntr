<script lang="ts">
	import SearchInput from '$lib/components/self/SearchInput.svelte';
    import SearchResults from '$lib/components/self/SearchResults.svelte';

	import { page } from '$app/state';

	let query = $state(page.url.searchParams.get('q') || '');
</script>

<div class="min-h-screen">
	<div class="sticky top-0 z-10">
		<div class="container mx-auto flex justify-center py-4">
			<SearchInput bind:value={query} enableAutocomplete={false} showTrailingButtons={false} />
		</div>
	</div>

	<div class="container mx-auto py-4">
		<div class="mx-auto max-w-4xl">
			<SearchResults />
		</div>
	</div>
</div>
