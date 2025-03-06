<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import SearchIcon from '$lib/components/self/SearchIcon.svelte';
	let searchIcon: any;
	let isFocused = $state(false);
</script>

<div class="relative flex h-screen flex-col items-center justify-center gap-12">
	<!-- Blurred background -->
	<div
		class="absolute inset-0 bg-cover bg-center bg-no-repeat blur-sm"
		style="background-image: url('/background.webp')"
	></div>
	<!-- Sharp grain overlay -->
	<div
		class="pointer-events-none absolute inset-0 z-10 bg-[url('/grain.png')] bg-repeat opacity-95"
	></div>

	<h1 class="relative z-20 text-[8rem] font-bold" style="font-family: 'LinLibertine'">Vyntr</h1>
	<div class="relative z-20 mx-6 w-full max-w-4xl">
		<SearchIcon
			bind:this={searchIcon}
			size={30}
			class="absolute left-6 top-1/2 z-20 h-8 w-8 -translate-y-1/2 text-primary"
		/>
		<div class="group/panel relative">
			<div
				class="relative flex h-full items-center justify-center rounded-[2rem] bg-transparent backdrop-blur-lg transition-all duration-200 {isFocused ? 'shadow-md' : 'hover:shadow-md'}"
			>
				<div
					class="relative z-10 h-full w-full overflow-hidden rounded-[2rem] bg-background/50 text-foreground"
				>
					<Input
						placeholder="How do I cook..."
						class="h-20 border-0 bg-transparent pl-20 text-2xl focus:ring-0 focus:ring-offset-0"
						onfocus={() => {
							searchIcon?.animate();
							isFocused = true;
						}}
						onblur={() => (isFocused = false)}
					/>
				</div>
			</div>
		</div>
	</div>
</div>
