import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { apiKey } from "better-auth/plugins";
import { env } from '$env/dynamic/private';
import {
    PUBLIC_PRODUCT_ID_PREMIUM,
    PUBLIC_PRODUCT_ID_10000,
    PUBLIC_PRODUCT_ID_50000,
    PUBLIC_PRODUCT_ID_100000
} from '$env/static/public';
import { db } from "./server/db";
import { polar } from "@polar-sh/better-auth";
import { Polar } from "@polar-sh/sdk";
import { eq } from "drizzle-orm";
import { apikey } from "./server/schema";

if (!env.GOOGLE_CLIENT_ID) throw new Error('GOOGLE_CLIENT_ID is not set');
if (!env.GOOGLE_CLIENT_SECRET) throw new Error('GOOGLE_CLIENT_SECRET is not set');
if (!env.POLAR_ACCESS_TOKEN) throw new Error('POLAR_ACCESS_TOKEN is not set');
if (!env.POLAR_WEBHOOK_SECRET) throw new Error('POLAR_WEBHOOK_SECRET is not set');
if (!PUBLIC_PRODUCT_ID_PREMIUM) throw new Error('PUBLIC_PRODUCT_ID_PREMIUM is not set');
if (!PUBLIC_PRODUCT_ID_10000) throw new Error('PUBLIC_PRODUCT_ID_10000 is not set');
if (!PUBLIC_PRODUCT_ID_50000) throw new Error('PUBLIC_PRODUCT_ID_50000 is not set');
if (!PUBLIC_PRODUCT_ID_100000) throw new Error('PUBLIC_PRODUCT_ID_100000 is not set');

export const polarClient = new Polar({
    accessToken: env.POLAR_ACCESS_TOKEN,
});

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
        }),
        polar({
            client: polarClient,
            createCustomerOnSignUp: true,
            // Enable customer portal
            enableCustomerPortal: true, // Deployed under /portal for authenticated users

            checkout: {
                enabled: true,
                products: [
                    {
                        productId: PUBLIC_PRODUCT_ID_PREMIUM,
                        slug: "premium"
                    },
                    {
                        productId: PUBLIC_PRODUCT_ID_10000,
                        slug: "10000"
                    },
                    {
                        productId: PUBLIC_PRODUCT_ID_50000,
                        slug: "50000"
                    },
                    {
                        productId: PUBLIC_PRODUCT_ID_100000,
                        slug: "100000"
                    }
                ],
                successUrl: "/success?checkout_id={CHECKOUT_ID}&product={PRODUCT_SLUG}"
            },
            webhooks: {
                secret: env.POLAR_WEBHOOK_SECRET,
                onPayload: async (_) => { },
                onOrderCreated: async (payload) => {
                    const productId = payload.data.productId;
                    const userId = payload.data.customer.externalId as string;

                    const userApiKeys = await db
                        .select()
                        .from(apikey)
                        .where(eq(apikey.userId, userId));

                    const keyToUpdate = userApiKeys[0];

                    const credits = {
                        [PUBLIC_PRODUCT_ID_10000]: 10_000,
                        [PUBLIC_PRODUCT_ID_50000]: 50_000,
                        [PUBLIC_PRODUCT_ID_100000]: 100_000
                    }[productId];

                    if (credits) {
                        const currentRemaining = keyToUpdate.remaining ?? 0;
                        const newRemaining = currentRemaining + credits;

                        await auth.api.updateApiKey({
                            body: {
                                keyId: keyToUpdate.id,
                                userId: userId,
                                remaining: newRemaining
                            }
                        });
                    } else {
                        console.log(`Product ${productId} does not correspond to credit purchase.`);
                    }
                },
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