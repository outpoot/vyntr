<script lang="ts">
    import HeartCrack from 'lucide-svelte/icons/heart-crack';

	const { detail } = $props<{ detail: String }>();
</script>

<div
	class="relative overflow-hidden rounded-xl border bg-card p-4 shadow-custom-inset drop-shadow-md"
>
	<div class="flex items-start gap-4">
		<div class="rounded-full bg-primary/50 p-2 transition-transform hover:scale-110">
			<HeartCrack class="h-4 w-4" />
		</div>
		<div class="flex flex-col gap-2">
			<div class="text-2xl font-bold">
				{detail}
			</div>
		</div>
	</div>
</div>
