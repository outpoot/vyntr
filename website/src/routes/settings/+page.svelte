<script lang="ts">
	import AuthGate from '$lib/components/self/AuthGate.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Card } from '$lib/components/ui/card';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Select, SelectContent, SelectItem, SelectTrigger } from '$lib/components/ui/select';
	import { toast } from 'svelte-sonner';
	import User from 'lucide-svelte/icons/user';
	import CreditCard from 'lucide-svelte/icons/credit-card';
	import Globe from 'lucide-svelte/icons/globe';
	import Download from 'lucide-svelte/icons/download';
	import Shield from 'lucide-svelte/icons/shield';
	import Trash2 from 'lucide-svelte/icons/trash-2';
	import Search from 'lucide-svelte/icons/search';
	import { subscriptionStore } from '$lib/stores/subscription';
	import { USER_DATA } from '$lib/stores/userdata';
	import { Label } from '$lib/components/ui/label';
	import { Switch } from '$lib/components/ui/switch';

	const buttonClass = 'border bg-card text-card-foreground shadow-custom-inset hover:bg-card-hover';

	let { data } = $props();
	let showDeleteConfirm = $state(false);
	let loading = $state(false);

	const languages = [
		{ value: 'en', label: 'English' },
		{ value: 'es', label: 'Spanish' },
		{ value: 'fr', label: 'French' },
		{ value: 'de', label: 'German' },
		{ value: 'it', label: 'Italian' }
	];

	let selectedLanguage = $state(data.preferences.preferredLanguage);

	// Search features
	let safeSearch = $state(data.preferences.safeSearch);
	let autocomplete = $state(data.preferences.autocomplete);
	let instantResults = $state(data.preferences.instantResults);
	let aiSummarise = $state(data.preferences.aiSummarise);

	// Privacy settings
	let anonymousQueries = $state(data.preferences.anonymousQueries);
	let analyticsEnabled = $state(data.preferences.analyticsEnabled);
	let aiPersonalization = $state(data.preferences.aiPersonalization);

	$effect(() => {
		subscriptionStore.checkStatus();
	});

	function formatUserDataForExport() {
		const exportData = {
			profile: {
				id: $USER_DATA?.id,
				name: $USER_DATA?.name,
				email: $USER_DATA?.email,
				image: $USER_DATA?.image,
				isAdmin: $USER_DATA?.isAdmin,
				isBanned: $USER_DATA?.isBanned,
				banReason: $USER_DATA?.banReason
			},
			preferences: {
				language: selectedLanguage,
				search: {
					safeSearch,
					autocomplete,
					instantResults,
					aiSummarise
				},
				privacy: {
					anonymousQueries,
					analyticsEnabled,
					aiPersonalization
				}
			},
			subscription: {
				type: $subscriptionStore.isActive ? 'Pro' : 'Free',
				isActive: $subscriptionStore.isActive
			},
			websites: data.websites,
			apiKeys: data.apiKeys,
			apiUsage: data.apiUsage,
			messageUsage: data.messageUsage,
			exportDate: new Date().toISOString()
		};

		return JSON.stringify(exportData, null, 2);
	}

	async function downloadData() {
		loading = true;
		try {
			const data = formatUserDataForExport();
			const blob = new Blob([data], { type: 'application/json' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			const timestamp = new Date().toISOString().split('T')[0];
			a.href = url;
			a.download = `vyntr-data-${timestamp}.json`;
			document.body.appendChild(a);
			a.click();
			URL.revokeObjectURL(url);
			document.body.removeChild(a);
			toast.success('Data downloaded successfully');
		} catch (err) {
			console.error('Error downloading data:', err);
			toast.error('Failed to download data');
		} finally {
			loading = false;
		}
	}

	async function deleteAccount() {
		loading = true;
		try {
			await fetch('/api/user', { method: 'DELETE' });
			showDeleteConfirm = false;
			window.location.href = '/';
		} catch (err) {
			toast.error('Failed to delete account');
			loading = false;
		}
	}

	async function updateLanguage(lang: string) {
		try {
			await fetch('/api/user/preferences', {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ preferredLanguage: lang })
			});
			selectedLanguage = lang;
			toast.success('Language preference updated');
		} catch (err) {
			toast.error('Failed to update language preference');
		}
	}

	async function updateSearchFeature(feature: string, value: boolean) {
		try {
			await fetch('/api/user/preferences', {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ [feature]: value })
			});
			toast.success('Preference updated');
		} catch (err) {
			toast.error('Failed to update preference');
		}
	}
</script>

<AuthGate
	title="Account Settings"
	description="Sign in to manage your account settings and preferences."
>
	<div class="container mx-auto space-y-6 p-8">
		<div class="flex flex-col items-center justify-center">
			<h1 class="text-3xl font-bold">Settings</h1>
			<p class="text-muted">Manage your account preferences</p>
		</div>

		<Card class="p-6 shadow-custom-inset drop-shadow-md">
			<div class="flex items-center gap-2">
				<User class="h-5 w-5 text-primary" />
				<h2 class="text-xl font-bold">Profile</h2>
			</div>
			<div class="mt-4 space-y-4">
				<div>
					<Label class="text-sm font-medium">Email</Label>
					<p class="text-muted">{$USER_DATA?.email}</p>
				</div>
				<div>
					<Label class="text-sm font-medium">Name</Label>
					<p class="text-muted">{$USER_DATA?.name}</p>
				</div>
			</div>
		</Card>

		<Card class="p-6 shadow-custom-inset drop-shadow-md">
			<div class="flex items-center gap-2">
				<CreditCard class="h-5 w-5 text-primary" />
				<h2 class="text-xl font-bold">Subscription</h2>
			</div>
			<div class="mt-4 space-y-4">
				<p class="text-muted">
					Current plan: <span class="font-medium"
						>{$subscriptionStore.isActive ? 'Pro' : 'Free'}</span
					>
				</p>
				<div class="space-x-2">
					<Button class={buttonClass} href="/api/auth/portal">Manage Subscription</Button>
					<Button class={buttonClass} href="/api">View API Usage</Button>
				</div>
			</div>
		</Card>

		<Card class="p-6 shadow-custom-inset drop-shadow-md">
			<div class="flex items-center gap-2">
				<Globe class="h-5 w-5 text-primary" />
				<h2 class="text-xl font-bold">Search Preferences</h2>
			</div>
			<div class="mt-4 max-w-md space-y-4">
				<div class="space-y-2">
					<Label class="text-sm font-medium">Preferred Language</Label>
					<Select type="single" bind:value={selectedLanguage} onValueChange={updateLanguage}>
						<SelectTrigger
							>{languages.find((l) => l.value === selectedLanguage)?.label ||
								'Select language'}</SelectTrigger
						>
						<SelectContent>
							{#each languages as lang}
								<SelectItem value={lang.value}>{lang.label}</SelectItem>
							{/each}
						</SelectContent>
					</Select>
					<p class="text-sm text-muted">Search results will prioritize content in this language</p>
				</div>
			</div>
		</Card>

		<Card class="p-6 shadow-custom-inset drop-shadow-md">
			<div class="flex items-center gap-2">
				<Search class="h-5 w-5 text-primary" />
				<h2 class="text-xl font-bold">Search Features</h2>
			</div>
			<div class="mt-4 space-y-6">
				<div class="flex items-center justify-between">
					<div>
						<Label class="text-sm font-medium">Safe Search</Label>
						<p class="text-sm text-muted">Blur NSFW content in search results (coming soon)</p>
					</div>
					<Switch
						checked={safeSearch}
						disabled
						onCheckedChange={(v) => updateSearchFeature('safeSearch', v)}
					/>
				</div>

				<div class="flex items-center justify-between">
					<div>
						<Label class="text-sm font-medium">Autocomplete</Label>
						<p class="text-sm text-muted">Show search suggestions as you type</p>
					</div>
					<Switch
						checked={autocomplete}
						onCheckedChange={(v) => updateSearchFeature('autocomplete', v)}
					/>
				</div>

				<div class="flex items-center justify-between">
					<div>
						<Label class="text-sm font-medium">Instant Results</Label>
						<p class="text-sm text-muted">Enable !bang commands for quick searches</p>
					</div>
					<Switch
						checked={instantResults}
						onCheckedChange={(v) => updateSearchFeature('instantResults', v)}
					/>
				</div>

				<div class="flex items-center justify-between">
					<div>
						<Label class="text-sm font-medium">AI Summaries</Label>
						<p class="text-sm text-muted">Show AI-generated summaries in search results</p>
					</div>
					<Switch
						checked={aiSummarise}
						onCheckedChange={(v) => updateSearchFeature('aiSummarise', v)}
					/>
				</div>
			</div>
		</Card>

		<Card class="p-6 shadow-custom-inset drop-shadow-md">
			<div class="flex items-center gap-2">
				<Shield class="h-5 w-5 text-primary" />
				<h2 class="text-xl font-bold">Privacy & Data</h2>
			</div>
			<div class="mt-4 space-y-6">
				<div class="flex items-center justify-between">
					<div>
						<Label class="text-sm font-medium">Anonymous Search Logging</Label>
						<p class="text-sm text-muted">Help improve search results by sharing anonymous data</p>
					</div>
					<Switch
						checked={anonymousQueries}
						onCheckedChange={(v) => updateSearchFeature('anonymousQueries', v)}
					/>
				</div>

				<div class="flex items-center justify-between">
					<div>
						<Label class="text-sm font-medium">Analytics</Label>
						<p class="text-sm text-muted">Allow anonymous usage data collection via Plausible</p>
					</div>
					<Switch
						checked={analyticsEnabled}
						onCheckedChange={(v) => updateSearchFeature('analyticsEnabled', v)}
					/>
				</div>

				<div class="flex items-center justify-between">
					<div>
						<Label class="text-sm font-medium">AI Personalization</Label>
						<p class="text-sm text-muted">
							Allow Yappatron AI to learn from your interactions (coming soon)
						</p>
					</div>
					<Switch
						checked={aiPersonalization}
						disabled
						onCheckedChange={(v) => updateSearchFeature('aiPersonalization', v)}
					/>
				</div>

				<div class="mt-6 flex flex-wrap gap-4">
					<Button class={buttonClass} onclick={downloadData} disabled={loading}>
						<Download class="h-4 w-4" />
						Download My Data
					</Button>
					<Button variant="destructive" onclick={() => (showDeleteConfirm = true)}>
						<Trash2 class="h-4 w-4" />
						Delete Account
					</Button>
				</div>
			</div>
		</Card>
	</div>

	<Dialog.Root bind:open={showDeleteConfirm}>
		<Dialog.Content>
			<Dialog.Header>
				<Dialog.Title>Delete Account</Dialog.Title>
				<Dialog.Description>
					Are you sure you want to delete your account? This action cannot be undone and will
					permanently erase all your data.
				</Dialog.Description>
			</Dialog.Header>
			<Dialog.Footer>
				<Button variant="ghost" onclick={() => (showDeleteConfirm = false)}>Cancel</Button>
				<Button variant="destructive" onclick={deleteAccount} disabled={loading}>Delete</Button>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Root>
</AuthGate>
