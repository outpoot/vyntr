<script lang="ts">
	import Button from '$lib/components/ui/button/button.svelte';
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	let { children } = $props();
</script>

<ModeWatcher />
{@render children()}

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
