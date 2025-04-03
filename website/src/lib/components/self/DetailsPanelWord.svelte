<script lang="ts">
	import { Book } from 'lucide-svelte';
	import type { WordDefinitionSearchDetail } from '$lib/types/searchDetails';
	import { Badge } from '../ui/badge';

	const { details } = $props<{ details: WordDefinitionSearchDetail }>();
</script>

<div
	class="relative mb-6 overflow-hidden rounded-xl border bg-card p-4 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] drop-shadow-md"
>
	<div class="flex items-start gap-4">
		<div class="rounded-full bg-primary/50 p-2 transition-transform hover:scale-110">
			<Book class="h-4 w-4" />
		</div>
		<div class="flex w-full flex-col gap-4">
			<div>
				<h3 class="text-2xl font-bold">{details.word}</h3>
				{#if details.partOfSpeech}
					<p class="text-sm italic text-muted">{details.partOfSpeech}</p>
				{/if}
				{#if details.pronunciations?.length}
					<p class="text-sm text-muted">{details.pronunciations.join(', ')}</p>
				{/if}
			</div>

			{#if details.definitions?.length}
				<div class="space-y-2">
					{#each details.definitions as def, i}
						<div class="inline-flex items-start justify-center gap-3">
							<div
								class="flex h-8 w-8 items-center justify-center rounded-full bg-primary/50 p-2 transition-transform hover:scale-110 select-none"
							>
								{i + 1}
							</div>
							<div class="flex flex-col">
								<p>{def.gloss}</p>
								<p class="text-sm italic text-muted">{def.pos}</p>
							</div>
						</div>
					{/each}
				</div>
			{/if}

			{#if details.examples?.length}
				<div>
					<h4 class="mb-1 font-semibold">Examples:</h4>
					<ul class="list-inside list-disc space-y-1">
						{#each details.examples as example}
							<li class="text-sm text-muted">{example}</li>
						{/each}
					</ul>
				</div>
			{/if}

			{#if details.synonyms?.length}
				<div class="flex gap-4">
					<div class="inline-flex items-center gap-2">
						<h4 class="text-success my-auto text-sm">Similar:</h4>
						<div class="flex flex-wrap gap-1">
							{#each details.synonyms as synonym}
								<Badge variant="outline" class="transition-colors hover:bg-primary/50">
									{synonym}
								</Badge>
							{/each}
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
