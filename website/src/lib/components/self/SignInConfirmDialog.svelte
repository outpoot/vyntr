<script lang="ts">
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';

	let { open = $bindable(false), onConfirm } = $props<{
		open?: boolean;
		onConfirm: (provider: 'google') => void;
	}>();
</script>

<Dialog bind:open>
	<DialogContent class="sm:max-w-md">
		<DialogHeader>
			<DialogTitle>Sign in to Vyntr</DialogTitle>
			<DialogDescription>
				Choose a service to sign in with. Your account will be created automatically if you don't
				have one.
			</DialogDescription>
		</DialogHeader>
		<div class="flex flex-col gap-4 py-4">
			<Button
				class="flex w-full items-center justify-center gap-2"
				variant="outline"
				onclick={() => onConfirm('google')}
			>
				<img
					class="h-5 w-5"
					src="https://lh3.googleusercontent.com/COxitqgJr1sJnIDe8-jiKhxDx1FrYbtRHKJ9z_hELisAlapwE9LUPh6fcXIfb5vwpbMl4xl9H9TRFPc5NOO8Sb3VSgIBrfRYvW6cUA"
					alt="Google"
				/>
				<span>Continue with Google</span>
			</Button>

			<p class="text-center text-xs text-muted">
				By continuing, you agree to our
				<a href="/legal/terms" class="text-primary hover:underline">Terms of Service</a>
				and
				<a href="/legal/privacy" class="text-primary hover:underline">Privacy Policy</a>
			</p>
		</div>
	</DialogContent>
</Dialog>
