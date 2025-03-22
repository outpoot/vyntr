<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	let { children } = $props();
</script>

<ModeWatcher />
<div class="fixed inset-0 bg-background"></div>
<div class="pointer-events-none fixed inset-0 bg-[url('/grain.png')] bg-repeat opacity-50"></div>

{@render children()}