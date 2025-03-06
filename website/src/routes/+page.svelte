<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import Theme from '$lib/components/self/Theme.svelte';
	import SearchIcon from '$lib/components/self/SearchIcon.svelte';
	let searchIcon: any;
	let isFocused = $state(false);
</script>

<div class="flex h-screen items-center justify-center flex-col gap-8">
	<h1 class="text-8xl font-bold" style="font-family: 'LinLibertine'">Vyntr</h1>
	<div class="relative w-full max-w-2xl mx-4">
		<SearchIcon
			bind:this={searchIcon}
			size={20}
			class="absolute left-4 top-1/2 z-20 h-5 w-5 -translate-y-1/2 text-primary"
		/>
		<div class="group/panel relative">
			<div
				class="relative flex h-full items-center justify-center rounded-3xl bg-background
				bg-gradient-to-b from-border to-border/50 p-px transition-all duration-200
				{isFocused ? 'shadow-md' : 'hover:shadow-md'}"
			>
				<div
					class="relative z-10 h-full w-full overflow-hidden rounded-3xl bg-background/80 text-foreground"
				>
					<Input
						placeholder="How do I cook..."
						class="border-0 pl-12 focus:ring-0 focus:ring-offset-0 h-14 text-lg"
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

<Theme />