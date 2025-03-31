<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Compass, Home, Bot, Crown, User } from 'lucide-svelte';
</script>

<Sidebar.Root collapsible="icon">
	<Sidebar.Header class="flex flex-row items-center p-2">
		<h1 class="montserrat-black ml-3 text-2xl">Vyntr</h1>
	</Sidebar.Header>

	<Sidebar.Content>
		<Sidebar.Group>
			<Sidebar.GroupContent>
				<Sidebar.Menu>
					<Sidebar.MenuItem>
						<Sidebar.MenuButton
							class="h-12 space-x-1.5 p-3 text-lg font-bold group-data-[collapsible=icon]:!p-0"
						>
							<Home size={24} class="!h-6 !w-6" />
							<span>Home</span>
						</Sidebar.MenuButton>
					</Sidebar.MenuItem>
					<Sidebar.MenuItem>
						<Sidebar.MenuButton
							class="h-12 space-x-1.5 p-3 text-lg group-data-[collapsible=icon]:!p-0"
						>
							<Compass size={24} class="!h-6 !w-6" />
							<span>Registry</span>
						</Sidebar.MenuButton>
					</Sidebar.MenuItem>
					<Sidebar.MenuItem>
						<Sidebar.MenuButton
							class="h-12 space-x-1.5 p-3 text-lg group-data-[collapsible=icon]:!p-0"
						>
							<Bot size={24} class="!h-6 !w-6" />
							<span>Chatbot</span>
						</Sidebar.MenuButton>
					</Sidebar.MenuItem>
					<Sidebar.MenuItem>
						<Sidebar.MenuButton
							class="h-12 space-x-1.5 p-3 text-lg group-data-[collapsible=icon]:!p-0"
						>
							<Crown size={24} class="!h-6 !w-6" />
							<span>Premium</span>
						</Sidebar.MenuButton>
					</Sidebar.MenuItem>
					<Sidebar.MenuItem>
						<Sidebar.MenuButton
							class="h-12 space-x-1.5 p-3 text-lg group-data-[collapsible=icon]:!p-0"
						>
							<User size={24} class="!h-6 !w-6" />
							<span>Profile</span>
						</Sidebar.MenuButton>
					</Sidebar.MenuItem>
				</Sidebar.Menu>
			</Sidebar.GroupContent>
		</Sidebar.Group>
	</Sidebar.Content>
</Sidebar.Root>
