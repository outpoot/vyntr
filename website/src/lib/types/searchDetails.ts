import type { ArticleData } from './article';
import type { TimeUnit } from '$lib/dateUtils';

export type SearchDetailType = 'bliptext' | 'person' | 'calculator' | 'movie' | 'date';

interface BaseSearchDetail {
    type: SearchDetailType;
}

export interface BliptextSearchDetail {
    type: 'bliptext';
    article: ArticleData;
}

export interface PersonSearchDetail extends BaseSearchDetail {
    type: 'person';
    name: string;
    occupation: string[];
    bio: string;
    image?: string;
    birthDate?: string;
    birthPlace?: string;
}

export interface CalculatorSearchDetail extends BaseSearchDetail {
    type: 'calculator';
    expression: string;
    result: string;
}

export interface MovieSearchDetail extends BaseSearchDetail {
    type: 'movie';
    title: string;
    director: string;
    year: string;
    cast: string[];
    poster?: string;
    rating?: string;
    runtime?: string;
}

export interface DateSearchDetail extends BaseSearchDetail {
    type: 'date';
    value: number;
    description: string;
    date: string;
    displayText: string;
    unit: TimeUnit;
}

export type SearchDetail =
    | BliptextSearchDetail
    | PersonSearchDetail
    | CalculatorSearchDetail
    | MovieSearchDetail
    | DateSearchDetail;

export interface WebSearchResult {
    favicon: string;
    title: string;
    url: string;
    pageTitle: string;
    date: string;
    preview: string;
}

export interface SearchResponse {
    web: WebSearchResult[];
    bliptext: BliptextSearchDetail | null;
    date: DateSearchDetail | null;
}
