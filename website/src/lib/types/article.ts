export interface ArticleSummaryKey {
    key: string;
    value: string;
}

export interface ArticleSummary {
    image?: {
        url: string;
        caption: string;
    };
    keys: ArticleSummaryKey[];
    introduction?: string;
}

export interface ArticleData {
    slug: string;
    title: string;
    content: string;
    summary: ArticleSummary;
}

export interface SearchScore {
    slug: string;
    title: string;
    score: number;
}

export interface SearchResults {
    scores: SearchScore[];
    bestMatch: ArticleData | null;
}
