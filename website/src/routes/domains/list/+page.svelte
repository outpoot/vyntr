<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Globe, Plus } from 'lucide-svelte';
	import { goto } from '$app/navigation';
	import Explore from '$lib/components/self/icon/Explore.svelte';

	let { data } = $props();

	const statusBadgeClass = (status: string) => {
		const base = 'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium';
		switch (status) {
			case 'public':
				return `${base} bg-success text-green-700`;
			case 'pending':
				return `${base} bg-yellow-50 text-yellow-700`;
			case 'unlisted':
				return `${base} bg-muted text-muted-foreground`;
			case 'suspended':
				return `${base} bg-destructive text-destructive-foreground`;
			default:
				return base;
		}
	};
</script>

<div class="container mx-auto space-y-6 p-6">
	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold">Connected Domains</h1>
		<Button onclick={() => goto('/domains/register')} variant="default">
			<Plus class="h-4 w-4" />
			Register domain
		</Button>
	</div>

	{#if data.domains.length === 0}
		<div class="py-12 text-center">
			<Globe class="mx-auto h-12 w-12 text-muted" />
			<h3 class="mt-2 text-sm font-semibold">No domains connected</h3>
			<p class="mx-auto max-w-lg rounded-lg px-4 py-3 text-center text-sm text-muted">
				Connect your domain to unlock
				<a
					class="inline-flex translate-y-[1.5px] items-center gap-1 font-medium hover:underline"
					href="/"
				>
					<img src="/favicon.svg" alt="Vyntr logo" class="h-4 w-4" />
					Vyntr
				</a>
				indexing, enhance discoverability in the
				<a
					class="inline-flex translate-y-[1.7px] items-center gap-1 font-medium hover:underline"
					href="/explore"
				>
					<Explore class="h-4 w-4 translate-y-[1.1px]" />
					Registry
				</a>, and start building your audience.
			</p>
		</div>
	{:else}
		<div class="overflow-hidden rounded-lg border bg-card shadow">
			<table class="min-w-full divide-y">
				<thead class="bg-primary/10">
					<tr>
						<th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Domain</th>
						<th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Status</th>
						<th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Added</th>
						<th class="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider"
							>Actions</th
						>
					</tr>
				</thead>
				<tbody class="divide-y bg-card">
					{#each data.domains as domain}
						<tr>
							<td class="whitespace-nowrap px-6 py-4">
								<div class="text-sm font-medium">{domain.domain}</div>
							</td>
							<td class="whitespace-nowrap px-6 py-4">
								<span class={statusBadgeClass(domain.status)}>
									{domain.status}
								</span>
							</td>
							<td class="whitespace-nowrap px-6 py-4 text-sm">
								{new Date(domain.createdAt).toLocaleDateString()}
							</td>
							<td class="whitespace-nowrap px-6 py-4 text-right text-sm">
								<Button
									variant="ghost"
									size="sm"
									onclick={() => goto(`/domains/manage/${domain.domain.replace('https://', '')}`)}
								>
									Manage
								</Button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
