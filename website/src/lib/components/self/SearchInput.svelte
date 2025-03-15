<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import SearchIcon from './SearchIcon.svelte';
	import { Search } from 'lucide-svelte';
	import TrailingButtons from './TrailingButtons.svelte';
	import { goto } from '$app/navigation';

	let searchIcon: any;
	let isFocused = $state(false);

	let {
		value = $bindable(),
		enableAutocomplete = $bindable(true),
		showTrailingButtons = true
	} = $props();

	let searchValue = $state(value);
	let selectedIndex = $state(-1);
	let inputRef: HTMLInputElement | null = $state(null);

	$effect(() => {
		if (inputRef) {
			inputRef.focus();
			isFocused = true;
		}

		if (searchValue !== value) {
			enableAutocomplete = true;
		}
	});

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
	let filteredSuggestions = $derived(
		suggestions.filter((s) => s.toLowerCase().includes(searchValue?.toLowerCase()))
	);
	let hasSuggestions = $derived(filteredSuggestions.length > 0);
	let showSuggestions = $derived(
		Boolean(enableAutocomplete && searchValue && hasSuggestions && isFocused)
	);

	function handleSubmit(event?: Event) {
		if (event) event.preventDefault();
		enableAutocomplete = false;

		if (searchValue.trim()) {
			goto(`/search?q=${encodeURIComponent(searchValue.trim())}`);
		}
	}

	function selectSuggestion(s: string) {
		searchValue = s;
		selectedIndex = -1;
		handleSubmit();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (!hasSuggestions) return;
		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				selectedIndex = (selectedIndex + 1) % filteredSuggestions.length;
				break;
			case 'ArrowUp':
				e.preventDefault();
				selectedIndex = selectedIndex <= 0 ? filteredSuggestions.length - 1 : selectedIndex - 1;
				break;
			case 'Enter':
				if (selectedIndex >= 0) selectSuggestion(filteredSuggestions[selectedIndex]);
				break;
			case 'Escape':
				isFocused = false;
				selectedIndex = -1;
				break;
		}
	}
</script>

<form class="relative w-full max-w-3xl" onsubmit={handleSubmit}>
	<SearchIcon
		bind:this={searchIcon}
		size={24}
		class="absolute left-5 top-1/2 z-20 h-6 w-6 -translate-y-1/2 text-primary-foreground"
	/>
	<Input
		bind:value={searchValue}
		placeholder="How do I cook..."
		{showSuggestions}
		focused={isFocused}
		bind:ref={inputRef}
		class={`h-11 w-full ${
			showSuggestions
				? 'rounded-b-none border-b-0 border-l-2 border-r-2 border-t-2'
				: 'rounded-b-[1.5rem] border-2'
		} bg-primary pl-14 text-base text-primary-foreground shadow-lg focus:border-ring focus:outline-none sm:h-12 sm:pl-16 sm:text-lg md:h-14`}
		onfocus={() => {
			searchIcon?.animate();
			isFocused = true;
		}}
		onblur={() => (isFocused = false)}
		onkeydown={handleKeydown}
	>
		{#each filteredSuggestions as suggestion, i}
			<button
				class="flex w-full items-center gap-3 rounded-md px-6 py-1 text-left text-base text-primary-foreground {i ===
				selectedIndex
					? 'bg-muted'
					: ''} hover:bg-muted"
				onmousedown={() => selectSuggestion(suggestion)}
				onmouseover={() => (selectedIndex = i)}
				onfocus={() => (selectedIndex = i)}
			>
				<Search
					size={12}
					class="transition-transform duration-100 {i === selectedIndex ? 'scale-110' : ''}"
				/>
				{suggestion}
			</button>
		{/each}

		{#if showTrailingButtons}
			<div class="mb-2 flex justify-center">
				<TrailingButtons />
			</div>
		{:else}
			<div class="mb-3"></div>
		{/if}
	</Input>
</form>
