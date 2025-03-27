import postgres from "postgres";
import type { BunRequest, Server } from "bun";
import { config } from "dotenv";
import path from "path";

const scriptDir = import.meta.dir;
const envPath = path.resolve(scriptDir, "../.env");

config({ path: envPath });
console.log("Starting Bun WordNet API server...");

// --- Configuration ---
const DATABASE_URL = process.env.PRIVATE_DB_URL;
const PORT = process.env.PORT || 3000;
const SIMILARITY_THRESHOLD: number = 0.3;
const LIMIT_RESULTS: number = 10;
// --- End Configuration ---

// --- Type Definitions ---
interface Definition {
    pos: string;
    gloss: string;
    source?: string;
}

interface WordEntryResponse {
    id: string;
    word: string;
    partOfSpeech?: string | null;
    pronunciations?: string[] | null;
    definitions?: Definition[] | null;
    examples?: string[] | null;
    synonyms?: string[] | null;
    antonyms?: string[] | null;
    similarWords?: string[] | null;
}

interface MatchResult {
    similarity: number;
    entry: WordEntryResponse;
}

// --- Database Connection ---
if (!DATABASE_URL) {
    console.error("FATAL: PRIVATE_DB_URL environment variable is not set.");
    process.exit(1);
}

const sql = postgres(DATABASE_URL, {});

console.log(`Database connection established.`);

// --- API ---
const server = Bun.serve({
    port: PORT,

    async fetch(req: Request, server: Server): Promise<Response> {
        const url = new URL(req.url);
        const pathSegments = url.pathname.split("/").filter(Boolean);

        if (req.method === "GET" && url.pathname === "/health") {
            return new Response("OK");
        }

        if (
            req.method === "GET" &&
            pathSegments.length === 2 && // expecting ["lookup", "term"]
            pathSegments[0] === "lookup"
        ) {
            const searchTerm = decodeURIComponent(pathSegments[1]);

            console.log(`Received request for term: ${searchTerm}`);
            try {
                const rows = await sql<
                    { similarity: number; data: WordEntryResponse }[]
                >`
              SELECT
                  similarity(word, ${searchTerm}) AS similarity,
                  json_build_object(
                      'id', id,
                      'word', word,
                      'partOfSpeech', part_of_speech,
                      'pronunciations', pronunciations,
                      'definitions', definitions,
                      'examples', examples,
                      'synonyms', synonyms,
                      'antonyms', antonyms,
                      'similarWords', similar_words
                  ) as data
              FROM wordnet
              WHERE word % ${searchTerm} AND similarity(word, ${searchTerm}) >= ${SIMILARITY_THRESHOLD}
              ORDER BY
                  (word = ${searchTerm}) DESC,
                  similarity DESC
              LIMIT ${LIMIT_RESULTS};
            `;

                const results: MatchResult[] = rows.map((row) => ({
                    similarity: row.similarity,
                    entry: row.data,
                }));

                return Response.json(results, { status: 200 });
            } catch (error) {
                console.error(`Database query failed for term '${searchTerm}':`, error);

                return new Response("Failed to query database", { status: 500 });
            }
        }
        return new Response("Not Found", { status: 404 });
    },

    error(error: Error): Response {
        console.error("Server Error:", error);
        return new Response("Internal Server Error", { status: 500 })
    },
});

console.log(`Bun server listening on http://localhost:${server.port}`);