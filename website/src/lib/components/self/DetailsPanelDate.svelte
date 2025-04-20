<script lang="ts">
	import Calendar from 'lucide-svelte/icons/calendar';

	const { displayText, description, date } = $props<{
		displayText: string;
		description: string;
		date: string;
	}>();

	const formattedDate = new Date(date).toLocaleDateString('en-US', {
		weekday: 'long',
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	});
</script>

<div
	class="relative overflow-hidden rounded-xl border bg-card p-4 shadow-custom-inset drop-shadow-md"
>
	<div class="flex items-start gap-4">
		<div class="rounded-full bg-primary/50 p-2 transition-transform hover:scale-110">
			<Calendar class="h-4 w-4" />
		</div>
		<div class="flex flex-col gap-1">
			{#if description}
				<h3 class="text-lg font-semibold">{description}</h3>
			{/if}
			<p class="text-3xl font-bold">{displayText}</p>
			<p class="text-sm text-muted">{formattedDate}</p>
		</div>
	</div>
</div>
