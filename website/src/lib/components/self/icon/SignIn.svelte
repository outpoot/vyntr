<script lang="ts">
	interface Props {
		size?: number;
		filled?: boolean;
		[key: string]: any;
	}

	let { size = 24, filled = false, ...rest }: Props = $props();

	let _size = size + 'px';
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	height={_size}
	viewBox="0 -960 960 960"
	width={_size}
	fill="currentColor"
	{...rest}
>
	<path
		d="M480-120v-80h280v-560H480v-80h280q33 0 56.5 23.5T840-760v560q0 33-23.5 56.5T760-120H480Zm-80-160-55-58 102-102H120v-80h327L345-622l55-58 200 200-200 200Z"
	/>
</svg>
