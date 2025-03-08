<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import SearchIcon from '$lib/components/self/SearchIcon.svelte';
	import Theme from '$lib/components/self/Theme.svelte';
	import { Button } from '$lib/components/ui/button';
	let searchIcon: any;
	let isFocused = $state(false);
</script>

<div class="relative flex h-screen flex-col items-center justify-center gap-12 px-4 sm:px-6">
	<div class="absolute inset-0 bg-black"></div>

	<div
		class="pointer-events-none absolute inset-0 bg-[url('/grain.png')] bg-repeat opacity-95"
	></div>

	<h1
		class="montserrat-black relative select-none text-[4rem] text-primary-foreground sm:text-[5rem] md:text-[8rem]"
	>
		Vyntr
	</h1>
	<div class="relative w-full max-w-4xl">
		<SearchIcon
			bind:this={searchIcon}
			size={30}
			class="absolute left-6 top-1/2 z-20 h-8 w-8 -translate-y-1/2 text-primary-foreground"
		/>
		<Input
			placeholder="How do I cook..."
			class="h-14 w-full rounded-[2rem] border-2 bg-primary pl-20 text-lg text-primary-foreground shadow-xl focus:border-2 focus:border-ring focus:outline-none sm:h-16 sm:text-xl md:h-20 md:text-2xl"
			onfocus={() => {
				searchIcon?.animate();
				isFocused = true;
			}}
			onblur={() => (isFocused = false)}
			autofocus
		/>
	</div>

	<div class="z-20">
		<Button>I'm Feeling Lucky</Button>
	</div>
</div>
