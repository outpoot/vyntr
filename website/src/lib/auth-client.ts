import { createAuthClient } from "better-auth/svelte";
import { env } from '$env/dynamic/public';

export const client = createAuthClient({
    baseURL: env.PUBLIC_BETTER_AUTH_URL,
});

export const { signIn, signUp, getSession, signOut } = client;