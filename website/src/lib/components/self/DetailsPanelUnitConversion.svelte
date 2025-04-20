<script lang="ts">
	import ArrowRight from 'lucide-svelte/icons/arrow-right';
	import Ruler from 'lucide-svelte/icons/ruler';
	import type { UnitConversionSearchDetail } from '$lib/types/searchDetails';
	import { getUnitDisplayName } from '$lib/utils/unitParser';
	import { CATEGORY_NAMES } from '$lib/utils/units';
	import { formatAmount } from '$lib/utils';

	const { details } = $props<{ details: UnitConversionSearchDetail }>();
</script>

<div
	class="relative mb-6 overflow-hidden rounded-xl border bg-card p-4 shadow-custom-inset drop-shadow-md"
>
	<div class="flex items-start gap-4">
		<div class="rounded-full bg-primary/50 p-2 transition-transform hover:scale-110">
			<Ruler class="h-4 w-4" />
		</div>
		<div class="flex w-full flex-col gap-4">
			<div>
				<h3 class="text-2xl font-bold">Unit Conversion</h3>
				<p class="text-sm italic text-muted">{CATEGORY_NAMES[details.category]}</p>
			</div>

			<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
				<div class="flex flex-col">
					<span class="text-sm text-muted">From</span>
					<span class="text-lg font-semibold"
						>{details.value} {getUnitDisplayName(details.fromUnit)}</span
					>
				</div>
				<div class="hidden sm:block">
					<ArrowRight class="h-5 w-5 text-muted" />
				</div>
				<div class="flex flex-col">
					<span class="text-sm text-muted">To</span>
					<span class="text-lg font-semibold">
						{formatAmount(details.result)}
						{getUnitDisplayName(details.toUnit)}
					</span>
				</div>
			</div>
		</div>
	</div>
</div>
