import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { env } from '$env/dynamic/private';
import * as schema from './schema';

if (!env.DATABASE_URL) throw new Error('DATABASE_URL is not set');
/**
 * Cache the database connection in development. This avoids creating a new connection on every HMR
 * update.
 */
const globalForDb = globalThis as unknown as {
    client: postgres.Sql | undefined;
};

const client = globalForDb.client ?? postgres(env.DATABASE_URL);
if (env.NODE_ENV !== 'production') globalForDb.client = client;

export const db = drizzle(client, { schema });