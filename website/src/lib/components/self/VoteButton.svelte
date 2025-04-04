<script lang="ts">
	import { ThumbsUp, ThumbsDown } from 'lucide-svelte';
	import { scale, fly } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import { formatCompactNumber } from '$lib/utils';

	interface Props {
		count: number;
		isActive?: boolean;
		handleVote: () => void;
		type: 'up' | 'down';
	}

	let { count, isActive = false, handleVote, type }: Props = $props();
</script>

<button
	class="vote-btn {type === 'up' ? 'hover:text-blue-600' : 'hover:text-destructive'} {isActive
		? type === 'up'
			? 'active-up'
			: 'active-down'
		: ''}"
	onclick={() => handleVote()}
>
	{#key isActive}
		<div in:scale={{ duration: 250, delay: 50, start: 0.5, easing: quintOut }}>
			{#if type === 'up'}
				<ThumbsUp class="h-4 w-4" fill={isActive ? 'currentColor' : 'none'} />
			{:else}
				<ThumbsDown class="h-4 w-4" fill={isActive ? 'currentColor' : 'none'} />
			{/if}
		</div>
	{/key}

	<div class="number-container">
		<span class="number-placeholder" aria-hidden="true">
			{formatCompactNumber(count)}
		</span>
		<div class="number-wrapper">
			{#key count}
				<span
					class="number text-sm font-medium"
					in:fly={{ y: -20, duration: 200, opacity: 0, easing: quintOut }}
					out:fly|local={{ y: 20, duration: 200, opacity: 0, easing: quintOut }}
				>
					{formatCompactNumber(count)}
				</span>
			{/key}
		</div>
	</div>
</button>

<style>
	.vote-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		height: 2rem;
		padding: 0 0.5rem;
		border-radius: 0.375rem;
		background: transparent;
		overflow: hidden;
	}

	.number-container {
		position: relative;
		overflow: hidden;
		height: 100%;
		display: flex;
		align-items: center;
	}

	.number-wrapper {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
	}

	.number {
		position: absolute;
		height: 100%;
		display: flex;
		align-items: center;
	}

	.number-placeholder {
		opacity: 0;
	}

	.content {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		min-width: 3rem;
	}

	.active-up {
		color: rgb(37 99 235);
		background: rgb(37 99 235 / 0.1);
	}

	.active-down {
		color: rgb(239 68 68);
		background: rgb(239 68 68 / 0.1);
	}
</style>
