CREATE TABLE sites (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    language VARCHAR(10),
    title TEXT,
    canonical_url TEXT,
    content_text TEXT
);

CREATE TABLE meta_tags (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES sites(id),
    name TEXT,
    content TEXT
);
