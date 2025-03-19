<script lang="ts">
	import SearchResultEntry from './SearchResultEntry.svelte';

	let { results = [] } = $props();
</script>

<div class="flex flex-col gap-4">
	{#each results as result}
		<SearchResultEntry {result} />
	{/each}
</div>
