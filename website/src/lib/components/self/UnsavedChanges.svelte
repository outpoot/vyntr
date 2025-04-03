<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { quintInOut } from 'svelte/easing';
	import { slide } from 'svelte/transition';

	let { onSave = () => {}, onDiscard = () => {} } = $props();
</script>

<div
	class="fixed inset-x-0 bottom-0 z-40 flex h-16 items-center justify-center border-t bg-background/80 backdrop-blur"
	transition:slide={{
		duration: 200,
		easing: quintInOut
	}}
>
	<div class="flex items-center gap-20">
		<span class="text-sm text-muted">Careful — You have unsaved changes.</span>
		<div class="space-x-2">
			<button class="text-sm hover:underline" onclick={() => onDiscard()}>Discard</button>
			<Button size="sm" onclick={() => onSave()}>Save changes</Button>
		</div>
	</div>
</div>
