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
		d="M240-400q-33 0-56.5-23.5T160-480q0-33 23.5-56.5T240-560q33 0 56.5 23.5T320-480q0 33-23.5 56.5T240-400Zm240 0q-33 0-56.5-23.5T400-480q0-33 23.5-56.5T480-560q33 0 56.5 23.5T560-480q0 33-23.5 56.5T480-400Zm240 0q-33 0-56.5-23.5T640-480q0-33 23.5-56.5T720-560q33 0 56.5 23.5T800-480q0 33-23.5 56.5T720-400Z"
	/>
</svg>
