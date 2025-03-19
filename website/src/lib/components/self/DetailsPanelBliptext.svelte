<script lang="ts">
	import type { BliptextSearchDetail } from '$lib/types/searchDetails';
	import * as Card from '$lib/components/ui/card';

	let { details } = $props<{ details: BliptextSearchDetail }>();

	let truncated = $state('');

	let imageError = $state(false);
	let expanded = $state(false);
	let hasMore = $state(false);

	$effect(() => {
		if (!details?.article.summary.introduction) return;
		const intro = details.article.summary.introduction;

		truncated = intro.slice(0, 500);
		hasMore = intro.length > 500;
	});
</script>

{#if details}
	<Card.Root class="z-0 h-fit w-96 bg-card text-card-foreground">
		<Card.Header class="pb-3">
			<Card.Title class="text-lg font-semibold leading-none tracking-tight">
				{details.article.title}
			</Card.Title>
		</Card.Header>

		<Card.Content class="grid gap-4">
			{#if details.article.summary.image && !imageError}
				<img
					src={details.article.summary.image.url}
					alt={details.article.summary.image.caption}
					class="aspect-video w-full rounded-md object-cover"
					onerror={() => (imageError = true)}
				/>
			{/if}

			<div
				class="grid auto-rows-[minmax(0,auto)] grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-3"
			>
				{#each details.article.summary.keys as key}
					<div class="flex flex-col gap-1">
						<h4 class="font-medium leading-none">{key.key}</h4>
						<p class="text-sm text-muted-foreground">
							{key.value}
						</p>
					</div>
				{/each}
			</div>

			{#if details.article.summary.introduction}
				<div class="space-y-2 border-t pt-4">
					<p
						class="break-long-words overflow-hidden text-sm text-card-foreground"
						style="max-width: 100%;"
						lang="en"
					>
						{#if expanded}
							{details.article.summary.introduction}
						{:else}
							{truncated || details.article.summary.introduction}
						{/if}
						{#if hasMore}
							<button
								type="button"
								class="text-blue-500 hover:underline focus:outline-none"
								onclick={() => (expanded = !expanded)}
							>
								{expanded ? ' Show less' : '...'}
							</button>
						{/if}
					</p>
				</div>
			{/if}
		</Card.Content>

		<Card.Footer class="flex items-center justify-center border-t p-4">
			<a
				href={`https://bliptext.com/articles/${details.article.slug}`}
				class="flex items-center gap-1 hover:opacity-80"
				target="_blank"
				rel="noopener noreferrer"
			>
				<span class="text-xs text-muted-foreground">Powered by</span>
				<img src="https://bliptext.com/favicon.svg" alt="Bliptext logo" class="h-4 w-4" />
				<span class="text-xs font-medium">Bliptext</span>
			</a>
		</Card.Footer>
	</Card.Root>
{/if}
