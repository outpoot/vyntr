<script lang="ts">
	import Search from 'lucide-svelte/icons/search';
	import { Spring } from 'svelte/motion';

	let { size = 28, className = '', ...rest } = $props();

	const position = new Spring({ y: 0, scale: 1 }, {
		stiffness: 0.05,
		damping: 0.2,
		precision: 0.0001
	});

	export async function animate() {
		position.target = { y: -6, scale: 0.95 };
		await new Promise(resolve => setTimeout(resolve, 150));
		
		position.target = { y: 0, scale: 1 };
		await new Promise(resolve => setTimeout(resolve, 150));
		
		position.target = { y: -3, scale: 0.98 };
		await new Promise(resolve => setTimeout(resolve, 150));
		
		position.target = { y: 0, scale: 1 };
	}
</script>

<div class="flex select-none items-center justify-center {className}" {...rest}>
	<div style="transform: translateY({position.current.y}px) scale({position.current.scale})">
		<Search class="transition-transform duration-200 hover:scale-105" {size} />
	</div>
</div>
