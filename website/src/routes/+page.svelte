<script lang="ts">
    import SearchInput from '$lib/components/self/SearchInput.svelte';
    import TrailingButtons from '$lib/components/self/TrailingButtons.svelte';
	import { Button } from '$lib/components/ui/button';
</script>

<svelte:head>
	<title>Vyntr</title>
</svelte:head>

<div class="relative flex h-screen flex-col items-center gap-3" style="padding-top: 23vh">
	<h1 class="montserrat-black relative select-none text-[4rem] text-primary-foreground sm:text-[5rem] md:text-[8rem] flex items-center gap-2">
		<img src="favicon.svg" alt="Vyntr logo" class="w-[5rem] mr-2" />
		Vyntr
	</h1>
    
    <SearchInput />
    <TrailingButtons />
</div>

<footer class="space-x-2 border-t border-border bg-primary text-sm text-primary-foreground">
	<Button variant="ghost" href="/about">About</Button>
	<Button variant="ghost" href="/about">Privacy</Button>
	<Button variant="ghost" href="/about">Terms</Button>
	<Button variant="ghost" href="/about">Settings</Button>
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
