<script lang="ts">
	import { cn } from '$lib/utils.js';
	import { Separator } from '$lib/components/ui/separator';
	import type { HTMLInputAttributes } from 'svelte/elements';

	type Props = HTMLInputAttributes & {
		children: () => any;
		ref?: any;
		type?: HTMLInputAttributes['type'];
		class?: string;
		focused?: boolean;
		showSuggestions?: boolean;
	};

	let {
		children,
		ref = $bindable(null),
		value = $bindable(),
		type,
		class: className,
		showSuggestions = false,
		...restProps
	}: Props = $props();
</script>

<div class="relative w-full">
	<input
		bind:this={ref}
		class={cn(
			'flex w-full border bg-background px-3 py-2 text-2xl placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 md:text-xl',
			showSuggestions ? 'rounded-b-none rounded-t-[1.5rem] border-b-0' : 'rounded-[1.5rem]',
			className
		)}
		{type}
		bind:value
		{...restProps}
	/>
	{#if showSuggestions}
		<div
			class="absolute left-0 right-0 top-full z-50 rounded-b-[1.5rem] border-x-2 border-b-2 border-ring bg-primary"
		>
			<Separator class="mx-auto w-[95%] " />
			<div class="max-h-[500px] overflow-y-auto py-2">
				{@render children()}
			</div>
		</div>
	{/if}
</div>
