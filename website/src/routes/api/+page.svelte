<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Card } from '$lib/components/ui/card';
	import { Key, Trash2, Plus, History, CircleDollarSign, Coins, ArrowRight } from 'lucide-svelte';
	import * as Dialog from '$lib/components/ui/dialog';
	import { toast } from 'svelte-sonner';
	import Codeblock from '$lib/components/self/Codeblock.svelte';
	import Status from '$lib/components/self/Status.svelte';
	import { LinkedChart, LinkedValue, LinkedLabel } from 'svelte-tiny-linked-charts';
	import { formatDateFriendly } from '$lib/utils';

	let { data } = $props();
	let apiKey = $state(null);
	let apiKeyId = $state<string | null>(data.apiKey?.id || null);
	let justCreated = $state(false);
	let credits = $state(data.apiKey?.remaining ?? 1000);

	const usageData = $state(data.usageData || {});
	const totalRequests = $derived<number>(
		Object.values(usageData).reduce((a: number, b: unknown) => a + Number(b), 0)
	);

	const creditPackages = [
		{ credits: 10_000, price: 10 },
		{ credits: 50_000, price: 45 },
		{ credits: 100_000, price: 80 }
	];

	let showDeleteConfirm = $state(false);
	let loading = $state(false);

	async function createKey() {
		loading = true;
		try {
			const response = await fetch('/api/keys', {
				method: 'POST'
			});
			const { id, key, remaining } = await response.json();
			apiKeyId = id;
			apiKey = key;
			credits = remaining;

			justCreated = true;
			toast.success('API key created');
		} catch (err) {
			toast.error('Failed to create API key');
		} finally {
			loading = false;
		}
	}

	async function deleteKey() {
		if (!apiKeyId) return;

		loading = true;
		try {
			await fetch(`/api/keys/${apiKeyId}`, {
				method: 'DELETE'
			});
			apiKey = null;
			apiKeyId = null;

			showDeleteConfirm = false;
			toast.success('API key deleted');
		} catch (err) {
			toast.error('Failed to delete API key');
		} finally {
			loading = false;
		}
	}
</script>

<div class="container mx-auto space-y-6 p-8">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold">API</h1>
			<p class="text-muted">Manage your API access and usage</p>
		</div>
	</div>

	<div class="grid gap-6 md:grid-cols-2">
		<Card class="p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] drop-shadow-md">
			<div class="flex flex-col gap-2">
				<div class="flex items-center gap-2">
					<Coins class="h-5 w-5 text-primary" />
					<h3 class="font-semibold">Credits</h3>
				</div>
				<div class="text-2xl font-bold">{credits.toLocaleString()}</div>
				<p class="text-sm text-muted">
					Every user gets 1,000 free credits to start. Each API call costs 1 credit.
				</p>
				<div class="mt-4 space-y-3">
					{#each creditPackages as pkg}
						<Button
							variant="outline"
							class="relative flex h-auto w-full flex-col gap-1 p-4 hover:border-primary"
							onclick={() => (window.location.href = `/premium?credits=${pkg.credits}`)}
						>
							<div class="flex w-full items-center justify-between">
								<span class="text-lg font-bold">
									{pkg.credits.toLocaleString()} credits
								</span>
								<ArrowRight class="h-4 w-4 text-muted" />
							</div>
							<div class="flex w-full items-center justify-between text-sm text-muted">
								<span>${pkg.price.toFixed(2)}</span>
								<span>${((pkg.price / pkg.credits) * 1000).toFixed(1)} per 1k credits</span>
							</div>
							{#if pkg.credits === 100_000}
								<span
									class="absolute -right-1 -top-1 rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground"
								>
									Best value
								</span>
							{/if}
						</Button>
					{/each}
				</div>
			</div>
		</Card>

		<Card class="p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] drop-shadow-md">
			<div class="flex flex-col gap-4">
				<div class="flex items-center justify-between">
					<div class="flex flex-col">
						<div class="flex items-center gap-2">
							<History class="h-5 w-5 text-primary" />
							<h3 class="font-semibold">Usage</h3>
						</div>
						<div class="text-2xl font-bold">
							{totalRequests.toLocaleString()} requests
						</div>
						<p class="text-sm text-muted">Last 30 days</p>
					</div>
				</div>

				{#if Object.values(usageData).every((x) => x === 0)}
					<div class="flex h-[280px] items-center justify-center">
						<p class="-rotate-12 text-4xl font-medium text-muted">No data</p>
					</div>
				{:else}
					<LinkedChart
						data={usageData}
						barMinWidth={15}
						width={600}
						gap={4}
						height={280}
						fill="hsl(var(--primary))"
						fadeOpacity={0.2}
						uid="usage"
						linked="usage-data"
					/>

					<div class="flex items-center justify-between text-sm text-muted">
						<LinkedLabel
							linked="usage-data"
							empty="Hover to see details"
							transform={(key) =>
								key ? formatDateFriendly(new Date(key).getTime()) + ' | ' : 'Hover to see details'}
						/>
						<LinkedValue
							uid="usage"
							empty=""
							transform={(value) => (value ? `${value.toLocaleString()} requests` : '')}
						/>
					</div>
				{/if}
			</div>
		</Card>
	</div>

	<Card class="p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] drop-shadow-md">
		<div class="flex items-start justify-between">
			<div>
				<h2 class="text-xl font-bold">API Key</h2>
				<p class="text-sm text-muted">Use this key to authenticate your API requests</p>
			</div>
			{#if apiKeyId}
				<div class="flex gap-2">
					<Button
						variant="destructive"
						onclick={() => (showDeleteConfirm = true)}
						disabled={loading}
					>
						<Trash2 class="h-4 w-4" />
						Delete
					</Button>
				</div>
			{/if}
		</div>

		{#if apiKey && justCreated}
			<div class="mt-4 flex max-w-[800px] flex-col gap-2">
				<Codeblock text={apiKey} />
				<Status
					type="warning"
					message="This is the only time your full API key will be shown. If you lose it, you'll need to create a new one."
					maxWidth={true}
				/>
			</div>
		{:else if !apiKey && data.apiKey && apiKeyId}
			<div class="mt-4 flex max-w-[800px] flex-col gap-2">
				<Codeblock text={`${data.apiKey.prefix}${'x'.repeat(64)}`} displayOnly={true} />
				<p class="mt-2 text-xs text-muted">
					For security reasons, the full API key is only shown once upon creation. If you've lost
					your key, you'll need to delete this one and create a new one.
				</p>
			</div>
		{:else}
			<div class="mt-4">
				<Button onclick={createKey} disabled={loading}>
					<Key class="h-4 w-4" />
					Create API Key
				</Button>
			</div>
		{/if}
	</Card>

	<Card class="p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] drop-shadow-md">
		<h2 class="text-xl font-bold">Documentation</h2>
		<div class="mt-4 space-y-6">
			<div class="flex flex-col gap-2">
				<h3 class="font-medium">Endpoint</h3>
				<p class="text-sm text-muted">Make GET requests to:</p>
				<Codeblock text="https://vyntr.com/api/search?q=your query" displayOnly={true} />
			</div>

			<div class="flex flex-col gap-2">
				<h3 class="font-medium">Authentication</h3>
				<p class="text-sm text-muted">Include your API key in the Authorization header:</p>
				<Codeblock
					text={`curl -X GET "https://vyntr.com/api/search?q=hello" -H "Authorization: Bearer ${data.apiKey?.prefix ?? 'vyntr_'}your_api_key"`.trim()}
					displayOnly={true}
				/>
			</div>

			<div class="flex flex-col gap-2">
				<h3 class="font-medium">Example Response</h3>
				<p class="text-sm text-muted">The API returns a JSON object containing search results:</p>
				<Codeblock
					text={`
{
  "web": [
    {
      "title": "Example Result",
      "url": "https://example.com",
      "preview": "Preview text..."
    }
  ],
  "bliptext": {
    "type": "bliptext",
    "article": { ... }
  },
  "date": null,
  "word": null,
  "currency": null,
  "unitConversion": null
}
					`.trim()}
					displayOnly={true}
				/>
			</div>

			<div>
				<h3 class="font-medium">Rate Limiting</h3>
				<p class="mt-1 text-sm text-muted">
					For each call, a credit is deducted from your balance. If you exceed your limit, you'll
					receive a 429 error. You can check your usage in the dashboard. <br /> <br />If you run
					out of credits, you can purchase more in the dashboard.
				</p>
			</div>
		</div>
	</Card>
</div>

<Dialog.Root bind:open={showDeleteConfirm}>
	<Dialog.Content>
		<Dialog.Header>
			<Dialog.Title>Delete API Key</Dialog.Title>
			<Dialog.Description>
				Are you sure you want to delete your API key? This action cannot be undone.
			</Dialog.Description>
		</Dialog.Header>
		<Dialog.Footer>
			<Button variant="ghost" onclick={() => (showDeleteConfirm = false)}>Cancel</Button>
			<Button variant="destructive" onclick={deleteKey}>Delete</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
