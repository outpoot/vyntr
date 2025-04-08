<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import AppSidebar from '$lib/components/self/AppSidebar.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar';
	import { page } from '$app/state';
	import { invalidateAll } from '$app/navigation';
	import { onMount } from 'svelte';
	import { USER_DATA } from '$lib/stores/userdata';
	import { Toaster } from '$lib/components/ui/sonner';

	let { data, children } = $props<{
		data: { userSession?: any; theme: string };
		children: any;
	}>();

	let isMainPage = $state(page.route.id === '/');

	$effect(() => {
		if (data?.userSession) {
			USER_DATA.set(data.userSession);
		} else {
			USER_DATA.set(null);
		}
	});

	onMount(() => {
		console.log(
			'%c                                             ___   \n    _____                                   /\\  \\  \n   /::\\  \\                     ___         /::\\  \\ \n  /:/\\:\\  \\                   /\\__\\       /:/\\:\\__\\\n /:/ /::\\__\\   ___     ___   /:/__/      /:/ /:/  /\n/:/_/:/\\:|__| /\\  \\   /\\__\\ /::\\  \\     /:/_/:/  / \n\\:\\/:/ /:/  / \\:\\  \\ /:/  / \\/\\:\\  \\__  \\:\\/:/  /  \n \\::/_/:/  /   \\:\\  /:/  /   ~~\\:\\/\\__\\  \\::/__/   \n  \\:\\/:/  /     \\:\\/:/  /       \\::/  /   \\:\\  \\   \n   \\::/  /       \\::/  /        /:/  /     \\:\\__\\  \n    \\/__/         \\/__/         \\/__/       \\/__/',
			'color: #4962ee; font-family: monospace; font-size: 12px; font-weight: bold; text-shadow: 2px 2px rgba(0,0,0,0.2);'
		);
		console.log(
			'%c Welcome to Vyntr! DO NOT FUCKING PASTE ANYTHING IN THE CONSOLE UNLESS YOU KNOW WHAT YOU ARE DOING.',
			'color: #4962ee; font-family: monospace; font-size: 12px; font-weight: bold; text-shadow: 2px 2px rgba(0,0,0,0.2);'
		);
		console.log(
			'%c A product by Outpoot.com',
			'color: #4962ee; font-family: monospace; font-size: 12px; font-weight: bold; text-shadow: 2px 2px rgba(0,0,0,0.2);'
		);

		const url = new URL(window.location.href);
		if (url.searchParams.has('signedIn')) {
			url.searchParams.delete('signedIn');
			window.history.replaceState({}, '', url);
			invalidateAll();
		}
	});
</script>

<svelte:head>
	<script
		src="https://cdn.jsdelivr.net/npm/@polar-sh/checkout@0.1/dist/embed.global.js"
		defer
		data-auto-init
	></script>
</svelte:head>

<ModeWatcher />
<Toaster />

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
