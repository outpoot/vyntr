<script lang="ts">
    import {
        Dialog,
        DialogContent,
        DialogHeader,
        DialogTitle,
        DialogDescription
    } from '$lib/components/ui/dialog';

    let { open = $bindable(false) } = $props<{ open?: boolean }>();

    const sections = [
        {
            title: 'Queries',
            items: [
                { title: 'Search by title', content: 'title:"getting started"' },
                { title: 'Search multiple options', content: 'python AND (django OR flask)' },
                { title: 'Search by language', content: '(react OR vue) AND language:ja' },
                { title: 'Search by parent URL', content: 'url:github.com' },
                { title: 'Search by domain', content: 'url:.org' },
                { title: 'Search by subdomain', content: 'url:docs.' }
            ]
        },
        {
            title: 'Search Settings',
            items: [
                { 
                    title: 'Configuration', 
                    content: 'Search settings can be accessed in <a href="/settings" class="text-primary hover:underline">Settings</a>' 
                }
            ]
        },
        {
            title: 'Keyboard Shortcuts',
            items: [
                { title: '↑/↓', content: 'Navigate between autocomplete suggestions' },
                { title: 'Enter', content: 'Open selected result' },
                { title: 'Esc', content: 'Exit dialogs and menus' }
            ]
        }
    ];
</script>

<Dialog bind:open>
    <DialogContent class="sm:max-w-2xl">
        <DialogHeader>
            <DialogTitle class="flex items-center gap-2">
                <img src="/favicon.svg" alt="Vyntr" class="h-6 w-6 text-foreground" />
                How to Vynt properly
            </DialogTitle>
            <DialogDescription>Tips and tricks to help you get the most out of Vyntr</DialogDescription>
        </DialogHeader>

        <div class="flex flex-col gap-8 py-6">
            {#each sections as section}
                <div>
                    <h3 class="mb-4 text-lg font-semibold">{section.title}</h3>
                    <div class="grid gap-4 {section.title === 'Search Settings' ? '' : 'sm:grid-cols-2'}">
                        {#each section.items as item}
                            <div class="rounded-lg border bg-card p-4 shadow-custom-inset">
                                <h4 class="font-medium text-primary">{item.title}</h4>
                                <p class="mt-1 text-sm text-muted-foreground">{@html item.content}</p>
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
    </DialogContent>
</Dialog>