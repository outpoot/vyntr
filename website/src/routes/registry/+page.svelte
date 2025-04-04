<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import { WEBSITE_CATEGORIES } from '$lib/constants';
	import { Button } from '$lib/components/ui/button';
	import * as Select from '$lib/components/ui/select';
	import { toast } from 'svelte-sonner';
	import {
		Search,
		ArrowUpRight,
		Star,
		ThumbsUp,
		ThumbsDown,
		Link2,
		Globe,
		Check
	} from 'lucide-svelte';
	import { scale } from 'svelte/transition';

	let { data } = $props();

	let searchQuery = $state('');
	let selectedCategory = $state('all');
	let copiedDomain = $state('');

	const filteredSites = $derived(
		data.sites.filter((site: any) => {
			const terms = searchQuery.toLowerCase().split(' ').filter(Boolean);
			const matchesSearch = terms.every(
				(term) =>
					site.domain.toLowerCase().includes(term) ||
					site.description?.toLowerCase().includes(term) ||
					site.tags?.some((tag: string) => tag.toLowerCase().includes(term)) ||
					site.category.toLowerCase().includes(term)
			);
			const matchesCategory = selectedCategory === 'all' || site.category === selectedCategory;
			return matchesSearch && matchesCategory;
		})
	);

	function getFaviconUrl(domain: string): string {
		// PLACEHOLDER TODO
		try {
			const url = new URL(domain.startsWith('http') ? domain : `https://${domain}`);
			return `https://www.google.com/s2/favicons?domain=${url.hostname}&sz=32`;
		} catch (e) {
			return '';
		}
	}

	function copyLink(domain: string) {
		navigator.clipboard.writeText(domain);
		copiedDomain = domain;
		toast.success('Link copied to clipboard');
		setTimeout(() => (copiedDomain = ''), 2000);
	}

	function getCleanDomain(domain: string): string {
		try {
			const url = new URL(domain.startsWith('http') ? domain : `https://${domain}`);
			return url.hostname.replace(/^www\./, '');
		} catch (e) {
			return domain.replace(/^https?:\/\//, '').replace(/^www\./, '');
		}
	}
</script>

<div class="container mx-auto p-8">
	<div class="mb-8">
		<h1 class="text-3xl font-bold">Registry</h1>
		<p class="text-muted">Discover and explore websites in our community</p>
	</div>

	<div class="mb-6 flex flex-wrap items-center gap-4">
		<div class="relative min-w-[200px] flex-1">
			<Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
			<Input
				bind:value={searchQuery}
				placeholder="Search domains, descriptions, or tags..."
				class="pl-10"
			/>
		</div>
		<Select.Root type="single" bind:value={selectedCategory}>
			<Select.Trigger class="w-full sm:w-[180px]">
				<span class="capitalize">
					{selectedCategory === 'all'
						? 'All categories'
						: WEBSITE_CATEGORIES.find((c) => c.value === selectedCategory)?.label}
				</span>
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="all">All categories</Select.Item>
				{#each WEBSITE_CATEGORIES as category}
					<Select.Item value={category.value}>{category.label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>

	{#if filteredSites.length === 0}
		<p class="py-8 text-center text-muted">No sites found matching your criteria.</p>
	{:else}
		<div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
			{#each filteredSites as site (site.domain)}
				{@const isCopied = copiedDomain === site.domain}
				{@const faviconUrl = getFaviconUrl(site.domain)}
				<div
					class="group relative flex flex-col rounded-xl border bg-card p-4 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] drop-shadow-md transition-shadow hover:shadow-lg"
				>
					<div class="flex flex-1 flex-col gap-3">
						<div class="flex items-start justify-between gap-2">
							<a
								href={site.domain}
								target="_blank"
								rel="noopener noreferrer"
								class="group/link flex min-w-0 items-center gap-2"
							>
								<div
									class="flex h-6 w-6 flex-shrink-0 items-center justify-center overflow-hidden rounded-full border bg-white"
								>
									{#if faviconUrl}
										<img
											src={faviconUrl}
											alt="{getCleanDomain(site.domain)} favicon"
											class="h-full w-full object-contain"
											loading="lazy"
										/>
										<Globe class="hidden h-4 w-4 text-muted" aria-hidden="true" />
									{:else}
										<Globe class="h-4 w-4 text-muted" aria-hidden="true" />
									{/if}
								</div>
								<h3
									class="truncate text-base font-semibold text-blue-600 group-hover/link:underline"
								>
									{getCleanDomain(site.domain)}
								</h3>
								<ArrowUpRight
									class="h-4 w-4 flex-shrink-0 text-muted transition-colors group-hover/link:text-blue-600"
								/>
							</a>
							{#if site.isFeatured}
								<Star class="h-4 w-4 flex-shrink-0 text-yellow-400" aria-label="Featured" />
							{/if}
						</div>

						<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
							<div class="flex items-center gap-1">
								<Globe class="h-3 w-3" />
								<span>{site.visits?.toLocaleString() ?? 'N/A'}</span>
							</div>
							<Badge variant="secondary" class="text-xs font-normal capitalize">
								{WEBSITE_CATEGORIES.find((c) => c.value === site.category)?.label || site.category}
							</Badge>
							{#each site.tags?.slice(0, 2) || [] as tag}
								<Badge variant="outline" class="text-xs font-normal">{tag}</Badge>
							{/each}
						</div>

						<p class="line-clamp-2 flex-1 text-sm text-muted">
							{site.description || 'No description provided.'}
						</p>
					</div>

					<div class="mt-3 flex items-center justify-end gap-1 border-t pt-3">
						<Button
							variant="ghost"
							size="icon"
							class="h-8 w-8 hover:bg-secondary/80"
							aria-label="Copy link"
							onclick={() => copyLink(site.domain)}
							disabled={isCopied}
						>
							{#if isCopied}
								<div in:scale|fade={{ duration: 150 }}>
									<Check class="h-4 w-4" />
								</div>
							{:else}
								<div in:scale|fade={{ duration: 150 }}>
									<Link2 class="h-4 w-4" />
								</div>
							{/if}
						</Button>

						<Button
							variant="ghost"
							size="sm"
							class="group/button relative isolate h-8 px-2 transition-colors hover:bg-blue-600/15 hover:text-blue-600"
						>
							<ThumbsUp
								class="inline-flex h-4 w-4 items-center justify-center transition-colors group-hover/button:text-blue-600"
							/>

							{site.upvotes ?? 0}
						</Button>

						<Button
							variant="ghost"
							size="sm"
							class="group/button relative isolate h-8 px-2 transition-colors hover:bg-red-600/15 hover:text-destructive"
						>
							<ThumbsDown
								class="inline-flex h-4 w-4 items-center justify-center transition-colors group-hover/button:text-destructive"
							/>

							{site.downvotes ?? 0}
						</Button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
