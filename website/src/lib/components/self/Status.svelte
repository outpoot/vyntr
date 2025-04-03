<script lang="ts">
	import { AlertCircle, CheckCircle2, AlertTriangle } from 'lucide-svelte';

	interface Props {
		type?: 'error' | 'success' | 'warning';
		message: string;
		maxWidth?: boolean;
	}

	let { type = 'error', message, maxWidth = true }: Props = $props();
</script>

<div
	class="inline-flex items-start gap-2 rounded-md border bg-background p-3 text-sm"
	class:max-w-xl={maxWidth}
	class:border-destructive={type === 'error'}
	class:border-green-200={type === 'success'}
	class:border-yellow-200={type === 'warning'}
>
	{#if type === 'error'}
		<AlertCircle class="mt-0.5 h-4 w-4 flex-shrink-0 text-destructive" />
	{:else if type === 'warning'}
		<AlertTriangle class="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-600" />
	{:else}
		<CheckCircle2 class="mt-0.5 h-4 w-4 flex-shrink-0 text-success" />
	{/if}
	<span
		class:text-destructive={type === 'error'}
		class:text-green-600={type === 'success'}
		class:text-yellow-600={type === 'warning'}
	>
		{message}
	</span>
</div>
