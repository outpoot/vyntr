<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Globe, MoreVertical } from 'lucide-svelte';
	import type { SearchResult } from '$lib/types/search';

	let { result } = $props<{ result: SearchResult }>();
	let imageError = $state(false);

	function formatDate(dateStr: string | null) {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleDateString(undefined, { 
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}
</script>

<div class="relative rounded-xl bg-primary p-4">
	<div class="flex items-start justify-between">
		<a href={result.url} class="group inline-flex flex-col">
			<div class="flex items-center gap-2">
				<div class="relative flex h-full items-center">
					<div
						class="flex h-[26px] w-[26px] items-center justify-center rounded-full bg-white p-[1px]"
					>
						{#if !imageError}
							<img
								src={result.favicon}
								alt=""
								class="ml-[1px] h-[22px] w-[22px] rounded-full object-contain"
								onerror={() => (imageError = true)}
							/>
						{:else}
							<Globe class="h-[18px] w-[18px] text-muted-foreground" />
						{/if}
					</div>
				</div>
				<div class="flex flex-col py-0.5">
					<span class="text-sm text-primary-foreground">{result.title}</span>
					<span class="text-xs text-muted-foreground">{result.url}</span>
				</div>
			</div>

			<h3 class="mt-1 text-xl text-blue-600 group-hover:underline">
				{result.pageTitle}
			</h3>
		</a>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				<button type="button" class="mt-1" onclick={(e) => e.preventDefault()}>
					<MoreVertical class="h-5 w-5 text-primary-foreground" />
				</button>
			</DropdownMenu.Trigger>
			<DropdownMenu.Content>
				<DropdownMenu.Item>Copy link</DropdownMenu.Item>
				<DropdownMenu.Item>Share</DropdownMenu.Item>
				<DropdownMenu.Item>Similar results</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>

	<div class="mt-2 flex text-sm text-muted-foreground">
		<span>
			{#if result.date}
				<span class="text-muted-foreground/60">
					{formatDate(result.date)} ―
				</span>
			{/if}
			{result.preview}
		</span>
	</div>
</div>
