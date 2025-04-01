import { writable } from 'svelte/store';

export type User = {
    id: string;
    name: string;
    email: string;
    isAdmin: boolean;
    image: string;
    isBanned: boolean;
    banReason: string | null;
} | null;

export const USER_DATA = writable<User>(undefined);