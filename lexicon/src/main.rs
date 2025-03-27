use actix_web::{get, web, App, HttpResponse, HttpServer, Responder};
use fuzzy_matcher::skim::SkimMatcherV2;
use fuzzy_matcher::FuzzyMatcher;
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::{self, BufReader};
use std::time::Instant;

#[derive(Deserialize, Serialize, Debug, Clone)]
#[serde(rename_all = "camelCase")]
struct WordEntry {
    word: String,
    id: String,
    part_of_speech: String,
    #[serde(default)]
    pronunciations: Option<Vec<String>>,
    #[serde(default)]
    definitions: Option<Vec<Definition>>,
    #[serde(default)]
    examples: Option<Vec<String>>,
    #[serde(default)]
    synonyms: Option<Vec<String>>,
    #[serde(default)]
    antonyms: Option<Vec<String>>,
    #[serde(default)]
    similar_words: Option<Vec<String>>,
}

#[derive(Deserialize, Serialize, Debug, Clone)]
struct Definition {
    pos: String,
    gloss: String,
    #[serde(default)]
    source: Option<String>,
}

#[derive(Serialize, Debug, Clone)]
struct MatchResult {
    score: i64,
    entry: WordEntry,
}

struct AppState {
    word_entries: Vec<WordEntry>,
    matcher: SkimMatcherV2,
}

const EXACT_MATCH_BOOST: i64 = 1_000_000;

fn load_wordnet_data(file_path: &str) -> io::Result<Vec<WordEntry>> {
    println!("Loading WordNet data from {}...", file_path);
    let start = Instant::now();
    let file = File::open(file_path)?;
    let reader = BufReader::new(file);
    let entries: Vec<WordEntry> = serde_json::from_reader(reader)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    let duration = start.elapsed();
    println!("Loaded {} entries in {:.2?}", entries.len(), duration);
    Ok(entries)
}

#[get("/lookup/{term}")]
async fn lookup_handler(term: web::Path<String>, data: web::Data<AppState>) -> impl Responder {
    let search_term = term.into_inner();
    println!("Received lookup request for: {}", search_term);
    let start = Instant::now();

    let matcher = &data.matcher;

    let results: Vec<MatchResult> = data
        .word_entries
        .iter()
        .filter_map(|entry| {
            let search_lower = search_term.to_lowercase();
            let entry_lower = entry.word.to_lowercase();

            matcher
                .fuzzy_match(&entry_lower, &search_lower)
                .map(|mut score| {
                    if entry_lower == search_lower {
                        score += EXACT_MATCH_BOOST;
                    }
                    MatchResult {
                        score,
                        entry: entry.clone(),
                    }
                })
        })
        .collect();

    let mut results = results;
    results.sort_unstable_by(|a, b| b.score.cmp(&a.score));

    let top_n = 10;
    results.truncate(top_n);

    let duration = start.elapsed();
    println!(
        "Lookup for '{}' completed in {:.2?}, found {} potential matches (top {} returned)",
        search_term,
        duration,
        results.len(),
        top_n
    );

    HttpResponse::Ok().json(results)
}

#[actix_web::main]
async fn main() -> io::Result<()> {
    let data_file = "wn.json";

    let word_entries = load_wordnet_data(data_file).expect("Failed to load WordNet data file");

    let app_state = web::Data::new(AppState {
        word_entries,
        matcher: SkimMatcherV2::default(),
    });

    println!("Starting server at http://127.0.0.1:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(lookup_handler)
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
