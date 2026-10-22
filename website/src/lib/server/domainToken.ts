import { createHmac } from 'node:crypto';
import { env } from '$env/dynamic/private';

export function normalizeHost(input: unknown): string | null {
    if (typeof input !== 'string') return null;
    const host = input.trim().toLowerCase()
        .replace(/^https?:\/\//, '')
        .replace(/[\/?#].*$/, '')
        .replace(/\.$/, '');
    if (host.length > 253) return null;
    if (!/^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/.test(host)) return null;
    return host;
}

export function verificationTokenFor(userId: string, host: string): string {
    const secret = env.PRIVATE_BETTER_AUTH_SECRET;
    if (!secret) throw new Error('PRIVATE_BETTER_AUTH_SECRET is not set');
    const mac = createHmac('sha256', secret).update(`vyntr-domain-verify:${userId}:${host}`).digest('hex');
    return `vyntr-verify=${mac.slice(0, 40)}`;
}
