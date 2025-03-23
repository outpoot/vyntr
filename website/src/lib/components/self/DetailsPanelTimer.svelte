<script lang="ts">
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { Play, Pause, RotateCcw } from 'lucide-svelte';

	const { seconds } = $props<{ seconds: number }>();

	let timeLeft = $state(seconds);
	let isRunning = $state(false);
	let progress = $state(1);
	let timerInterval: ReturnType<typeof setInterval> | null = null;
	let audio: HTMLAudioElement;
	let isAlarmSounding = $state(false);
	let isCompleted = $state(false);

	onMount(() => {
		audio = new Audio('/timer-complete.mp3');
		audio.loop = true;
		return () => {
			stopAlarm();
			if (timerInterval) clearInterval(timerInterval);
		};
	});

	function startTimer() {
		if (isRunning) return;

		stopAlarm();
		isCompleted = false;

		isRunning = true;

		const totalTime = seconds * 1000;
		const startTime = Date.now();
		timeLeft = seconds;
		progress = 1;

		timerInterval = setInterval(() => {
			const elapsed = Date.now() - startTime;
			const remaining = Math.max(0, totalTime - elapsed);
			progress = remaining / totalTime;
			timeLeft = Math.ceil(remaining / 1000);
			if (remaining <= 0) {
				stopTimer();
				isCompleted = true;
				startAlarm();
			}
		}, 16);
	}

	function stopTimer() {
		if (timerInterval) {
			clearInterval(timerInterval);
			timerInterval = null;
		}
		isRunning = false;
	}

	function resetTimer() {
		stopTimer();
		stopAlarm();
		timeLeft = seconds;
		progress = 1;
		isCompleted = false;
	}

	function startAlarm() {
		isAlarmSounding = true;
		audio.play();
	}

	function stopAlarm() {
		if (isAlarmSounding) {
			audio.pause();
			audio.currentTime = 0;
			isAlarmSounding = false;
		}
	}

	function formatTime(totalSeconds: number): string {
		const minutes = Math.floor(totalSeconds / 60);
		const seconds = totalSeconds % 60;
		return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
	}
</script>

<div class="relative mb-6 h-[120px] overflow-hidden rounded-xl border bg-card shadow-sm">
	<div
		class="absolute inset-0 bottom-0 left-0 right-0 bg-sidebar"
		style="height: {(1 - progress) * 100}%; transition: height 0.066s linear;"
	></div>

	<div class="relative flex h-full flex-col justify-between p-4">
		<div class="flex items-center justify-center">
			<span class="font-mono text-3xl font-bold text-primary-foreground"
				>{formatTime(timeLeft)}</span
			>
		</div>

		<div class="flex w-full gap-2">
			{#if !isCompleted && !isRunning}
				<Button class="h-10 flex-1" onclick={startTimer}>
					<Play size={18} class="mr-2" />
					<span>Start</span>
				</Button>
			{:else if isRunning}
				<Button class="h-10 flex-1" onclick={stopTimer} variant="destructive">
					<Pause size={18} class="mr-2" />
					<span>Pause</span>
				</Button>
			{/if}
			<Button class="h-10 flex-1" onclick={resetTimer} variant="outline">
				<RotateCcw size={18} class="mr-2" />
				<span>Reset</span>
			</Button>
		</div>
	</div>
</div>
