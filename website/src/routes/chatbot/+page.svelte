<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
    import ArrowUp from 'lucide-svelte/icons/arrow-up';
	import { Popover, PopoverContent, PopoverTrigger } from '$lib/components/ui/popover';
	import { onMount } from 'svelte';
    import AuthGate from '$lib/components/self/AuthGate.svelte';

	type Source = {
		title: string;
		url: string;
		favicon: string;
		preview?: string;
	};

	type MessageWithSources = {
		role: 'user' | 'assistant';
		content: string;
		sources?: {
			web: Source[];
			bliptext: Source | null;
		};
	};

	let messages: MessageWithSources[] = $state([]);
	let inputMessage = $state('');
	let lastMessageElement: HTMLDivElement | null = $state(null);
	let textareaElement: HTMLTextAreaElement;
	let messageUsage = $state({ limit: 5, used: 0, remaining: 5, resetsAt: '' });
	let timeUntilReset = $state('');

	function getResetTime(isoString: string) {
		const date = new Date(isoString);
		return date.toLocaleTimeString(undefined, { 
			hour: 'numeric', 
			minute: '2-digit',
			hour12: true 
		});
	}

	function updateCountdown(resetTime: string) {
		const now = new Date();
		const reset = new Date(resetTime);
		const diff = reset.getTime() - now.getTime();
		
		if (diff <= 0) {
			timeUntilReset = '';
			return;
		}

		const hours = Math.floor(diff / (1000 * 60 * 60));
		const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
		timeUntilReset = `(${hours}h ${minutes}m)`;
	}

	async function fetchMessageUsage() {
		const response = await fetch('/api/chat');
		if (response.ok) {
			messageUsage = await response.json();
		}
	}

	$effect(() => {
		if (lastMessageElement) {
			lastMessageElement.scrollIntoView({ behavior: 'smooth' });
		}
	});

	$effect(() => {
		if (messageUsage.resetsAt) {
			updateCountdown(messageUsage.resetsAt);
			const interval = setInterval(() => updateCountdown(messageUsage.resetsAt), 60000); // Update every minute
			return () => clearInterval(interval);
		}
	});

	onMount(() => {
		fetchMessageUsage();
	});

	function cleanMessageForAPI(message: MessageWithSources) {
		const { role, content } = message;
		return { role, content };
	}

	async function handleSubmit(e: { preventDefault: () => void }) {
		e.preventDefault();
		if (!inputMessage.trim()) return;

		const userMessage = inputMessage;
		messages = [...messages, { role: 'user', content: userMessage }];
		inputMessage = '';
		textareaElement.style.height = '56px';

		messages = [...messages, { role: 'assistant', content: '' }];
		const assistantMessageIndex = messages.length - 1;

		try {
			const response = await fetch('/api/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					messages: messages.slice(0, -1).map(cleanMessageForAPI)
				})
			});

			if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
			const reader = response.body?.getReader();
			if (!reader) throw new Error('No reader available');

			let content = '';
			let isGenerating = false;

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const text = new TextDecoder().decode(value);
				const events = text.split('\n\n').filter(Boolean);

				for (const event of events) {
					try {
						const lines = event.split('\n');
						const eventType = lines[0].replace('event: ', '');
						const data = JSON.parse(lines[1].replace('data: ', ''));

						switch (eventType) {
							case 'sources':
								messages[assistantMessageIndex].sources = data;
								break;
							case 'status':
								messages[assistantMessageIndex].content = data;
								content = '';
								isGenerating = data === 'Yapping...';
								break;
							case 'content':
								if (isGenerating) {
									content += data;
									messages[assistantMessageIndex].content = content;
								}
								break;
							case 'error':
								throw new Error(data);
						}
					} catch (eventError) {
						console.error('Error processing event:', { event, error: eventError });
						// Continue processing other events instead of breaking
						continue;
					}
				}
			}
		} catch (error) {
			console.error('Chat error:', error);
			messages[assistantMessageIndex].content = 'Sorry, something went wrong. Please try again.';
		} finally {
			await fetchMessageUsage();
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit(e);
		}
	}

	function handleTextareaInput(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		target.style.height = 'auto';
		target.style.height = Math.min(target.scrollHeight, 200) + 'px';
		target.style.overflow = 'hidden';
		setTimeout(() => (target.style.overflow = 'auto'), 0);

		const lineCount = (target.value.match(/\n/g) || []).length + 1;
		target.style.overflowY = lineCount > 7 ? 'scroll' : 'hidden';
	}

	function getDomainFromUrl(url: string) {
		try {
			return new URL(url).hostname;
		} catch {
			return url;
		}
	}

	function getPreview(preview: string | undefined) {
		if (!preview) return 'No description available';
		return preview.length > 100 ? preview.slice(0, 100) + '...' : preview;
	}
</script>

<AuthGate
    title="Welcome to Yappatron"
    description="Sign in to start chatting with our AI assistant. Free users get 5 messages per day!"
>
    <div class="relative flex h-screen max-h-screen flex-col">
        <main class="flex-1 overflow-hidden">
            <ScrollArea class="h-full">
                <div class="mx-auto mt-8 max-w-3xl space-y-4 px-4">
                    {#each messages as message, index}
                        {#if index === messages.length - 1}
                            <div
                                bind:this={lastMessageElement}
                                class="flex gap-3 {message.role === 'user'
                                    ? 'ml-auto w-[85%] md:w-[80%]'
                                    : 'w-[85%] md:w-[80%]'} rounded-xl bg-card p-4 shadow-custom-inset"
                            >
                                <div class="flex-1">
                                    {#if message.role === 'assistant'}
                                        <div class="mb-1 text-sm font-medium text-primary">Yappatron</div>
                                    {/if}
                                    <p class="whitespace-pre-line text-foreground">{message.content}</p>

                                    {#if message.role === 'assistant' && message.sources}
                                        <Popover>
                                            <PopoverTrigger>
                                                <div class="mt-2 inline-flex items-center">
                                                    <div class="flex -space-x-2">
                                                        {#if message.sources.bliptext}
                                                            <img
                                                                src={message.sources.bliptext.favicon}
                                                                alt="Bliptext"
                                                                class="h-5 w-5 rounded-full ring-2 ring-background"
                                                            />
                                                        {/if}
                                                        {#each message.sources.web.slice(0, 2) as source}
                                                            <img
                                                                src={source.favicon}
                                                                alt={source.title}
                                                                class="h-5 w-5 rounded-full ring-2 ring-background"
                                                            />
                                                        {/each}
                                                    </div>
                                                    <span class="ml-2 text-sm text-muted-foreground">sources</span>
                                                </div>
                                            </PopoverTrigger>
                                            <PopoverContent class="w-80 rounded-xl p-2" side="top">
                                                <div class="flex flex-col">
                                                    {#if message.sources.bliptext}
                                                        <a
                                                            href={message.sources.bliptext.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            class="flex flex-col gap-1 rounded-md p-3 text-sm transition-colors hover:bg-sidebar-accent"
                                                        >
                                                            <span class="font-medium">{message.sources.bliptext.title}</span>
                                                            <span class="text-muted-foreground"
                                                                >{message.sources.bliptext.preview || 'From Bliptext'}</span
                                                            >
                                                            <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                                                                <img
                                                                    src={message.sources.bliptext.favicon}
                                                                    alt="Bliptext"
                                                                    class="h-4 w-4"
                                                                />
                                                                {getDomainFromUrl(message.sources.bliptext.url)}
                                                            </div>
                                                        </a>
                                                    {/if}
                                                    {#each message.sources.web as source}
                                                        <a
                                                            href={source.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            class="flex flex-col gap-1 rounded-md p-3 text-sm transition-colors hover:bg-sidebar-accent"
                                                        >
                                                            <span class="font-medium">{source.title}</span>
                                                            <span class="text-muted-foreground">{getPreview(source.preview)}</span>
                                                            <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                                                                <img src={source.favicon} alt={source.title} class="h-4 w-4" />
                                                                {getDomainFromUrl(source.url)}
                                                            </div>
                                                        </a>
                                                    {/each}
                                                </div>
                                            </PopoverContent>
                                        </Popover>
                                    {/if}
                                </div>
                            </div>
                        {:else}
                            <div
                                class="flex gap-3 {message.role === 'user'
                                    ? 'ml-auto w-[85%] md:w-[80%]'
                                    : 'w-[85%] md:w-[80%]'} rounded-xl bg-card p-4 shadow-custom-inset"
                            >
                                <div class="flex-1">
                                    {#if message.role === 'assistant'}
                                        <div class="mb-1 text-sm font-medium text-primary">Yappatron</div>
                                    {/if}
                                    <p class="whitespace-pre-line text-foreground">{message.content}</p>

                                    {#if message.role === 'assistant' && message.sources}
                                        <Popover>
                                            <PopoverTrigger>
                                                <div class="mt-2 inline-flex items-center">
                                                    <div class="flex -space-x-2">
                                                        {#if message.sources.bliptext}
                                                            <img
                                                                src={message.sources.bliptext.favicon}
                                                                alt="Bliptext"
                                                                class="h-5 w-5 rounded-full ring-2 ring-background"
                                                            />
                                                        {/if}
                                                        {#each message.sources.web.slice(0, 2) as source}
                                                            <img
                                                                src={source.favicon}
                                                                alt={source.title}
                                                                class="h-5 w-5 rounded-full ring-2 ring-background"
                                                            />
                                                        {/each}
                                                    </div>
                                                    <span class="ml-2 text-sm text-muted-foreground">sources</span>
                                                </div>
                                            </PopoverTrigger>
                                            <PopoverContent class="w-80 rounded-xl p-2" side="top">
                                                <div class="flex flex-col">
                                                    {#if message.sources.bliptext}
                                                        <a
                                                            href={message.sources.bliptext.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            class="flex flex-col gap-1 rounded-md p-3 text-sm transition-colors hover:bg-sidebar-accent"
                                                        >
                                                            <span class="font-medium">{message.sources.bliptext.title}</span>
                                                            <span class="text-muted-foreground"
                                                                >{message.sources.bliptext.preview || 'From Bliptext'}</span
                                                            >
                                                            <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                                                                <img
                                                                    src={message.sources.bliptext.favicon}
                                                                    alt="Bliptext"
                                                                    class="h-4 w-4"
                                                                />
                                                                {getDomainFromUrl(message.sources.bliptext.url)}
                                                            </div>
                                                        </a>
                                                    {/if}
                                                    {#each message.sources.web as source}
                                                        <a
                                                            href={source.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            class="flex flex-col gap-1 rounded-md p-3 text-sm transition-colors hover:bg-sidebar-accent"
                                                        >
                                                            <span class="font-medium">{source.title}</span>
                                                            <span class="text-muted-foreground">{getPreview(source.preview)}</span>
                                                            <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                                                                <img src={source.favicon} alt={source.title} class="h-4 w-4" />
                                                                {getDomainFromUrl(source.url)}
                                                            </div>
                                                        </a>
                                                    {/each}
                                                </div>
                                            </PopoverContent>
                                        </Popover>
                                    {/if}
                                </div>
                            </div>
                        {/if}
                    {/each}

                    {#if messages.length === 0}
                        <div class="flex h-[calc(100vh-12rem)] items-center justify-center">
                            <div class="text-center text-muted-foreground">
                                <h3 class="text-lg font-semibold">Welcome to Vyntr Yappatron</h3>
                                <p class="text-sm">Start a conversation by typing a message below.</p>
                            </div>
                        </div>
                    {/if}
                </div>

                <div class="h-28"></div>
            </ScrollArea>
        </main>

        <div class="pointer-events-none absolute bottom-0 left-0 right-0 mb-4">
            <div class="mx-auto max-w-3xl px-4">
                <div class="mb-2 text-center text-sm text-muted-foreground">
                    {messageUsage.remaining} message{messageUsage.remaining === 1 ? '' : 's'} remaining today
                    {#if messageUsage.remaining <= 0}
                        · Resets at {getResetTime(messageUsage.resetsAt)} {timeUntilReset}
                    {/if}
                </div>
                <form class="pointer-events-auto relative flex" onsubmit={handleSubmit}>
                    <div
                        class="flex w-full items-end overflow-hidden rounded-[1.5rem] border bg-card shadow-custom-inset drop-shadow-md transition-colors focus-within:border-primary/80 hover:bg-card-hover"
                    >
                        <textarea
                            bind:this={textareaElement}
                            placeholder={messageUsage.remaining <= 0 ? "Message limit reached" : "Type your message..."}
                            bind:value={inputMessage}
                            rows="1"
                            onkeydown={handleKeyDown}
                            disabled={messageUsage.remaining <= 0}
                            class="flex w-full resize-none overflow-y-hidden bg-transparent px-6 py-4 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50
                            [&::-webkit-scrollbar-thumb]:rounded-full
                            [&::-webkit-scrollbar-thumb]:bg-muted-foreground/20
                            [&::-webkit-scrollbar-track]:rounded-full
                            [&::-webkit-scrollbar]:mr-2
                            [&::-webkit-scrollbar]:w-2"
                            style="min-height: 56px; max-height: 200px;"
                            oninput={handleTextareaInput}
                        ></textarea>
                        <Button type="submit" size="icon" disabled={messageUsage.remaining <= 0} class="group mb-2 mr-2 aspect-square rounded-full">
                            <ArrowUp
                                class="h-6 w-6 transition-transform duration-200 ease-out group-hover:-translate-y-0.5"
                            />
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</AuthGate>
