<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import AppSidebar from '$lib/components/self/AppSidebar.svelte';
	import TopBar from '$lib/components/self/TopBar.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import { page } from '$app/state';

	let { children } = $props();
	let isMainPage = $state(page.route.id === '/');
</script>

<ModeWatcher />
<div class="fixed inset-0 bg-background"></div>
<div class="graddygrad fixed inset-0"></div>

{#if isMainPage}
	{@render children()}
{:else}
	<Sidebar.Provider>
		<div class="flex h-screen w-full">
			<div class="relative">
				<AppSidebar />
			</div>
			<div class="flex min-w-0 flex-1 flex-col">
				<TopBar />
				<main class="relative flex-1 overflow-y-auto">
					{@render children()}
				</main>
			</div>
		</div>
	</Sidebar.Provider>
{/if}

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
