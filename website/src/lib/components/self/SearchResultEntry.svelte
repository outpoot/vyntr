<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import Globe from 'lucide-svelte/icons/globe';
	import Link from 'lucide-svelte/icons/link';
	import MoreVertical from 'lucide-svelte/icons/more-vertical';
	import type { SearchResult } from '$lib/types/search';
	import { toast } from 'svelte-sonner';

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
	function truncateString(str: string, maxLength = 100) {
		return str.length > maxLength ? str.slice(0, maxLength) + '...' : str;
	}
</script>

<div
	class="relative overflow-hidden rounded-xl border bg-card p-4 shadow-custom-inset drop-shadow-md"
>
	<div class="flex items-start justify-between gap-2">
		<a href={result.url} class="group inline-flex min-w-0 flex-col">
			<div class="flex min-w-0 items-center gap-2">
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
							<Globe class="h-[18px] w-[18px] text-muted" />
						{/if}
					</div>
				</div>
				<div class="flex min-w-0 flex-col py-0.5">
					<span class="truncate text-sm text-foreground">{truncateString(result.title, 50)}</span>
					<span class="truncate text-xs text-muted">{truncateString(result.url, 50)}</span>
				</div>
			</div>

			<h3 class="mt-1 text-xl text-blue-600 group-hover:underline">
				{truncateString(result.pageTitle, 50)}
			</h3>
		</a>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				<button type="button" class="mt-1" onclick={(e) => e.preventDefault()}>
					<MoreVertical class="h-5 w-5 text-primary" />
				</button>
			</DropdownMenu.Trigger>
			<DropdownMenu.Content class="w-32 rounded-xl p-2">
				<DropdownMenu.Item
					class="flex w-full items-center gap-2 rounded-md p-3 text-sm font-medium transition-colors hover:bg-sidebar-accent"
					onclick={() => {
						navigator.clipboard.writeText(result.url);
						toast('The link has been copied to your clipboard.');
					}}
				>
					<Link />
					Copy link
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>

	<div class="mt-2 flex text-sm text-muted">
		<span>
			{#if result.date}
				<span class="text-muted/60">
					{formatDate(result.date)} ―
				</span>
			{/if}
			{truncateString(result.preview, 100)}
		</span>
	</div>
</div>
