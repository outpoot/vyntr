<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import SearchIcon from '$lib/components/self/SearchIcon.svelte';
	import { Button } from '$lib/components/ui/button';
	let searchIcon: any;
	let isFocused = $state(false);
	let searchValue = $state('');

	const suggestions = [
		'How do I cook pasta',
		'How do I cook rice',
		'How do I cook chicken',
		'How do I cook steak',
		'How do I cook fish',
		'How do I cook eggs',
		'How do I cook potatoes',
		'How do I cook vegetables',
		'How do I cook bacon',
		'How do I cook breakfast'
	];

	let filteredSuggestions = $derived(suggestions.filter((s) => 
		s.toLowerCase().includes(searchValue.toLowerCase())
	));
	let hasSuggestions = $derived(filteredSuggestions.length > 0);
</script>

<div class="relative flex h-screen flex-col items-center justify-center gap-4">
	<div class="absolute inset-0 bg-black"></div>

	<div
		class="pointer-events-none absolute inset-0 bg-[url('/grain.png')] bg-repeat opacity-95"
	></div>

	<h1
		class="montserrat-black relative select-none text-[4rem] text-primary-foreground sm:text-[5rem] md:text-[8rem]"
	>
		Vyntr
	</h1>
	<div class="relative w-full max-w-3xl">
		<SearchIcon
			bind:this={searchIcon}
			size={24}
			class="absolute left-5 top-1/2 z-20 h-6 w-6 -translate-y-1/2 text-primary-foreground"
		/>
		<Input
			bind:value={searchValue}
			placeholder="How do I cook..."
			{hasSuggestions}
			focused={isFocused}
			class="h-12 w-full
		{hasSuggestions && searchValue && isFocused
				? 'rounded-b-none border-b-0 border-l-2 border-r-2 border-t-2'
				: 'rounded-b-[1.5rem] border-2'}
		bg-primary pl-14 text-base text-primary-foreground shadow-xl
		focus:border-ring focus:outline-none
		sm:h-14 sm:pl-16 sm:text-lg md:h-16"
			onfocus={() => {
				searchIcon?.animate();
				isFocused = true;
			}}
			onblur={() => (isFocused = false)}
			autofocus
		>
			{#each filteredSuggestions as suggestion}
				<button
					class="w-full px-6 py-2 text-left text-sm text-primary-foreground hover:bg-muted"
					onmousedown={() => (searchValue = suggestion)}
				>
					{suggestion}
				</button>
			{/each}
		</Input>
	</div>

	<div class="z-20 mt-2 inline-flex gap-2">
		<Button class="border">Search</Button>
		<Button class="border">I'm Feeling Lucky</Button>
	</div>
</div>
