import { tryCatch } from './result';

const DNS_ENDPOINT = 'https://cloudflare-dns.com/dns-query';

export type DNSError = {
    code: string;
    status: number;
    message: string;
};

export async function verifyDomainTXT(domain: string, expectedValue: string) {
    const cleanedDomain = domain.replace(/^https?:\/\//, '');
    const fetchDNS = async () => {
        const response = await fetch(
            `${DNS_ENDPOINT}?name=${encodeURIComponent(cleanedDomain)}&type=TXT`,
            {
                method: 'GET',
                headers: { 'Accept': 'application/dns-json' },
                cache: 'no-cache'
            }
        );

        if (!response.ok) {
            const errorMessages: Record<number, string> = {
                400: 'Invalid DNS query',
                413: 'DNS query too large',
                415: 'Unsupported content type',
                504: 'DNS resolver timeout'
            };

            throw {
                code: 'DNS_ERROR',
                status: response.status,
                message: errorMessages[response.status] || `DNS query failed: ${response.statusText}`
            } as DNSError;
        }

        const data = await response.json();

        if (!data.Answer) return false;

        return data.Answer.some((record: any) =>
            record.data.replace(/^"(.*)"$/, '$1') === expectedValue
        );
    };

    return tryCatch<boolean, DNSError>(fetchDNS());
}

export function generateVerificationToken(domain: string): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2);
    const domainHash = domain.replace(/[^a-z0-9]/gi, '').toLowerCase();
    return `vyntr-verify=${timestamp}-${domainHash}-${random}`;
}
