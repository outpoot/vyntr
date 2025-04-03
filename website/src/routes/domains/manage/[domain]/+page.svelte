<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { ArrowUpRight, Users, Globe } from 'lucide-svelte';
	import * as Select from '$lib/components/ui/select';
	import Status from '$lib/components/self/Status.svelte';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import UnsavedChanges from '$lib/components/self/UnsavedChanges.svelte';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import { WEBSITE_CATEGORIES } from '$lib/constants';
	import { Badge } from '$lib/components/ui/badge';

	let { data } = $props();
	let hasChanges = $state(false);
	let currentValues = $state({
		status: data.domain.status,
		description: data.domain.description ?? '',
		category: data.domain.category,
		tags: data.domain.tags ?? []
	});

	let newTag = $state('');

	function handleVisibilityChange(value: string) {
		currentValues.status = value;
		hasChanges = true;
	}

	function handleDescriptionChange(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		currentValues.description = target.value;
		hasChanges = true;
	}

	function handleCategoryChange(value: string) {
		currentValues.category = value;
		hasChanges = true;
	}

	function addTag(e: KeyboardEvent) {
		if (e.key === 'Enter' && newTag.trim()) {
			currentValues.tags = [...currentValues.tags, newTag.trim()];
			newTag = '';
			hasChanges = true;
		}
	}

	function removeTag(tag: string) {
		currentValues.tags = currentValues.tags.filter((t) => t !== tag);
		hasChanges = true;
	}

	async function handleSave() {
		// TODO: Implement save
		hasChanges = false;
	}

	function handleDiscard() {
		currentValues.status = data.domain.status;
		currentValues.description = data.domain.description ?? '';
		currentValues.category = data.domain.category;
		currentValues.tags = data.domain.tags ?? [];
		hasChanges = false;
	}

	const stats = `${data.domain.monthlyVisits.toLocaleString()} visits · ${data.domain.upvotes.toLocaleString()} upvotes · ${data.domain.downvotes.toLocaleString()} downvotes`;

	const visibilityOptions = [
		{ label: 'Unlisted', value: 'unlisted' },
		{ label: 'Public', value: 'public' }
	];

	const isVisibilityLocked = currentValues.status === 'pending' || !data.domain.isVerified;

	const visibilityHint = !data.domain.isVerified
		? 'Verify your domain ownership first'
		: currentValues.status === 'pending'
			? 'Your site is being reviewed'
			: 'Control who can see your website';
</script>

<div class="container mx-auto space-y-6 p-6">
	<div class="flex items-center justify-between">
		<div class="space-y-1">
			<Breadcrumb.Root>
				<Breadcrumb.List class="text-muted">
					<Breadcrumb.Item>
						<Breadcrumb.Link href="/domains/list">Domains</Breadcrumb.Link>
					</Breadcrumb.Item>
					<Breadcrumb.Separator />
					<Breadcrumb.Item>
						<Breadcrumb.Page>Manage</Breadcrumb.Page>
					</Breadcrumb.Item>
				</Breadcrumb.List>
			</Breadcrumb.Root>
			<h1 class="text-2xl font-bold">{data.domain.domain}</h1>
			<div class="flex items-center gap-1 text-sm text-muted">
				<Users class="h-4 w-4" />
				<span>{stats}</span>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<Button variant="outline" onclick={() => window.open(data.domain.domain, '_blank')}>
				<Globe class="h-4 w-4" />
				<span>Visit site</span>
				<ArrowUpRight class="h-4 w-4" />
			</Button>
			{#if data.domain.status === 'unlisted'}
				<Button>Publish site</Button>
			{:else}
				<Button variant="outline">Edit details</Button>
			{/if}
		</div>
	</div>

	{#if data.domain.status === 'unlisted'}
		<Status
			type="warning"
			message="Your site is not yet published. Once published, it will be reviewed and listed in our registry."
			maxWidth={false}
		/>
	{/if}

	<div class="rounded-lg border bg-card p-4">
		<h2 class="text-lg font-semibold">Details</h2>
		<div class="mt-4 space-y-4">
			<div>
				<div class="font-medium">Description</div>
				<div class="text-sm text-muted">Tell visitors what your site is about</div>
				<Textarea
					value={currentValues.description}
					onchange={handleDescriptionChange}
					placeholder="A brief description of your website..."
					class="mt-2"
				/>
			</div>

			<div>
				<div class="font-medium">Category</div>
				<div class="text-sm text-muted mb-2">Choose the best fit for your site</div>
				<Select.Root
					type="single"
					value={currentValues.category}
					onValueChange={handleCategoryChange}
				>
					<Select.Trigger>
						<span class="capitalize">
							{WEBSITE_CATEGORIES.find((c) => c.value === currentValues.category)?.label ??
								'Select category'}
						</span>
					</Select.Trigger>
					<Select.Content>
						{#each WEBSITE_CATEGORIES as category}
							<Select.Item value={category.value}>
								{category.label}
							</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>

			<div>
				<div class="font-medium">Tags</div>
				<div class="text-sm text-muted">Add keywords to help others discover your site</div>
				<div class="mt-2 flex flex-wrap gap-2">
					{#each currentValues.tags as tag}
						<Badge>
							<span class="flex items-center gap-1">
								{tag}
								<button
									onclick={() => removeTag(tag)}
									class="ml-1 rounded-full p-0.5 hover:bg-primary/10"
								>
									<span class="sr-only">Remove {tag}</span>
									×
								</button>
							</span>
						</Badge>
					{/each}
					<Input
						bind:value={newTag}
						onkeydown={addTag}
						placeholder="Press Enter to add tag"
						class="!w-auto flex-1"
					/>
				</div>
			</div>
		</div>
	</div>

	<div class="rounded-lg border bg-card p-4">
		<h2 class="text-lg font-semibold">Status</h2>
		<div class="mt-4 space-y-4">
			<div class="flex items-center justify-between">
				<div>
					<div class="font-medium">Visibility</div>
					<div class="text-sm text-muted">{visibilityHint}</div>
				</div>
				<Select.Root
					type="single"
					value={currentValues.status}
					onValueChange={handleVisibilityChange}
					disabled={isVisibilityLocked}
				>
					<Select.Trigger class="w-[150px]">
						<span class="capitalize">{currentValues.status}</span>
					</Select.Trigger>
					<Select.Content>
						{#each visibilityOptions as option}
							<Select.Item value={option.value} label={option.label} disabled={isVisibilityLocked}>
								{option.label}
							</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>
		</div>
	</div>

	{#if hasChanges}
		<UnsavedChanges onSave={handleSave} onDiscard={handleDiscard} />
	{/if}

	<div class="rounded-lg border border-destructive/50 bg-destructive/5 p-4">
		<h2 class="text-lg font-semibold">Danger Zone</h2>
		<div class="mt-4">
			<Button variant="destructive">Delete domain</Button>
		</div>
	</div>
</div>
