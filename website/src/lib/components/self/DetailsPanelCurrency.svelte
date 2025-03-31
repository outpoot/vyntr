<script lang="ts">
	import type { CurrencySearchDetail } from '$lib/types/searchDetails';
	import { DollarSign, ExternalLink } from 'lucide-svelte';
	import { formatLastUpdated, formatAmount } from '$lib/utils';

	const { details } = $props<{ details: CurrencySearchDetail }>();
</script>

<div
	class="relative overflow-hidden rounded-xl border bg-card p-4 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] drop-shadow-md"
>
	<div class="flex items-start gap-4">
		<div class="rounded-full bg-primary/50 p-2 transition-transform hover:scale-110">
			<DollarSign class="h-4 w-4" />
		</div>
		<div class="flex flex-col gap-2">
			<div class="text-2xl font-bold">
				{details.from.amount.toLocaleString()}
				{details.from.code}
				<span class="mx-1 text-muted-foreground">→</span>
				{formatAmount(details.to.amount)}
				{details.to.code}
			</div>
			<div class="text-sm text-muted-foreground">
				<p>1 {details.from.name} ≈ {details.rate.toFixed(6)} {details.to.name}</p>
				<p class="mt-1 text-xs">Last updated: {formatLastUpdated(details.lastUpdated)}</p>
			</div>
		</div>
	</div>

	<a
		href="https://github.com/fawazahmed0/exchange-api"
		target="_blank"
		rel="noopener noreferrer"
		class="absolute bottom-2 right-2 flex h-8 w-8 items-center justify-center rounded-full bg-transparent p-1 text-muted-foreground transition-all duration-200 hover:scale-110 hover:bg-primary/20"
		title="Data source"
	>
		<ExternalLink size={16} />
	</a>
</div>
