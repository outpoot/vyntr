import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { apiKey } from "better-auth/plugins";
import { env } from '$env/dynamic/private';
import { db } from "./server/db";

if (!env.GOOGLE_CLIENT_ID) throw new Error('GOOGLE_CLIENT_ID is not set');
if (!env.GOOGLE_CLIENT_SECRET) throw new Error('GOOGLE_CLIENT_SECRET is not set');

export const auth = betterAuth({
    baseURL: env.PUBLIC_BETTER_AUTH_URL,
    secret: env.PRIVATE_BETTER_AUTH_SECRET,
    appName: "Vyntr",

    plugins: [
        apiKey({
            defaultPrefix: 'vyntr_',
            rateLimit: {
                enabled: true,
                timeWindow: 1000 * 60 * 60 * 24, // 1 day
                maxRequests: 1000 // 1000 requests per day
            },
            permissions: {
                defaultPermissions: {
                    api: ['read']
                }
            }
        })
    ],

    database: drizzleAdapter(db, {
        provider: "pg",
    }),
    socialProviders: {
        google: {
            clientId: env.GOOGLE_CLIENT_ID,
            clientSecret: env.GOOGLE_CLIENT_SECRET,
        }
    },

    session: {
        cookieCache: {
            enabled: true,
            maxAge: 60 * 5, // 5 minutes
        }
    },
    user: {
        additionalFields: {
            isAdmin: {
                type: "boolean",
                required: true,
                defaultValue: false,
                input: false
            },
            isBanned: {
                type: "boolean",
                required: true,
                defaultValue: false,
                input: false
            },
            banReason: {
                type: "string",
                required: false,
                defaultValue: null,
                input: false
            }
        }
    },
});