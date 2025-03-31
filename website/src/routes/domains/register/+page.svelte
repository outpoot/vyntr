<script lang="ts">
	import DomainVerifyModal from '$lib/components/self/DomainVerifyModal.svelte';
	import Status from '$lib/components/self/Status.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { generateVerificationToken } from '$lib/utils/dns';

	let domain = $state('');
	let verificationToken = $state('');
	let error = $state('');
	let showModal = $state(false);
	let isValidDomain = $state(false);

	function normalizeDomain(input: string) {
		// remove any existing protocols
		let normalized = input.replace(/^https?:\/\//, '');
		// remove trailing slashes and whitespace
		return normalized.replace(/\/+$/, '').trim();
	}

	function validateDomain(input: string) {
		if (!input) return false;

		const normalized = normalizeDomain(input);

		const domainRegex = /^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/i;
		return domainRegex.test(normalized);
	}

	function handleInput(e: Event) {
		const target = e.target as HTMLInputElement;
		let value = target.value;

		value = value.replace(/^https?:\/\//, '');
		domain = value;
		isValidDomain = validateDomain(value);
		error = isValidDomain ? '' : 'Please enter a valid domain (e.g. example.com)';
	}

	function generateToken() {
		if (!isValidDomain) return;

		const fullDomain = `https://${normalizeDomain(domain)}`;
		verificationToken = generateVerificationToken(fullDomain);
		showModal = true;
	}
</script>

<div class="space-y-4 p-4">
	<Label class="text-xl font-bold">Register Your Domain</Label>
	<p class="text-sm text-muted-foreground">Add your domain to our registry and search index</p>

	<div class="flex items-end gap-2">
		<div class="w-full max-w-xl space-y-1">
			<Label>Domain to register</Label>
			<div class="flex items-center rounded-md border shadow-sm">
				<span
					class="flex items-center rounded-l-md border-r bg-muted/50 px-3 py-2.5 text-sm text-foreground/80"
				>
					https://
				</span>
				<Input
					value={domain}
					oninput={handleInput}
					placeholder="example.com"
					class="w-96 rounded-l-none border-0 text-base focus-visible:ring-0 focus-visible:ring-offset-0"
				/>
			</div>
		</div>
		<Button variant="default" onclick={generateToken} disabled={!isValidDomain}>Proceed</Button>
	</div>

	{#if error}
		<Status type="error" message={error} />
	{:else if domain && isValidDomain}
		<Status
			type="success"
			message="Valid domain format (will be registered as: https://{domain})"
		/>
	{/if}
</div>

<DomainVerifyModal bind:open={showModal} domain={`https://${domain}`} token={verificationToken} />
