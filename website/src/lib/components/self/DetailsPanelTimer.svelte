<script lang="ts">
	import { onMount } from 'svelte';
	import { scale } from 'svelte/transition';
	import { Button } from '$lib/components/ui/button';
	import { Play, Pause, RotateCcw, Timer, Clock, Volume2, VolumeX } from 'lucide-svelte';

	const { seconds } = $props<{ seconds: number }>();

	let timeLeft = $state(seconds);
	let isRunning = $state(false);
	let progress = $state(1);
	let timerInterval: ReturnType<typeof setInterval> | null = null;
	let audio: HTMLAudioElement;
	let isAlarmSounding = $state(false);
	let isCompleted = $state(false);
	let isMuted = $state(false);
	let isTimerMode = $state(true);
	let stopwatchTime = $state(0);

	onMount(() => {
		audio = new Audio('/timer-complete.mp3');
		audio.loop = true;
		return () => {
			stopAlarm();
			if (timerInterval) clearInterval(timerInterval);
		};
	});

	function toggleMode() {
		isTimerMode = !isTimerMode;
		resetTimer();
	}

	function toggleMute() {
		isMuted = !isMuted;
		if (isMuted) stopAlarm();
	}

	function startTimer() {
		if (isRunning) return;
		stopAlarm();
		isCompleted = false;
		isRunning = true;

		if (isTimerMode) {
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
					if (!isMuted) startAlarm();
				}
			}, 16);
		} else {
			const startTime = Date.now() - stopwatchTime * 1000;
			timerInterval = setInterval(() => {
				stopwatchTime = (Date.now() - startTime) / 1000;
				timeLeft = Math.floor(stopwatchTime);
				progress = 0;
			}, 16);
		}
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
		if (isTimerMode) {
			timeLeft = seconds;
			progress = 1;
		} else {
			stopwatchTime = 0;
			timeLeft = 0;
			progress = 0;
		}
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

	function formatStopwatchTime(seconds: number): string {
		if (seconds < 60) {
			return `${seconds.toFixed(1)}s`;
		}
		if (seconds < 3600) {
			const minutes = Math.floor(seconds / 60);
			const remainingSeconds = (seconds % 60).toFixed(1);
			return `${minutes}m ${remainingSeconds}s`;
		}
		const hours = Math.floor(seconds / 3600);
		return `${hours.toFixed(1)}h`;
	}

	function formatTime(totalSeconds: number): string {
		if (!isTimerMode) {
			return formatStopwatchTime(stopwatchTime);
		}
		const minutes = Math.floor(totalSeconds / 60);
		const seconds = totalSeconds % 60;
		return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
	}
</script>

<div
	class="relative h-[120px] overflow-hidden rounded-xl border bg-card shadow-[inset_0_1px_1px_rgba(255,255,255,0.9)] drop-shadow-md"
>
	<div class="absolute left-0 right-0 top-0 z-10 flex justify-between p-2">
		<Button variant="ghost" size="sm" onclick={toggleMode} class="w-[110px]">
			{#if isTimerMode}
				<div in:scale|fade={{ duration: 150 }} class="flex items-center">
					<Timer size={16} class="mr-2" />
					<span>Timer</span>
				</div>
			{:else}
				<div in:scale|fade={{ duration: 150 }} class="flex items-center">
					<Clock size={16} class="mr-2" />
					<span>Stopwatch</span>
				</div>
			{/if}
		</Button>
		<Button variant="ghost" size="sm" onclick={toggleMute} class="w-8">
			{#if isMuted}
				<div in:scale|fade={{ duration: 150 }}>
					<VolumeX size={16} />
				</div>
			{:else}
				<div in:scale|fade={{ duration: 150 }}>
					<Volume2 size={16} />
				</div>
			{/if}
		</Button>
	</div>

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
