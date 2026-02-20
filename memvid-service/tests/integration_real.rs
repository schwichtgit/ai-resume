//! Integration tests for RealSearcher (real.rs) using an actual .mv2 file.
//!
//! These tests require a real .mv2 file to be available. They are gated by
//! the `TEST_MV2_PATH` environment variable -- if unset, tests skip gracefully.
//!
//! In CI, the `memvid-integration` job runs ingest to produce a .mv2 file,
//! then sets `TEST_MV2_PATH` before invoking cargo tarpaulin.

use ai_resume_memvid::memvid::{AskMode, AskRequest, RealSearcher, Searcher};
use std::collections::HashMap;

/// Helper: return the .mv2 path from env, or None to skip the test.
fn mv2_path() -> Option<String> {
    std::env::var("TEST_MV2_PATH")
        .ok()
        .filter(|p| !p.is_empty())
}

/// Convenience macro to skip tests when TEST_MV2_PATH is not set.
macro_rules! require_mv2 {
    () => {
        match mv2_path() {
            Some(p) => p,
            None => {
                eprintln!("TEST_MV2_PATH not set -- skipping integration test");
                return;
            }
        }
    };
}

// ---------------------------------------------------------------------------
// Error cases (always runnable, no .mv2 needed)
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_real_searcher_missing_file_returns_error() {
    let result = RealSearcher::new("/nonexistent/path/to/file.mv2").await;
    assert!(result.is_err(), "Opening a missing file should fail");
    let err_msg = format!("{}", result.unwrap_err());
    assert!(
        err_msg.contains("not found") || err_msg.contains("Memvid file not found"),
        "Error should mention file not found, got: {}",
        err_msg
    );
}

#[tokio::test]
async fn test_real_searcher_empty_path_returns_error() {
    let result = RealSearcher::new("").await;
    assert!(result.is_err(), "Opening an empty path should fail");
}

// ---------------------------------------------------------------------------
// Loading and metadata
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_load_mv2_file_succeeds() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load valid .mv2 file");

    assert!(
        searcher.is_ready(),
        "Searcher should be ready after loading"
    );
    assert!(
        searcher.frame_count() > 0,
        "Frame count should be positive, got {}",
        searcher.frame_count()
    );
}

#[tokio::test]
async fn test_memvid_file_returns_path() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let reported = searcher.memvid_file();
    assert!(
        reported.contains(".mv2"),
        "memvid_file() should contain '.mv2', got: {}",
        reported
    );
}

#[tokio::test]
async fn test_is_ready_after_load() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    assert!(searcher.is_ready());
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_search_returns_results() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let response = searcher
        .search("programming languages", 5, 200)
        .await
        .expect("Search should succeed");

    assert!(
        !response.hits.is_empty(),
        "Search for 'programming languages' should return hits"
    );
    assert!(response.total_hits > 0);
    assert!(response.took_ms >= 0);

    // Verify hit structure
    for hit in &response.hits {
        assert!(!hit.snippet.is_empty(), "Each hit should have a snippet");
        assert!(hit.score >= 0.0, "Score should be non-negative");
    }
}

#[tokio::test]
async fn test_search_respects_top_k() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let response = searcher
        .search("experience", 2, 200)
        .await
        .expect("Search should succeed");

    assert!(
        response.hits.len() <= 2,
        "Should return at most top_k=2 hits, got {}",
        response.hits.len()
    );
}

#[tokio::test]
async fn test_search_snippet_truncation() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let snippet_chars = 50;
    let response = searcher
        .search("experience", 3, snippet_chars)
        .await
        .expect("Search should succeed");

    for hit in &response.hits {
        // snippet_chars + "..." suffix = max snippet_chars + 3
        assert!(
            hit.snippet.len() <= (snippet_chars as usize) + 3,
            "Snippet should be truncated to ~{} chars, got {} chars",
            snippet_chars,
            hit.snippet.len()
        );
    }
}

// ---------------------------------------------------------------------------
// Ask -- semantic mode
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_ask_semantic_mode() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let request = AskRequest {
        question: "What programming languages are listed?".to_string(),
        use_llm: false,
        top_k: 5,
        filters: HashMap::new(),
        start: 0,
        end: 0,
        snippet_chars: 200,
        mode: AskMode::Sem,
        uri: None,
        cursor: None,
        as_of_frame: None,
        as_of_ts: None,
        adaptive: None,
    };

    let response = searcher.ask(request).await.expect("Ask should succeed");

    assert!(!response.answer.is_empty(), "Answer should not be empty");
    assert!(
        !response.evidence.is_empty(),
        "Evidence should not be empty"
    );
    assert!(
        response.stats.candidates_retrieved > 0,
        "Should retrieve candidates"
    );
    assert!(response.stats.retrieval_ms >= 0);
}

// ---------------------------------------------------------------------------
// Ask -- lexical mode
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_ask_lexical_mode() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let request = AskRequest {
        question: "Python".to_string(),
        use_llm: false,
        top_k: 3,
        filters: HashMap::new(),
        start: 0,
        end: 0,
        snippet_chars: 150,
        mode: AskMode::Lex,
        uri: None,
        cursor: None,
        as_of_frame: None,
        as_of_ts: None,
        adaptive: None,
    };

    let response = searcher.ask(request).await.expect("Ask should succeed");

    assert!(!response.answer.is_empty());
    assert!(!response.evidence.is_empty());
}

// ---------------------------------------------------------------------------
// Ask -- hybrid mode
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_ask_hybrid_mode() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let request = AskRequest {
        question: "leadership and team management".to_string(),
        use_llm: false,
        top_k: 5,
        filters: HashMap::new(),
        start: 0,
        end: 0,
        snippet_chars: 200,
        mode: AskMode::Hybrid,
        uri: None,
        cursor: None,
        as_of_frame: None,
        as_of_ts: None,
        adaptive: None,
    };

    let response = searcher.ask(request).await.expect("Ask should succeed");

    assert!(!response.answer.is_empty());
    assert!(response.stats.retrieval_ms >= 0);
}

// ---------------------------------------------------------------------------
// Ask -- context_only (use_llm = false)
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_ask_context_only_mode() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let request = AskRequest {
        question: "What is the candidate's name?".to_string(),
        use_llm: false, // context_only = true in memvid-core
        top_k: 3,
        filters: HashMap::new(),
        start: 0,
        end: 0,
        snippet_chars: 300,
        mode: AskMode::Sem,
        uri: None,
        cursor: None,
        as_of_frame: None,
        as_of_ts: None,
        adaptive: None,
    };

    let response = searcher.ask(request).await.expect("Ask should succeed");

    // In context_only mode, answer is built from evidence concatenation
    assert!(!response.answer.is_empty());
    assert!(!response.evidence.is_empty());
}

// ---------------------------------------------------------------------------
// get_state -- profile entity
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_get_state_profile() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let response = searcher
        .get_state("__profile__", None)
        .await
        .expect("get_state should succeed");

    assert!(response.found, "Profile entity should be found");
    assert_eq!(response.entity, "__profile__");
    assert!(
        !response.slots.is_empty(),
        "Profile should have at least one slot"
    );
}

// ---------------------------------------------------------------------------
// get_state -- nonexistent entity
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_get_state_nonexistent_entity() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let response = searcher
        .get_state("__does_not_exist_xyz__", None)
        .await
        .expect("get_state should succeed even for missing entity");

    assert!(!response.found);
    assert!(response.slots.is_empty());
}

// ---------------------------------------------------------------------------
// get_state -- specific slot filter
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_get_state_with_slot_filter() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    // First get all slots to find a valid one
    let all_response = searcher
        .get_state("__profile__", None)
        .await
        .expect("get_state should succeed");

    if all_response.found && !all_response.slots.is_empty() {
        // Pick the first slot name and request only that one
        let slot_name = all_response.slots.keys().next().unwrap().clone();
        let filtered = searcher
            .get_state("__profile__", Some(&slot_name))
            .await
            .expect("get_state with slot filter should succeed");

        assert!(filtered.found);
        assert!(
            filtered.slots.len() <= 1,
            "Filtering by slot should return at most 1 slot, got {}",
            filtered.slots.len()
        );
        if !filtered.slots.is_empty() {
            assert!(
                filtered.slots.contains_key(&slot_name),
                "Filtered result should contain the requested slot"
            );
        }
    }
}

// ---------------------------------------------------------------------------
// Debug trait implementation
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_real_searcher_debug_impl() {
    let path = require_mv2!();
    let searcher = RealSearcher::new(&path)
        .await
        .expect("Should load .mv2 file");

    let debug_str = format!("{:?}", searcher);
    assert!(
        debug_str.contains("RealSearcher"),
        "Debug output should contain 'RealSearcher'"
    );
    assert!(
        debug_str.contains("file_path"),
        "Debug output should contain 'file_path'"
    );
    assert!(
        debug_str.contains("frame_count"),
        "Debug output should contain 'frame_count'"
    );
}
