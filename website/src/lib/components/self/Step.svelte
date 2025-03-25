<script lang="ts">
	let { number, title, children } = $props();
</script>

<div>
	<div class="mb-1 flex items-center gap-2">
		<div
			class="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground"
		>
			{number}
		</div>
		<span class="font-medium">{title}</span>
	</div>
	<div class="ml-10">
		{@render children()}
	</div>
</div>
