<script lang="ts">
	import type { CalculatorSearchDetail } from '$lib/types/searchDetails';
	import * as Card from '$lib/components/ui/card';

	let { details } = $props<{ details: CalculatorSearchDetail }>();
</script>

{#if details}
	<Card.Root class="relative mb-6 w-full bg-card text-card-foreground shadow-sm">
		<Card.Header class="pb-3">
			<Card.Title>Calculator</Card.Title>
		</Card.Header>

		<Card.Content class="grid gap-4">
            <div class="flex flex-col gap-4">
                <div class="rounded-md border p-3 hover:bg-muted/50">
                    <p class="text-end font-mono text-md text-muted-foreground">{details.expression}=</p>
                    <p class="text-end font-mono text-4xl font-bold">{details.result}</p>
                </div>
            </div>
		</Card.Content>
	</Card.Root>
{/if}