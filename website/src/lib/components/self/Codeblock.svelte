<script>
	import { scale } from 'svelte/transition';
	import { Button } from '../ui/button';
	import { Check, Copy } from 'lucide-svelte';

	const { text = '', displayOnly = false } = $props();
	let isSuccess = $state(false);

	async function copyToClipboard() {
		try {
			await navigator.clipboard.writeText(text);
			isSuccess = true;
			setTimeout(() => {
				isSuccess = false;
			}, 2000);
		} catch (err) {
			console.error('Failed to copy text:', err);
		}
	}
</script>

<div class="flex w-full items-center gap-2 overflow-hidden rounded-md border bg-primary/10">
	<code class="block flex-grow overflow-x-auto whitespace-pre-wrap p-3 font-mono text-sm">
		{text}
	</code>

	{#if !displayOnly}
		<Button
			variant="ghost"
			size="sm"
			class="mr-1 h-8 w-8 flex-shrink-0 p-0 hover:bg-primary/15"
			onclick={copyToClipboard}
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
	{/if}
</div>
