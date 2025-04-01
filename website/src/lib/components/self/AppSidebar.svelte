<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import SignInConfirmDialog from './SignInConfirmDialog.svelte';

	import Crown from './icon/Crown.svelte';
	import Explore from './icon/Explore.svelte';
	import Home from './icon/Home.svelte';
	import Wand from './icon/Wand.svelte';
	import SignIn from './icon/SignIn.svelte';

	import { activeSidebarItem } from '$lib/stores/sidebar';
	import { scale } from 'svelte/transition';
	import { signIn } from '$lib/auth-client';
	import { page } from '$app/state';
	import { USER_DATA } from '$lib/stores/userdata';

	let navItems = $derived([
		{ id: 'home', label: 'Home', icon: Home },
		{ id: 'registry', label: 'Registry', icon: Explore },
		{ id: 'chatbot', label: 'Chatbot', icon: Wand },
		{ id: 'premium', label: 'Premium', icon: Crown },
		{
			id: 'account',
			label: $USER_DATA ? 'Profile' : 'Sign In',
			icon: $USER_DATA ? Home : SignIn
		}
	]);

	async function handleSignIn(provider: 'discord' | 'google') {
		await signIn.social({
			provider,
			callbackURL: `${page.url.pathname}?signIn=1`
		});
	}

	const handleClick = (item: { id: string; label: string; icon: any }) => {
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
</script>

<Sidebar.Root collapsible="icon">
	<Sidebar.Header class="mt-4 flex flex-row items-center p-2">
		<h1 class="montserrat-black ml-3 text-2xl">Vyntr</h1>
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
													<svelte:component this={item.icon} size={24} class="icon" filled={true} />
												</div>
											{:else}
												<div class="absolute inset-0 flex items-center justify-center">
													<svelte:component
														this={item.icon}
														size={24}
														class="icon"
														filled={false}
													/>
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
				</Sidebar.Menu>
			</Sidebar.GroupContent>
		</Sidebar.Group>
	</Sidebar.Content>
</Sidebar.Root>

<SignInConfirmDialog bind:open={showConfirm} onConfirm={handleSignIn} />

<style lang="postcss">
	:global(.icon) {
		@apply !h-6 !w-6 transition-all duration-200 ease-in-out;
	}

	:global(.menu-button) {
		@apply relative overflow-hidden transition-all duration-200;
	}

	:global(.menu-button:hover) {
		@apply bg-border/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)];
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
