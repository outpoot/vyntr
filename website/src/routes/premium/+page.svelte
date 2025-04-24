<script lang="ts">
	import { Card } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import Check from 'lucide-svelte/icons/check';
	import Sparkles from 'lucide-svelte/icons/sparkles';
	import MessageSquare from 'lucide-svelte/icons/message-square';
	import Zap from 'lucide-svelte/icons/zap';
	import Crown from 'lucide-svelte/icons/crown';
	import { subscriptionStore } from '$lib/stores/subscription';
    import { USER_DATA } from '$lib/stores/userdata';
	import { toast } from 'svelte-sonner';

	const benefits = [
		'150 messages per day with Yappatron AI',
		'Priority response time',
		'Higher website submission limits',
		'Priority website verification',
		'Early access to new features',
		'Support the development of Vyntr :)'
	];

	$effect(() => {
		subscriptionStore.checkStatus();
	});

	const comparisons = [
		{
			feature: 'Daily AI Messages',
			free: '15 messages',
			premium: '150 messages'
		},
		{
			feature: 'Response Priority',
			free: 'Standard',
			premium: 'Priority'
		},
		{
			feature: 'Website Submissions',
			free: '20',
			premium: '50'
		},
		{
			feature: 'Website Verification',
			free: 'Standard queue',
			premium: 'Priority queue'
		}
	];
</script>

<div class="container mx-auto px-4 py-16 sm:px-6 lg:px-8">
	<div class="text-center">
		<div class="flex items-center justify-center gap-2">
			<Crown class="h-8 w-8 text-primary" />
			<h1 class="text-4xl font-bold">Premium Experience</h1>
		</div>
		<p class="mt-4 text-xl text-muted-foreground">
			Unlock the full potential of Vyntr with Premium
		</p>
	</div>

	<div class="mt-16 grid gap-8 lg:grid-cols-2">
		<Card
			class="relative overflow-hidden rounded-xl p-8 shadow-custom-inset"
		>
			<div class="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-primary/10 blur-3xl"></div>
			<div class="relative">
				{#if !$subscriptionStore.isActive}
					<div
						class="absolute -right-2 -top-2 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground shadow-sm"
					>
						Current Plan
					</div>
				{/if}
				<h3 class="text-2xl font-bold">Free</h3>
				<p class="mt-2 text-muted-foreground">Get started with basic features</p>
				<div class="mt-6">
					<span class="text-3xl font-bold">$0</span>
					<span class="text-muted-foreground">/month</span>
				</div>
				<ul class="mt-8 space-y-4">
					<li class="flex items-center gap-2">
						<MessageSquare class="h-5 w-5 text-muted-foreground" />
						<span>5 messages per day with Yappatron AI</span>
					</li>
					<li class="flex items-center gap-2">
						<Zap class="h-5 w-5 text-muted-foreground" />
						<span>Standard response time</span>
					</li>
				</ul>
			</div>
		</Card>

		<Card
			class="relative overflow-hidden rounded-xl border-primary bg-primary/5 p-8 shadow-custom-inset "
		>
			<div class="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-primary/20 blur-3xl"></div>
			<div class="relative">
				{#if $subscriptionStore.isActive}
					<div
						class="absolute -right-2 -top-2 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground shadow-sm"
					>
						Current Plan
					</div>
				{/if}
				<div class="inline-flex items-center rounded-full bg-primary/10 px-3 py-1 shadow-sm">
					<Sparkles class="mr-1 h-4 w-4 text-primary" />
					<span class="text-sm font-medium text-primary">Most Popular</span>
				</div>
				<h3 class="mt-4 text-2xl font-bold">Premium</h3>
				<p class="mt-2 text-muted-foreground">Enhanced features for real sigmas</p>
				<div class="mt-6">
					<span class="text-3xl font-bold">$4</span>
					<span class="text-muted-foreground">/month</span>
				</div>
				<ul class="mt-8 space-y-4">
					{#each benefits as benefit}
						<li class="flex items-center gap-2">
							<Check class="h-5 w-5 text-primary" />
							<span>{benefit}</span>
						</li>
					{/each}
				</ul>
				<Button
					class="mt-8 w-full"
					href={!$USER_DATA 
						? undefined 
						: ($subscriptionStore.isActive 
							? '/api/auth/portal' 
							: '/api/auth/checkout/premium')}
					onclick={!$USER_DATA ? () => toast.error('Please sign in to upgrade') : undefined}
					data-polar-checkout={$USER_DATA}
					data-polar-checkout-theme
				>
					{!$USER_DATA 
						? 'Sign in to upgrade' 
						: ($subscriptionStore.isActive 
							? 'Manage Subscription' 
							: 'Upgrade to Premium')}
				</Button>
			</div>
		</Card>
	</div>

	<div class="mt-16">
		<h2 class="text-center text-2xl font-bold">Compare Plans</h2>
		<div class="mt-8 overflow-hidden rounded-xl border bg-card shadow-sm">
			<table class="w-full">
				<thead>
					<tr class="border-b bg-primary/10">
						<th class="px-6 py-4 text-left text-xs font-medium uppercase tracking-wider">Feature</th>
						<th class="px-6 py-4 text-center text-xs font-medium uppercase tracking-wider">Free</th>
						<th class="px-6 py-4 text-center text-xs font-medium uppercase tracking-wider">Premium</th>
					</tr>
				</thead>
				<tbody>
					{#each comparisons as { feature, free, premium }}
						<tr class="border-b last:border-0">
							<td class="px-6 py-4">{feature}</td>
							<td class="px-6 py-4 text-center text-muted-foreground">{free}</td>
							<td class="px-6 py-4 text-center font-medium text-primary">{premium}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
</div>
