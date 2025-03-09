<script lang="ts">
    import SearchInput from '$lib/components/self/SearchInput.svelte';
    import TrailingButtons from '$lib/components/self/TrailingButtons.svelte';
</script>

<div class="relative flex h-screen flex-col items-center gap-4" style="padding-top: 25vh">
    <div class="absolute inset-0 bg-black"></div>
    <div class="pointer-events-none absolute inset-0 bg-[url('/grain.png')] bg-repeat opacity-95"></div>

    <h1 class="montserrat-black relative select-none text-[4rem] text-primary-foreground sm:text-[5rem] md:text-[8rem]">
        Vyntr
    </h1>
    
    <SearchInput />
    <TrailingButtons />
</div>
