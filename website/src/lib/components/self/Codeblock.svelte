<script>
	import { scale } from 'svelte/transition';
	import { Button } from '../ui/button';
	import { Check, Copy } from 'lucide-svelte';

	const { text = '', onCopy = () => {}, isSuccess = false } = $props();
</script>

<div class="inline-flex items-center gap-2 overflow-hidden rounded-md border bg-muted/50">
	<code class="block overflow-x-auto p-3 font-mono text-sm">{text}</code>
	<Button
		variant="ghost"
		size="sm"
		class="mr-1 h-8 w-8 p-0"
		onclick={() => onCopy()}
		aria-label="Copy to clipboard"
	>
		{#if isSuccess}
			<div in:scale|fade={{ duration: 150 }}>
				<Check class="h-4 w-4" />
			</div>
		{:else}
			<div in:scale|fade={{ duration: 150 }}>
				<Copy class="h-4 w-4" />
			</div>
		{/if}
	</Button>
</div>
