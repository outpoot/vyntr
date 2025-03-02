CREATE TABLE sites (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    language TEXT,
    title TEXT,
    canonical_url TEXT,
    content_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE meta_tags (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES sites(id),
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);