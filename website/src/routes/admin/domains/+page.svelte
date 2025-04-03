<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as Card from '$lib/components/ui/card';
	import { ExternalLink, Check, X } from 'lucide-svelte';

	interface User {
		id: string;
		email: string;
		name: string;
		emailVerified: boolean;
		createdAt: Date;
		updatedAt: Date;
		isAdmin: boolean;
	}

	interface Domain {
		id: string;
		domain: string;
		description: string | null;
		category: string;
		tags: string[];
		status: string;
		createdAt: Date;
		updatedAt: Date;
		user: User;
	}

	let { data } = $props<{ domains: Domain[] }>();
	let domains = $state(data.domains);

	async function handleAction(domain: Domain, action: 'approve' | 'reject') {
		try {
			const response = await fetch(
				`/api/admin/domains/${domain.domain.replace('https://', '')}/${action}`,
				{
					method: 'POST'
				}
			);

			if (response.ok) {
				domains = domains.filter((d: { id: string }) => d.id !== domain.id);
			}
		} catch (error) {
			console.error(`Failed to ${action} domain:`, error);
		}
	}
</script>

<div class="container mx-auto p-8">
	<div class="mb-8">
		<h1 class="text-3xl font-bold">Domain Review</h1>
		<p class="text-muted">Review and manage domain submissions</p>
	</div>

	<div class="grid gap-6">
		{#if domains.length === 0}
			<div class="rounded-lg border bg-card p-8 text-center">
				<h3 class="text-lg font-semibold">No pending domains</h3>
				<p class="text-sm text-muted">All clear! No domains waiting for review.</p>
			</div>
		{:else}
			{#each domains as domain (domain.id)}
				<Card.Root>
					<Card.Header>
						<div class="flex items-start justify-between">
							<div>
								<Card.Title>{domain.domain}</Card.Title>
								<Card.Description class="text-muted"
									>Submitted by {domain.user.email}</Card.Description
								>
							</div>
							<Button
								variant="outline"
								size="sm"
								onclick={() => window.open(domain.domain, '_blank')}
							>
								<ExternalLink class="h-4 w-4" />
								Visit
							</Button>
						</div>
					</Card.Header>
					<Card.Content>
						<div class="space-y-4">
							<div>
								<div class="font-medium">Description</div>
								<p class="text-sm text-muted">{domain.description || 'No description provided'}</p>
							</div>
							<div>
								<div class="font-medium">Category</div>
								<p class="text-sm capitalize text-muted">{domain.category}</p>
							</div>
							{#if domain.tags?.length}
								<div>
									<div class="font-medium">Tags</div>
									<div class="mt-2 flex flex-wrap gap-2">
										{#each domain.tags as tag}
											<Badge variant="secondary">{tag}</Badge>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</Card.Content>
					<Card.Footer class="flex justify-end gap-2">
						<Button variant="destructive" onclick={() => handleAction(domain, 'reject')}>
							<X class="h-4 w-4" />
							Reject
						</Button>
						<Button variant="default" onclick={() => handleAction(domain, 'approve')}>
							<Check class="h-4 w-4" />
							Approve
						</Button>
					</Card.Footer>
				</Card.Root>
			{/each}
		{/if}
	</div>
</div>
