<script lang="ts">
	import SearchInput from '$lib/components/self/SearchInput.svelte';
	import TrailingButtons from '$lib/components/self/TrailingButtons.svelte';
	import { Button } from '$lib/components/ui/button';
</script>

<svelte:head>
	<title>Vyntr</title>
</svelte:head>

<div class="relative flex h-screen flex-col items-center gap-3" style="padding-top: 23vh">
	<h1
		class="montserrat-black relative select-none text-[4rem] text-primary sm:text-[5rem] md:text-[8rem]"
	>
		Vyntr
	</h1>

	<SearchInput className="max-w-3xl px-4" />
	<TrailingButtons />
</div>

<footer class="space-x-2 border-t border-border bg-card text-sm">
	<Button variant="ghost" href="/legal/about">About</Button>
	<Button variant="ghost" href="/legal/privacy">Privacy</Button>
	<Button variant="ghost" href="/legal/terms">Terms</Button>
	<Button variant="ghost" href="/settings">Settings</Button>
</footer>

<style>
	footer {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		text-align: center;
		padding: 0.25rem;
		transition: all 0.5s ease;
		z-index: 30;
	}
</style>
