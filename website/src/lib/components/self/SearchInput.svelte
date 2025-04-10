<script lang="ts">
	import { Search } from 'lucide-svelte';
	import SearchIcon from './SearchIcon.svelte';
	import TrailingButtons from './TrailingButtons.svelte';
	import { Separator } from '$lib/components/ui/separator';
	import { cn } from '$lib/utils.js';

	function debounce<T extends (...args: any[]) => any>(
		func: T,
		wait: number
	): (...args: Parameters<T>) => void {
		let timeout: ReturnType<typeof setTimeout>;
		return (...args: Parameters<T>) => {
			clearTimeout(timeout);
			timeout = setTimeout(() => func(...args), wait);
		};
	}

	let {
		value = $bindable(),
		enableAutocomplete = $bindable(true),
		showTrailingButtons = true,
		className = $bindable('')
	} = $props();

	let searchIcon: any;
	let isFocused = $state(false);
	let searchValue = $state(value);
	let selectedIndex = $state(-1);
	let inputRef: HTMLInputElement | null = $state(null);

	let suggestions = $state<string[]>([]);
	let isLoading = $state(false);

	const fetchSuggestions = debounce(async (value: string) => {
		if (!value || value.length < 2 || !enableAutocomplete) {
			suggestions = [];
			return;
		}

		isLoading = true;
		try {
			const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(value)}`);
			if (response.ok) {
				suggestions = await response.json();
			}
		} catch (err) {
			console.error('Failed to fetch suggestions:', err);
		} finally {
			isLoading = false;
		}
	}, 150);

	$effect(() => {
		if (searchValue) {
			fetchSuggestions(searchValue);
		} else {
			suggestions = [];
		}
	});

	let filteredSuggestions = $derived(suggestions);
	let hasSuggestions = $derived(filteredSuggestions.length > 0);
	let showSuggestions = $derived(
		Boolean(enableAutocomplete && searchValue && hasSuggestions && isFocused)
	);

	$effect(() => {
		if (inputRef) {
			inputRef.focus();
			isFocused = true;
		}
		if (searchValue !== value) {
			enableAutocomplete = true;
		}
	});

	function handleSubmit(event?: Event) {
		if (event) event.preventDefault();
		enableAutocomplete = false;
		if (searchValue?.trim()) {
			window.location.href = `/search?q=${encodeURIComponent(searchValue.trim())}`;
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

<form class="w-full {className}" onsubmit={handleSubmit}>
	<div class="relative w-full">
		<SearchIcon
			bind:this={searchIcon}
			size={24}
			class="absolute left-5 top-1/2 z-20 h-6 w-6 -translate-y-1/2"
		/>
		<input
			bind:value={searchValue}
			bind:this={inputRef}
			placeholder="How do I cook..."
			class={cn(
				'flex h-11 w-full border bg-card px-3 py-2 pl-14 text-base shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] drop-shadow-md  transition-colors placeholder:text-muted focus-within:border-primary/80 hover:bg-card-hover focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 sm:h-12 sm:pl-16 sm:text-lg md:h-14',
				showSuggestions ? 'rounded-b-none rounded-t-[1.5rem] border-b-0' : 'rounded-[1.5rem]'
			)}
			onfocus={() => {
				searchIcon?.animate();
				isFocused = true;
			}}
			onblur={() => (isFocused = false)}
			onkeydown={handleKeydown}
		/>
		{#if showSuggestions}
			<div
				class="absolute left-0 right-0 top-full z-50 rounded-b-[1.5rem] border-x border-b bg-card drop-shadow-md"
			>
				<Separator class="mx-auto w-[95%]" />
				<div class="max-h-[500px] overflow-y-auto py-2">
					{#each filteredSuggestions as suggestion, i}
						<button
							class="flex w-full items-center gap-3 rounded-sm px-6 py-1 text-left text-base {i ===
							selectedIndex
								? 'bg-accent'
								: ''} hover:bg-primary/20"
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
				</div>
			</div>
		{/if}
	</div>
</form>
