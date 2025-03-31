import { writable } from 'svelte/store';

export const activeSidebarItem = writable<string>('home');
