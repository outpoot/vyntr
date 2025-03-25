<script lang="ts">
	import { Menu, CircleUser, Sun, Moon } from 'lucide-svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { useSidebar } from '$lib/components/ui/sidebar';
	import { fade, scale } from 'svelte/transition';
	import { mode, toggleMode } from 'mode-watcher';
	import { goto } from '$app/navigation';

	const sidebar = useSidebar();

	let rotating = false;
	const handleThemeToggle = () => {
		rotating = true;
		toggleMode();
		setTimeout(() => (rotating = false), 500);
	};
</script>

<header
	class="sticky top-0 z-50 flex h-[3.3rem] items-center justify-between border-b border-border bg-sidebar px-4 text-sidebar-foreground"
>
	<div class="flex items-center">
		<div class="relative">
			{#if !sidebar.open}
				<div
					class="absolute left-0 top-1/2 -translate-y-1/2"
					in:fade={{ duration: 200 }}
					out:fade={{ duration: 150 }}
				>
					<Button class="h-9 w-9 px-2 py-2" variant="ghost" onclick={sidebar.toggle}>
						<Menu size={20} />
					</Button>
				</div>
			{/if}
			<h1
				class="montserrat-black text-xl transition-transform duration-200"
				style="transform: translateX({!sidebar.open ? '2.75rem' : '0'})"
			>
				Vyntr
			</h1>
		</div>
	</div>

	<div class="flex items-center gap-2">
		<Button
			variant="ghost"
			size="icon"
			onclick={handleThemeToggle}
			aria-label="Toggle theme"
			class={rotating ? 'theme-rotate' : ''}
		>
			{#key $mode}
				<div in:scale={{ duration: 300, start: 0.5, opacity: 0 }}>
					{#if $mode === 'light'}
						<Moon size={20} />
					{:else}
						<Sun size={20} />
					{/if}
				</div>
			{/key}
		</Button>

		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				<Button variant="ghost" size="icon" class="hover-pulse rounded-full">
					<CircleUser class="h-5 w-5" />
					<span class="sr-only">Toggle user menu</span>
				</Button>
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end">
				<DropdownMenu.Label>My Account</DropdownMenu.Label>
				<DropdownMenu.Separator />
				<DropdownMenu.Item>Settings</DropdownMenu.Item>
				<DropdownMenu.Item>Support</DropdownMenu.Item>
				<DropdownMenu.Item onclick={() => goto('/domains/register')}>Domains</DropdownMenu.Item>
				<DropdownMenu.Separator />
				<DropdownMenu.Item>Logout</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</header>
