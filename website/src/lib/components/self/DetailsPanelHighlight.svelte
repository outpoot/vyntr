<script lang="ts">
	import { Info } from 'lucide-svelte';

	const { text } = $props<{ text: string }>();

	const regex = /^(.*?)highlight\("([^"]+)"\)(.*?)$/;
	const match = text.match(regex);

	let beforeHighlight = $state('');
	let highlighted = $state('');
	let afterHighlight = $state('');

	if (match) {
		beforeHighlight = match[1];
		highlighted = match[2];
		afterHighlight = match[3];
	} else {
		beforeHighlight = text;
	}
</script>

<div
	class="relative mb-6 overflow-hidden rounded-xl border bg-card p-4 shadow-custom-inset drop-shadow-md"
>
	<div class="flex items-start gap-4">
		<div class="rounded-full bg-primary/20 p-2 transition-transform hover:scale-110">
			<Info class="h-4 w-4" />
		</div>
		<div class="flex w-full flex-col">
			<p class="text-lg">
				{beforeHighlight}<span class="rounded bg-primary/20 px-1">{highlighted}</span
				>{afterHighlight}
			</p>
		</div>
	</div>
</div>
