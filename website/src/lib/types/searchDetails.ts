import type { ArticleData } from './article';

export type SearchDetailType = 'bliptext' | 'person' | 'calculator' | 'movie';

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

export type SearchDetail = 
    | BliptextSearchDetail 
    | PersonSearchDetail 
    | CalculatorSearchDetail 
    | MovieSearchDetail;
