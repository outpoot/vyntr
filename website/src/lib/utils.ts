import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

export function formatLastUpdated(timestamp: string | null): string {
	if (!timestamp) return 'Unknown';

	try {
		const date = new Date(timestamp);

		const options: Intl.DateTimeFormatOptions = {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit',
			timeZone: 'UTC',
			timeZoneName: 'short'
		};

		return date.toLocaleString('en-US', options);
	} catch (e) {
		return 'Unknown date';
	}
}

export function formatAmount(amount: number) {
	return amount.toLocaleString(undefined, {
		maximumFractionDigits: amount < 0.01
			? Math.max(2, -Math.floor(Math.log10(amount)) + 2)
			: 2
	});
}

export function formatCompactNumber(num: number): string {
	if (num < 1000) return num.toString();

	const formatter = Intl.NumberFormat('en', { notation: 'compact' });
	return formatter.format(num);
}

export function formatDateFriendly(dateStr: number): string {
	const date = new Date(dateStr);
	const today = new Date();
	const yesterday = new Date(today);
	yesterday.setDate(yesterday.getDate() - 1);

	if (date.toDateString() === today.toDateString()) {
		return 'Today';
	}
	if (date.toDateString() === yesterday.toDateString()) {
		return 'Yesterday';
	}

	return date.toLocaleDateString('en-US', {
		month: 'long',
		day: 'numeric',
		year: 'numeric'
	});
}

export function getFavicon(url: string) {
	try {
		const domain = url;
		const urlObj = new URL(domain.startsWith('http') ? domain : `https://${domain}`);
		return `https://www.google.com/s2/favicons?domain=${urlObj.hostname}&sz=32`;
	} catch (err) {
		return '';
	}
}