<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import SignInConfirmDialog from './SignInConfirmDialog.svelte';
	import { Popover, PopoverContent, PopoverTrigger } from '$lib/components/ui/popover';

	import Crown from './icon/Crown.svelte';
	import Explore from './icon/Explore.svelte';
	import Home from './icon/Home.svelte';
	import Wand from './icon/Wand.svelte';
	import SignIn from './icon/SignIn.svelte';
	import Settings from './icon/Settings.svelte';
	import Menu from 'lucide-svelte/icons/menu';
	import Sun from 'lucide-svelte/icons/sun';
	import Moon from 'lucide-svelte/icons/moon';

	import Key from './icon/Key.svelte';

	import { activeSidebarItem } from '$lib/stores/sidebar';
	import { scale } from 'svelte/transition';
	import { signIn, signOut } from '$lib/auth-client';
	import { USER_DATA } from '$lib/stores/userdata';
	import { mode, setMode } from 'mode-watcher';
	import More from './icon/More.svelte';
	import Dns from './icon/Dns.svelte';
	import { goto } from '$app/navigation';
	import { Label } from '../ui/label';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { Button } from '../ui/button';
	import { IsMobile } from '$lib/hooks/is-mobile.svelte';

	let navItems = $derived([
		{ id: 'home', label: 'Home', icon: Home, href: '/home' },
		{ id: 'registry', label: 'Registry', icon: Explore, href: '/registry' },
		{ id: 'chatbot', label: 'Chatbot', icon: Wand, href: '/chatbot' },
		{ id: 'premium', label: 'Premium', icon: Crown, href: '/premium' },
		{ id: 'api', label: 'API', icon: Key, href: '/api' },
		...(!$USER_DATA
			? [
					{
						id: 'account',
						label: 'Sign In',
						icon: SignIn,
						href: undefined
					}
				]
			: [])
	]);

	onMount(() => {
		const currentPath = page.url.pathname;
		const matchingItem = navItems.find((item) => item.href === currentPath);
		if (matchingItem && $activeSidebarItem !== matchingItem.id) {
			$activeSidebarItem = matchingItem.id;
		}
	});

	async function handleSignIn(provider: 'discord' | 'google') {
		await signIn.social({
			provider,
			callbackURL: `${page.url.pathname}?signIn=1`
		});
	}

	async function handleSignOut() {
		await signOut();
		goto('/');
	}

	const handleClick = (item: { id: string; label: string; icon: any; href?: string }) => {
		if (item.href) {
			goto(item.href);
		}

		if (item.id === 'account' && !$USER_DATA) {
			showConfirm = true;
			return;
		}

		if ($activeSidebarItem === item.id) {
			const iconEl = document.querySelector(`[data-item="${item.id}"] .icon`)?.parentElement;
			if (iconEl) {
				iconEl.classList.remove('pop');
				void iconEl.offsetWidth;
				iconEl.classList.add('pop');
			}
			return;
		}
		$activeSidebarItem = item.id;
	};

	let showConfirm = $state(false);

	function toggleTheme() {
		setMode($mode === 'dark' ? 'light' : 'dark');
	}
	const isMobile = new IsMobile().current;
</script>

<Sidebar.Provider>
	<Sidebar.Root collapsible="offcanvas">
		<Sidebar.Header class="ml-3 mt-4 flex flex-row items-center p-2">
			<Label class="montserrat-black text-2xl font-bold">Vyntr</Label>
			{#if $USER_DATA?.isAdmin}
				<span class="flex items-center justify-center text-[0.5rem] md:text-xs">|</span>
				<span class="text-[0.5rem] md:text-xs">Admin</span>
			{/if}
		</Sidebar.Header>

		<Sidebar.Content>
			<Sidebar.Group>
				<Sidebar.GroupContent>
					<Sidebar.Menu>
						{#each navItems as item}
							{@const isActive = $activeSidebarItem === item.id}
							<Sidebar.MenuItem>
								<div class:active={isActive}>
									<Sidebar.MenuButton
										class="menu-button flex h-12 items-center justify-start px-3 text-lg group-data-[collapsible=icon]:!p-0"
										onclick={() => handleClick(item)}
									>
										{#if item.icon}
											<div class="relative h-6 w-6" data-item={item.id}>
												{#if isActive}
													<div
														class="absolute inset-0 flex items-center justify-center"
														in:scale={{ duration: 150 }}
													>
														<item.icon size={24} class="icon" filled={true} />
													</div>
												{:else}
													<div class="absolute inset-0 flex items-center justify-center">
														<item.icon size={24} class="icon" filled={false} />
													</div>
												{/if}
											</div>
										{/if}
										<span class="label font-medium" class:font-bold={isActive}>
											{item.label}
										</span>
									</Sidebar.MenuButton>
								</div>
							</Sidebar.MenuItem>
						{/each}
						<Popover>
							<PopoverTrigger>
								<Sidebar.MenuItem>
									<div>
										<Sidebar.MenuButton
											class="menu-button flex h-12 items-center justify-start px-3 text-lg group-data-[collapsible=icon]:!p-0"
										>
											<div class="relative h-6 w-6">
												<div class="absolute inset-0 flex items-center justify-center">
													<More size={24} class="icon" filled={false} />
												</div>
											</div>
											<span class="label font-medium">More</span>
										</Sidebar.MenuButton>
									</div>
								</Sidebar.MenuItem>
							</PopoverTrigger>
							<PopoverContent class="w-64 rounded-xl p-2" side={!isMobile ? 'right' : 'bottom'}>
								{#if $USER_DATA}
									<p class="px-3 py-1.5">
										<span class="text-sm font-medium">Logged in as "{$USER_DATA?.name}"</span>
										<span class="text-sm text-muted-foreground">{`${$USER_DATA?.email.substring(
											0,
											2
										)}***${$USER_DATA?.email.substring($USER_DATA?.email.length - 1)}@${
											$USER_DATA?.email.split('@')[1]
										}`}</span>
									</p>
								{:else}
									<p class="px-3 py-1.5">
										<span class="text-sm font-medium">Sign in to unlock all features</span>
									</p>
								{/if}
								<div class="flex flex-col">
									<button
										class="flex w-full items-center gap-2 rounded-md p-3 text-sm font-medium transition-colors hover:bg-sidebar-accent"
										onclick={toggleTheme}
									>
										{#if $mode === 'dark'}
											<div class="flex items-center gap-2" in:scale|local={{ duration: 150 }}>
												<Sun class="h-4 w-4" />
												<span class="label font-medium">Light mode</span>
											</div>
										{:else}
											<div class="flex items-center gap-2" in:scale|local={{ duration: 150 }}>
												<Moon class="h-4 w-4" />
												<span class="label font-medium">Dark mode</span>
											</div>
										{/if}
									</button>
									{#if $USER_DATA}
										<button
											onclick={() => goto('/domains/list')}
											class="flex w-full items-center gap-2 rounded-md p-3 text-sm font-medium transition-colors hover:bg-sidebar-accent"
										>
											<Dns class="h-4 w-4" />
											<span class="label font-medium">My Domains</span>
										</button>

										<button
											onclick={() => goto('/settings')}
											class="flex w-full items-center gap-2 rounded-md p-3 text-sm font-medium transition-colors hover:bg-sidebar-accent"
										>
											<Settings class="h-4 w-4" />
											<span class="label font-medium">Settings</span>
										</button>

										{#if $USER_DATA?.isAdmin}
											<button
												onclick={() => goto('/admin/domains')}
												class="flex w-full items-center gap-2 rounded-md p-3 text-sm font-medium transition-colors hover:bg-sidebar-accent"
											>
												<Dns class="h-4 w-4" />
												<span class="label font-medium">Verification Center</span>
											</button>
										{/if}

										<div class="my-2 border-t"></div>

										<button
											onclick={handleSignOut}
											class="flex w-full items-center gap-2 rounded-md p-3 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
										>
											<SignIn class="h-4 w-4" />
											<span class="label font-medium">Sign out</span>
										</button>
									{/if}
								</div>
							</PopoverContent>
						</Popover>
					</Sidebar.Menu>
				</Sidebar.GroupContent>
			</Sidebar.Group>
		</Sidebar.Content>
	</Sidebar.Root>

	<div class="fixed left-4 top-4 z-40 md:hidden">
		<Sidebar.Trigger>
			<Button>
				<Menu class="h-6 w-6" />
				<span class="sr-only">Toggle Sidebar</span>
			</Button>
		</Sidebar.Trigger>
	</div>
</Sidebar.Provider>

<SignInConfirmDialog bind:open={showConfirm} onConfirm={handleSignIn} />

<style lang="postcss">
	:global(.icon) {
		@apply !h-6 !w-6 transition-all duration-200 ease-in-out;
	}

	:global(.menu-button) {
		@apply relative overflow-hidden transition-all duration-200;
	}

	:global(.menu-button:hover) {
		@apply bg-border/10 shadow-custom-inset;
	}

	:global(.menu-button:hover:not(.active) .icon) {
		transform: scale(1.1) !important;
	}

	:global(.active .menu-button span),
	:global(.active .menu-button .icon) {
		@apply !text-foreground;
	}

	:global(.menu-button:hover .label) {
		transform: rotate(2deg);
		transition: transform 200ms ease;
	}

	:global(.label) {
		transform: rotate(0deg);
		transition: transform 200ms ease;
	}

	:global(.pop) {
		animation: pop 300ms cubic-bezier(0.34, 1.56, 0.64, 1);
	}

	@keyframes pop {
		0%,
		100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.125);
		}
	}
</style>
