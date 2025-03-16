<script lang="ts">
    import { Menu, Share2, CircleUser } from 'lucide-svelte';
    import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
    import { Button } from '$lib/components/ui/button';
    import { useSidebar } from '$lib/components/ui/sidebar';
    import { fade, slide } from 'svelte/transition';

    const sidebar = useSidebar();
</script>

<header class="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border bg-sidebar px-4 text-sidebar-foreground">
    <div class="flex items-center">
        <div class="relative">
            {#if !sidebar.open}
                <div class="absolute left-0 top-1/2 -translate-y-1/2" transition:fade={{ duration: 200 }}>
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

    <div class="flex items-center gap-4">
        <Button variant="ghost" size="sm" class="gap-2">
            <Share2 size={16} />
            <span class="hidden sm:inline">Share</span>
        </Button>
        <DropdownMenu.Root>
            <DropdownMenu.Trigger>
                <Button variant="ghost" size="icon" class="rounded-full">
                    <CircleUser class="h-5 w-5" />
                    <span class="sr-only">Toggle user menu</span>
                </Button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Content align="end">
                <DropdownMenu.Label>My Account</DropdownMenu.Label>
                <DropdownMenu.Separator />
                <DropdownMenu.Item>Settings</DropdownMenu.Item>
                <DropdownMenu.Item>Support</DropdownMenu.Item>
                <DropdownMenu.Separator />
                <DropdownMenu.Item>Logout</DropdownMenu.Item>
            </DropdownMenu.Content>
        </DropdownMenu.Root>
    </div>
</header>
