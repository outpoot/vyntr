<script lang="ts">
    import AppSidebar from '$lib/components/self/AppSidebar.svelte';
    import TopBar from '$lib/components/self/TopBar.svelte';
    import * as Sidebar from '$lib/components/ui/sidebar';
  
    let { children } = $props();
</script>

<Sidebar.Provider>
    <div class="flex h-screen w-full">
        <div class="relative">
            <AppSidebar />
        </div>
        <div class="min-w-0 flex-1 flex flex-col">
            <TopBar />
            <main class="flex-1 overflow-y-auto">
                {@render children()}
            </main>
        </div>
    </div>
</Sidebar.Provider>
