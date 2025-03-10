CREATE INDEX IF NOT EXISTS idx_sites_id ON sites(id);
CREATE INDEX IF NOT EXISTS idx_meta_tags_analysis_id ON meta_tags(analysis_id);

DROP INDEX IF EXISTS idx_sites_indexed_id;
DROP MATERIALIZED VIEW IF EXISTS sites_indexed;

CREATE MATERIALIZED VIEW sites_indexed AS
SELECT 
    s.id,
    s.url,
    s.title,
    s.content_text,
    string_agg(format('%s: %s', mt.name, mt.content), ' ') as meta_content
FROM sites s
LEFT JOIN meta_tags mt ON s.id = mt.analysis_id
GROUP BY s.id, s.url, s.title, s.content_text;

CREATE INDEX CONCURRENTLY idx_sites_indexed_id ON sites_indexed(id);
CLUSTER sites_indexed USING idx_sites_indexed_id;
