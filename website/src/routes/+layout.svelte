<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	let { children } = $props();
</script>

<ModeWatcher />
{@render children()}

<footer class="space-x-4 border-t border-border bg-primary text-sm text-primary-foreground">
	<a href="/about">About</a>
	<a href="/about">Privacy</a>
	<a href="/about">Terms</a>
	<a href="/about">Settings</a>
</footer>

<style>
	footer {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		text-align: center;
		padding: 0.75rem;
		transition: all 0.5s ease;
		z-index: 30;
	}
</style>
