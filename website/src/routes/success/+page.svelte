<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Card } from '$lib/components/ui/card';
	import CircleCheck from 'lucide-svelte/icons/circle-check';
	import { goto } from '$app/navigation';
</script>

<div class="container mx-auto flex min-h-[80vh] items-center justify-center p-4">
	<Card class="w-full max-w-md p-6 text-center">
		<div class="mb-6 flex justify-center">
			<CircleCheck class="h-16 w-16 text-primary" />
		</div>

		<h1 class="mb-2 text-2xl font-bold">Success!</h1>
		<p class="mb-6 text-muted-foreground">Your payment has been successfully processed.</p>

		<div class="flex gap-4">
			<Button variant="outline" class="w-full" onclick={() => goto('/api')}>API</Button>
			<Button class="w-full" onclick={() => goto('/')}>Home</Button>
		</div>
	</Card>
</div>
