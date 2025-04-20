<script lang="ts">
	import { Separator } from '$lib/components/ui/separator';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import ShieldCheck from 'lucide-svelte/icons/shield-check';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	const LAST_UPDATED = 'April 20, 2025';
	const CONTACT_EMAIL = 'contact@outpoot.com';
</script>

<svelte:head>
	<title>Privacy Policy: Vyntr</title>
	<meta
		name="description"
		content="Learn how Vyntr protects your privacy while searching the web."
	/>
	<meta name="keywords" content="privacy, policy, data protection, vyntr, search engine" />
	<meta property="og:title" content="Privacy Policy: Vyntr" />
	<meta
		property="og:description"
		content="Learn how Vyntr protects your privacy while searching the web."
	/>
	<meta property="og:type" content="website" />
	<meta property="og:url" content={page.url.href} />
</svelte:head>

<div class="container mx-auto max-w-4xl py-10">
	<Card.Root class="p-6">
		<div class="mb-8 flex items-center gap-3">
			<ShieldCheck class="h-10 w-10 text-primary" />
			<div>
				<h1 class="text-4xl font-bold">Privacy Policy</h1>
				<p class="text-muted-foreground">
					Last updated: {LAST_UPDATED}
				</p>
			</div>
		</div>

		<Separator class="my-6" />

		<div class="space-y-2">
			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">1. Our Privacy Commitment</h2>
				<p class="mb-4">
					At Vyntr, we believe privacy is a fundamental right. Our search engine is built with
					privacy at its core, ensuring that your search activity remains private and secure. We
					minimize data collection and provide transparent control over any data we do collect.
				</p>
				<p>This privacy policy explains how we handle your data when you use our service.</p>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">2. Information We Collect</h2>
				<div class="space-y-4">
					<div>
						<h3 class="mb-2 text-lg font-medium">2.1 Search Data</h3>
						<p class="mb-4">When you perform a search:</p>
						<ul class="ml-6 list-disc space-y-2">
							<li>Search queries are processed anonymously</li>
							<li>No IP addresses are stored with search queries</li>
							<li>Search history is not saved by default</li>
							<li>Temporary processing data is immediately deleted after your search</li>
						</ul>
					</div>

					<div>
						<h3 class="mb-2 text-lg font-medium">2.2 Account Information</h3>
						<p class="mb-4">If you create an account, we store:</p>
						<ul class="ml-6 list-disc space-y-2">
							<li>Email address</li>
							<li>Username</li>
							<li>Account preferences</li>
						</ul>
						<p class="mt-2">
							Account data is retained as long as your account is active. You can delete your
							account at any time.
						</p>
					</div>
				</div>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">3. How We Use Your Data</h2>
				<p class="mb-4">We use collected data solely for:</p>
				<ul class="ml-6 list-disc space-y-2">
					<li>Providing search results</li>
					<li>Maintaining account functionality</li>
					<li>Improving search accuracy</li>
					<li>Fraud prevention and security</li>
				</ul>
				<p class="mt-4">
					We never sell your data or share it with third parties for advertising purposes.
				</p>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">4. AI Data Handling</h2>
				<p class="mb-4">When using our AI-powered features:</p>
				<ul class="ml-6 list-disc space-y-2">
					<li>AI queries are processed separately from regular searches</li>
					<li>No personal information is shared with AI providers or used to train models</li>
					<li>AI interactions are anonymized and temporary</li>
					<li>You can opt-out of AI features at any time</li>
				</ul>
				<p class="mt-4">
					Our AI features are provided through Google Gemini or Groq's APIs, and their respective
					privacy policies apply to the processing of AI queries.
				</p>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">5. Cookie Policy</h2>
				<p class="mb-4">
					We use only essential cookies that are necessary for the website to function. These
					cookies do not track you across websites.
				</p>
				<p>Required cookies include:</p>
				<ul class="ml-6 list-disc space-y-2">
					<li>Session management</li>
					<li>Security tokens</li>
					<li>User preferences</li>
				</ul>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">6. Your Privacy Rights</h2>
				<p class="mb-4">You have the right to:</p>
				<ul class="ml-6 list-disc space-y-2">
					<li>Access your personal data</li>
					<li>Erase your personal data</li>
					<li>Restrict the processing of your personal data</li>
				</ul>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">7. Data Security</h2>
				<p class="mb-4">
					We implement appropriate technical and organizational measures to protect your personal
					data against unauthorized access, disclosure, alteration, or destruction. These measures
					include encryption, firewalls, and access controls.
				</p>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">8. International Data Transfers</h2>
				<p class="mb-4">
					Your personal data may be transferred to and processed in countries outside the EU. We
					will only transfer your personal data to countries that provide an adequate level of data
					protection, or where we have put in place appropriate safeguards, such as standard
					contractual clauses.
				</p>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">9. Updates to Privacy Policy</h2>
				<p class="mb-4">
					We may update this privacy policy to reflect changes in our practices or for legal
					reasons. We will notify you of any material changes via email or through our website.
				</p>
			</Card.Content>

			<div class="text-sm text-muted-foreground">
				<p>Last Updated: {LAST_UPDATED}</p>
				<p>Contact: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
			</div>
		</div>

		<Separator class="my-8" />

		<div class="flex justify-center">
			<Button variant="outline" size="lg" onclick={() => goto('/legal/terms')}>
				Read our Terms of Service →
			</Button>
		</div>
	</Card.Root>
</div>
