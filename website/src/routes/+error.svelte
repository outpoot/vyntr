<script lang="ts">
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import { goto } from '$app/navigation';

	const status = $derived(page.status);
	const message = $derived(page.error?.message || getDefaultMessage(status));

	function getDefaultMessage(status: number) {
		switch (status) {
			case 404:
				return "We've searched everywhere, but this page seems to be missing.";
			case 403:
				return "You don't have permission to access this search result.";
			case 429:
				return "Whoa there! You're searching too fast. Please slow down and try again.";
			case 500:
				return "Our search engine encountered an error. We're working to fix it.";
			default:
				return 'An unexpected error occurred while processing your request.';
		}
	}
</script>

<svelte:head>
	<title>{status} - {status === 404 ? 'Page Not Found' : 'Error'} | Vyntr</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="container mx-auto flex min-h-[80vh] flex-col items-center justify-center py-8">
	<div class="text-center">
		<h1 class="mb-4 text-7xl font-bold text-primary">{status}</h1>
		<p class="mb-3 text-2xl font-semibold">
			{status === 404 ? "The page doesn't exist :(" : 'Search error occurred'}
		</p>
		<p class="mb-8 max-w-md text-center text-muted-foreground">
			{message}
		</p>
		<div class="flex flex-wrap justify-center gap-4">
			<Button variant="default" onclick={() => goto('/home')}>Return to Search</Button>
			<Button variant="outline" onclick={() => history.back()}>Go Back</Button>
		</div>
	</div>
</div>
