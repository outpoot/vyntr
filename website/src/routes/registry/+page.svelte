<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import { WEBSITE_CATEGORIES } from '$lib/constants';
	import { Button } from '$lib/components/ui/button';
	import * as Select from '$lib/components/ui/select';
	import { scale } from 'svelte/transition';

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

	function copyLink(domain: string) {
		navigator.clipboard.writeText(domain);
		copiedDomain = domain;
		toast.success('Link copied to clipboard');
		setTimeout(() => (copiedDomain = ''), 2000);
	}
</script>

<div class="container mx-auto p-8">
	<div class="mb-8">
		<h1 class="text-3xl font-bold">Registry</h1>
		<p class="text-muted">Discover and explore websites in our community</p>
	</div>

	<div class="mb-6 flex items-center gap-4">
		<div class="relative flex-1">
			<Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
			<Input
				bind:value={searchQuery}
				placeholder="Search domains, descriptions, or tags..."
				class="pl-10"
			/>
		</div>
		<Select.Root type="single" bind:value={selectedCategory}>
			<Select.Trigger class="w-[180px]">
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

	<div class="space-y-4">
		{#each filteredSites as site}
			<div class="rounded-lg border bg-card p-4">
				<div class="mb-3 flex items-start justify-between gap-4">
					<div class="flex flex-1 gap-3">
						<div class="mt-1 h-8 w-8 shrink-0 overflow-hidden rounded-full bg-muted">
							<Globe class="h-full w-full p-1.5 text-muted-foreground" />
						</div>
						<div class="min-w-0 flex-1">
							<div class="flex items-center gap-2">
								<h3 class="truncate text-base font-semibold">
									{site.domain.replace('https://', '')}
								</h3>
								{#if site.isFeatured}
									<Star class="h-4 w-4 flex-shrink-0 text-yellow-400" />
								{/if}
							</div>
							<p class="mt-1 line-clamp-2 text-sm text-muted">
								{site.description || 'No description'}
							</p>
							<div class="mt-2 flex flex-wrap items-center gap-2">
								<Badge variant="secondary" class="capitalize">
									{WEBSITE_CATEGORIES.find((c) => c.value === site.category)?.label ||
										site.category}
								</Badge>
								{#each site.tags?.slice(0, 3) || [] as tag}
									<Badge variant="outline">{tag}</Badge>
								{/each}
							</div>
						</div>
					</div>
					<div class="flex flex-col items-end gap-2">
						<div class="flex items-center gap-1">
							<Button
								variant="ghost"
								size="icon"
								onclick={() => copyLink(site.domain)}
								class="bg-card hover:bg-secondary/50"
							>
								{#if copiedDomain === site.domain}
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
								size="icon"
								onclick={() => window.open(site.domain, '_blank')}
								class="bg-card hover:bg-secondary/50"
							>
								<ArrowUpRight class="h-4 w-4" />
							</Button>
						</div>
						<div class="flex items-center gap-2">
							<div class="flex items-center gap-1 text-xs text-muted">
								<Globe class="h-3 w-3" />
								<span>{site.visits.toLocaleString()} visits</span>
							</div>
							<div class="flex items-center gap-1">
								<Button variant="ghost" size="sm" class="h-7">
									<ThumbsUp class="mr-1 h-3 w-3" />
									<span class="text-xs">{site.upvotes}</span>
								</Button>
								<Button variant="ghost" size="sm" class="h-7">
									<ThumbsDown class="mr-1 h-3 w-3" />
									<span class="text-xs">{site.downvotes}</span>
								</Button>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/each}
	</div>
</div>
