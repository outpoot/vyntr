import type { ArticleData } from './article';
import type { TimeUnit } from '$lib/utils/date';
import type { UnitCategory } from '$lib/utils/units';

export type SearchDetailType = 'bliptext' | 'person' | 'calculator' | 'movie' | 'date' | 'word' | 'currency' | 'unitConversion';

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

export interface Definition {
    pos: string;
    gloss: string;
    source?: string;
}

export interface WordDefinitionSearchDetail extends BaseSearchDetail {
    type: 'word';
    word: string;
    partOfSpeech?: string | null;
    pronunciations?: string[] | null;
    definitions?: Definition[] | null;
    examples?: string[] | null;
    synonyms?: string[] | null;
    similarWords?: string[] | null;
}

export interface CurrencySearchDetail extends BaseSearchDetail {
    type: 'currency';
    from: {
        code: string;
        name: string;
        amount: number;
    };
    to: {
        code: string;
        name: string;
        amount: number;
    };
    rate: number;
    lastUpdated: string | null;
}

export interface UnitConversionSearchDetail extends BaseSearchDetail {
    type: 'unitConversion';
    value: number;
    fromUnit: string;
    toUnit: string;
    category: UnitCategory;
    result: number;
    formattedResult: string;
}

export type SearchDetail =
    | BliptextSearchDetail
    | PersonSearchDetail
    | CalculatorSearchDetail
    | MovieSearchDetail
    | DateSearchDetail
    | WordDefinitionSearchDetail
    | CurrencySearchDetail
    | UnitConversionSearchDetail;

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
    word: WordDefinitionSearchDetail | null;
    currency: CurrencySearchDetail | null;
    unitConversion: UnitConversionSearchDetail | null;
    ai_summaries: string | null;
}
