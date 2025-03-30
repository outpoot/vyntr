CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_wordnet_word_lower_trgm ON wordnet USING gist (lower(word) gist_trgm_ops);