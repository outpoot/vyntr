<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import * as Select from '$lib/components/ui/select/index.js';

	import { ExternalLink } from 'lucide-svelte';

	import { onDestroy } from 'svelte';
	import { goto } from '$app/navigation';

	import Status from './Status.svelte';
	import Step from './Step.svelte';
	import Codeblock from './Codeblock.svelte';

	// Props
	let { domain = '', token = '', open = $bindable(false) } = $props();

	// State
	let provider = $state('any');
	let copied = $state(false);
	let verifying = $state(false);
	let verified = $state(false);
	let nextRetryTime = $state<number | null>(null);
	let remainingTime = $state(0);
	let cooldownInterval: number | undefined = $state();

	// Constants
	const domainProviders = [
		{ label: 'Cloudflare', value: 'cloudflare' },
		{ label: 'Other Domain Registrar', value: 'any' }
	];
	const registrarExamples = ['GoDaddy', 'Namecheap', 'Cloudflare', 'Porkbun', 'others'];

	const triggerContent = $derived(
		domainProviders.find((p) => p.value === provider)?.label ?? 'Select provider'
	);

	function copyToClipboard() {
		navigator.clipboard.writeText(token);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}

	function updateRemainingTime() {
		if (!nextRetryTime) return;
		const now = Date.now();
		remainingTime = Math.max(0, Math.ceil((nextRetryTime - now) / 1000));

		if (remainingTime === 0) {
			clearInterval(cooldownInterval);
			cooldownInterval = undefined;
			nextRetryTime = null;
		}
	}

	async function verifyDomain() {
		if (verifying || nextRetryTime) return;

		try {
			verifying = true;
			const response = await fetch('/api/domains/verify', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ domain, verificationToken: token })
			});

			if (response.ok) {
				verified = true;
			} else {
				nextRetryTime = Date.now() + 5000;
				updateRemainingTime();
				cooldownInterval = setInterval(updateRemainingTime, 100);
			}
		} catch (error) {
			console.error('Verification failed:', error);
			nextRetryTime = Date.now() + 5000;
			updateRemainingTime();
			cooldownInterval = setInterval(updateRemainingTime, 100);
		} finally {
			verifying = false;
		}
	}

	function handleClose() {
		open = false;
		if (verified) {
			goto('/domains/list');
		}
	}

	onDestroy(() => {
		clearInterval(cooldownInterval);
	});
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Connect Your Domain</Dialog.Title>
			<Dialog.Description>Setting up: {domain}</Dialog.Description>
		</Dialog.Header>

		<div class="space-y-6 py-6">
			<div class="space-y-4 rounded-lg border bg-card p-5 shadow-sm">
				<!-- STEP 1 -->
				<Step number={1} title="Where is your domain managed?">
					<div class="mb-5 w-[220px]">
						<Select.Root type="single" bind:value={provider}>
							<Select.Trigger class="w-full">{triggerContent}</Select.Trigger>
							<Select.Content>
								<Select.Group>
									{#each domainProviders as dp (dp.value)}
										<Select.Item value={dp.value} label={dp.label}>
											{dp.label}
										</Select.Item>
									{/each}
								</Select.Group>
							</Select.Content>
						</Select.Root>
					</div>
				</Step>

				<!-- CF PROVIDER -->
				{#if provider === 'cloudflare'}
					<!-- STEP 2 -->
					<Step number={2} title="Connect with Cloudflare">
						<p class="text-sm leading-relaxed">
							We'll securely connect to your Cloudflare account to automatically verify your domain.
						</p>
						<div class="mt-2 text-xs text-muted">
							The fastest way to get set up - no manual DNS changes needed.
						</div>
					</Step>
					<!-- STEP 3 -->
					<Step number={3} title="Completing verification">
						<p class="text-sm leading-relaxed">
							Hang tight while we verify your domain. This usually takes less than a minute.
						</p>
					</Step>
				{:else}
					<!-- OTHER PROVIDER -->
					<!-- STEP 2 -->
					<Step number={2} title="Access your domain settings">
						<p class="mb-2 text-sm">Sign in to your domain registrar:</p>
						<div class="flex flex-wrap gap-2 text-xs">
							{#each registrarExamples as registrar}
								<span
									class="inline-flex select-none items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium"
								>
									{registrar}
								</span>
							{/each}
						</div>
					</Step>
					<!-- STEP 3 -->
					<Step number={3} title="Add verification record">
						<p class="mb-2 text-sm leading-relaxed">
							Create a new TXT record in your DNS settings for <span class="font-bold"
								>{domain}</span
							>:
						</p>

						<Codeblock text={token} onCopy={copyToClipboard} isSuccess={copied} />

						<div class="mt-2 text-xs text-muted-">
							DNS changes may take some time to update - typically a few minutes, but could be up to
							24 hours.
						</div>
					</Step>
					<!-- STEP 4 -->
					<Step number={4} title="Complete verification">
						<p class="text-sm leading-relaxed">
							Once added, we'll check your DNS records to confirm ownership.
						</p>
					</Step>
				{/if}
			</div>

			{#if verified}
				<Status
					type="success"
					message="Domain verified successfully! You can now close this window."
				/>
			{/if}
		</div>

		<Dialog.Footer class="gap-3">
			<Button variant="outline" onclick={handleClose}>
				{verified ? 'Close' : 'Cancel'}
			</Button>
			{#if !verified}
				<Button
					variant="default"
					class="gap-2"
					disabled={verifying || Boolean(nextRetryTime)}
					onclick={() => (provider === 'cloudflare' ? null : verifyDomain())}
				>
					{#if verifying}
						Checking...
					{:else if nextRetryTime}
						Retry in {remainingTime}s
					{:else}
						{provider === 'cloudflare' ? 'Connect Cloudflare' : 'Check Verification'}
					{/if}
					{#if provider === 'cloudflare'}
						<ExternalLink class="h-4 w-4" />
					{/if}
				</Button>
			{/if}
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
