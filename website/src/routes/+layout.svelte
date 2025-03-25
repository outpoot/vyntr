<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	let { children } = $props();
</script>

<ModeWatcher />
<div class="fixed inset-0 bg-background"></div>
<div class="graddygrad fixed inset-0"></div>

{@render children()}

<style>
	.graddygrad {
		z-index: 9999;
		background: conic-gradient(
			from 50deg at 50% 10%,
			hsl(var(--primary)) 0deg,
			hsl(var(--secondary)) 120deg,
			hsl(var(--destructive)) 240deg
		);
		mix-blend-mode: normal;
		filter: blur(75px);
		will-change: filter;
		border-radius: 100%;
		opacity: 0.1;
		width: 100vw;
		height: 100vh;
		pointer-events: none;
		user-select: none;
	}
</style>
