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
