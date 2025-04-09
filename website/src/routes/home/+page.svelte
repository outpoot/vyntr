<script lang="ts">
	import SearchInput from "$lib/components/self/SearchInput.svelte";
	import TrailingButtons from "$lib/components/self/TrailingButtons.svelte";
</script>

<div class="relative flex h-screen flex-col items-center gap-3" style="padding-top: 23vh">
	<h1
		class="montserrat-black relative select-none text-[4rem] text-primary sm:text-[5rem] md:text-[8rem]"
	>
		Vyntr
	</h1>

	<SearchInput className="max-w-3xl" />
	<TrailingButtons />
</div>