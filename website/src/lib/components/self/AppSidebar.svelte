<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import Crown from './icon/Crown.svelte';
	import Explore from './icon/Explore.svelte';
	import Home from './icon/Home.svelte';
	import Wand from './icon/Wand.svelte';
	import { activeSidebarItem } from '$lib/stores/sidebar';
	import { scale } from 'svelte/transition';

	const navItems = [
		{ id: 'home', label: 'Home', icon: Home },
		{ id: 'registry', label: 'Registry', icon: Explore },
		{ id: 'chatbot', label: 'Chatbot', icon: Wand },
		{ id: 'premium', label: 'Premium', icon: Crown },
		{ id: 'profile', label: 'Profile' }
	];

	const handleClick = (item: string) => {
		$activeSidebarItem = item;
	};
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
						<Sidebar.MenuItem>
							<div class:active={$activeSidebarItem === item.id}>
								<Sidebar.MenuButton
									class="menu-button flex h-12 items-center justify-start px-3 text-lg group-data-[collapsible=icon]:!p-0"
									onclick={() => handleClick(item.id)}
								>
									{#if item.icon}
										<div class="relative h-6 w-6">
											{#if $activeSidebarItem === item.id}
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
									<span class="font-medium" class:font-bold={$activeSidebarItem === item.id}
										>{item.label}</span
									>
								</Sidebar.MenuButton>
							</div>
						</Sidebar.MenuItem>
					{/each}
				</Sidebar.Menu>
			</Sidebar.GroupContent>
		</Sidebar.Group>
	</Sidebar.Content>
</Sidebar.Root>

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
</style>
