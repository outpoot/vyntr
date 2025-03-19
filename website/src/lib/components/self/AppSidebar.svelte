<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Search, MessageSquarePlus, Menu } from 'lucide-svelte';
	import { Button } from '../ui/button';

	const searchHistory = {
		today: [
			'how to center a div in tailwind',
			'typescript generic constraints',
			'svelte stores vs signals'
		],
		yesterday: ['best practices for api routes', 'rust vs go performance'],
		older: [
			'javascript array methods cheatsheet',
			'docker compose environment variables',
			'graphql vs rest api',
			'web assembly tutorial'
		]
	};
</script>

<Sidebar.Root collapsible="offcanvas">
	<Sidebar.Header class="flex flex-row justify-between border-b border-border p-2">
		<Sidebar.Trigger class="h-9 w-9 px-2 py-2">
			<Menu size={20} />
		</Sidebar.Trigger>
		<div class="inline-flex items-center gap-1">
			<Button class="h-9 w-9 px-2 py-2" variant="ghost">
				<Search size={20} />
			</Button>
			<Button class="h-9 w-9 px-2 py-2" variant="ghost">
				<MessageSquarePlus size={20} />
			</Button>
		</div>
	</Sidebar.Header>

	<Sidebar.Content>
		<Sidebar.Group>
			<Sidebar.GroupLabel>Today</Sidebar.GroupLabel>
			<Sidebar.GroupContent>
				<Sidebar.Menu>
					{#each searchHistory.today as query}
						<Sidebar.MenuItem>
							<Sidebar.MenuButton>
								<span class="truncate">{query}</span>
							</Sidebar.MenuButton>
						</Sidebar.MenuItem>
					{/each}
				</Sidebar.Menu>
			</Sidebar.GroupContent>
		</Sidebar.Group>

		<Sidebar.Group>
			<Sidebar.GroupLabel>Yesterday</Sidebar.GroupLabel>
			<Sidebar.GroupContent>
				<Sidebar.Menu>
					{#each searchHistory.yesterday as query}
						<Sidebar.MenuItem>
							<Sidebar.MenuButton>
								<span class="truncate">{query}</span>
							</Sidebar.MenuButton>
						</Sidebar.MenuItem>
					{/each}
				</Sidebar.Menu>
			</Sidebar.GroupContent>
		</Sidebar.Group>

		<Sidebar.Group>
			<Sidebar.GroupLabel>Older</Sidebar.GroupLabel>
			<Sidebar.GroupContent>
				<Sidebar.Menu>
					{#each searchHistory.older as query}
						<Sidebar.MenuItem>
							<Sidebar.MenuButton>
								<span class="truncate">{query}</span>
							</Sidebar.MenuButton>
						</Sidebar.MenuItem>
					{/each}
				</Sidebar.Menu>
			</Sidebar.GroupContent>
		</Sidebar.Group>
	</Sidebar.Content>
</Sidebar.Root>
