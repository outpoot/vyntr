<script lang="ts">
	import { Separator } from '$lib/components/ui/separator';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
</script>

<svelte:head>
	<title>About Vyntr</title>
	<meta name="description" content="Learn about Vyntr - A modern, privacy-focused search engine" />
	<meta property="og:title" content="About Vyntr" />
	<meta
		property="og:description"
		content="Learn about Vyntr - A modern, privacy-focused search engine"
	/>
</svelte:head>

<div class="container mx-auto max-w-4xl py-10">
	<Card.Root class="p-6">
		<div class="mb-8 space-y-4 text-center">
			<h1 class="text-4xl font-bold">About Vyntr</h1>
			<p class="text-muted-foreground">
				A modern search engine built with independence & troll in mind.
			</p>
		</div>

		<Separator class="my-6" />

		<div>
			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">What is Vyntr?</h2>
				<p class="mb-4">
					Vyntr is a search engine that combines modern web technologies with satire comedy. Built
					with features like AI-powered summaries and a Chatbot that has access to <a
						href="https://bliptext.com"
						>Bliptext, the Wikipedia where anybody can edit anything without restrictions</a
					>, Vyntr aims to make web searching both shit and ass.
				</p>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">Created by FaceDev</h2>
				<p class="mb-4">
					yo dawg I'm facedev a YouTuber and shit. I created Vyntr because i was bored
				</p>
				<div class="mt-6 flex flex-wrap gap-4">
					<Button
						variant="outline"
						href="https://youtube.com/@FaceDevStuff"
						class="flex items-center gap-2"
					>
						Watch on YouTube
					</Button>
					<Button
						variant="outline"
						href="https://github.com/outpoot/vyntr"
						class="flex items-center gap-2"
					>
						Vyntr on GitHub
					</Button>
					<Button
						variant="outline"
						href="https://x.com/facedevstuff"
						class="flex items-center gap-2"
					>
						X
					</Button>
				</div>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">Watch the Development</h2>
				<p class="mb-4">This video documents the creation of Vyntr.</p>
				<div class="mt-4 aspect-video">
					<iframe
						class="h-full w-full rounded-lg"
						src="https://www.youtube.com/embed/REPLACE_ME"
						title="I made my own Search Engine"
						frameborder="0"
						allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
						allowfullscreen
					></iframe>
				</div>
			</Card.Content>

			<Card.Content>
				<h2 class="mb-4 text-2xl font-semibold">Features</h2>
				<ul class="ml-6 list-disc space-y-2">
					<li>No tracking, no personal data collection</li>
					<li>AI-powered for the laughs</li>
					<li>Instant results with !bang commands</li>
					<li>Modern, clean interface</li>
					<li>Open source and transparent</li>
				</ul>
			</Card.Content>
		</div>
	</Card.Root>
</div>
