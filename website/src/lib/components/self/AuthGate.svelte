<script lang="ts">
	import { USER_DATA } from '$lib/stores/userdata';
	import { Button } from '$lib/components/ui/button';
	import { signIn } from '$lib/auth-client';
	import { page } from '$app/state';

	export let title = 'Sign in required';
	export let description = 'Please sign in to access this feature.';

	async function handleSignIn() {
		await signIn.social({
			provider: 'google',
			callbackURL: `${page.url.pathname}?signIn=1`
		});
	}
</script>

{#if $USER_DATA}
	<slot />
{:else}
	<div class="flex h-[calc(100vh-12rem)] flex-col items-center justify-center gap-6 text-center">
		<div class="max-w-md space-y-2">
			<h2 class="text-2xl font-semibold">{title}</h2>
			<p class="text-muted-foreground">{description}</p>
		</div>
		<Button size="lg" onclick={handleSignIn}>Sign in with Google</Button>
	</div>
{/if}
