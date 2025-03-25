<script lang="ts">
	import { AlertCircle, CheckCircle2 } from 'lucide-svelte';

	export let type: 'error' | 'success' = 'error';
	export let message: string;
</script>

<div
	class="flex items-start gap-2 rounded-md border bg-background p-3 text-sm max-w-xl"
	class:border-destructive={type === 'error'}
	class:border-green-200={type === 'success'}
>
	{#if type === 'error'}
		<AlertCircle class="mt-0.5 h-4 w-4 flex-shrink-0 text-destructive" />
	{:else}
		<CheckCircle2 class="mt-0.5 h-4 w-4 flex-shrink-0 text-green-600" />
	{/if}
	<span class:text-destructive={type === 'error'} class:text-green-600={type === 'success'}>
		{message}
	</span>
</div>
