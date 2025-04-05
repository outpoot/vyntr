import { createAuthClient } from "better-auth/svelte";
import { apiKeyClient } from "better-auth/client/plugins";
import { env } from '$env/dynamic/public';

export const client = createAuthClient({
    baseURL: env.PUBLIC_BETTER_AUTH_URL,
    plugins: [
        apiKeyClient()
    ]
});

export const { signIn, signUp, getSession, signOut } = client;