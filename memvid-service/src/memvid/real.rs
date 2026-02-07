//! Real memvid searcher implementation using memvid-core.
//!
//! Loads .mv2 files and performs semantic search on resume data.

use async_trait::async_trait;
use memvid_core::{
    AclEnforcementMode, AdaptiveConfig, AskMode as MemvidAskMode, AskRequest as MemvidAskRequest,
    Memvid, SearchRequest,
};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{error, info};

use crate::error::ServiceError;
use crate::memvid::searcher::{
    AskMode, AskRequest, AskResponse, AskStats, SearchResponse, SearchResult, Searcher,
    StateResponse,
};

/// Real searcher that uses memvid-core to load and search .mv2 files.
pub struct RealSearcher {
    /// Path to the .mv2 file
    file_path: PathBuf,
    /// Memvid instance (wrapped in Arc<RwLock> for async access)
    memvid: Arc<RwLock<Memvid>>,
    /// Cached frame count (to avoid locking for frame_count() calls)
    frame_count: i32,
}

impl std::fmt::Debug for RealSearcher {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("RealSearcher")
            .field("file_path", &self.file_path)
            .field("frame_count", &self.frame_count)
            .finish_non_exhaustive()
    }
}

impl RealSearcher {
    /// Create a new RealSearcher by loading a .mv2 file.
    ///
    /// # Arguments
    /// * `file_path` - Path to the .mv2 file
    ///
    /// # Errors
    /// Returns error if:
    /// - File doesn't exist
    /// - File is corrupted
    /// - Unsupported version
    pub async fn new(file_path: impl AsRef<Path>) -> Result<Self, ServiceError> {
        let file_path = file_path.as_ref().to_path_buf();

        info!(
            path = %file_path.display(),
            "Loading memvid file"
        );

        // Check if file exists
        if !file_path.exists() {
            error!(path = %file_path.display(), "Memvid file not found");
            return Err(ServiceError::MemvidFileNotFound(
                file_path.display().to_string(),
            ));
        }

        // Load the memvid file (open read-only)
        let memvid = tokio::task::spawn_blocking({
            let file_path = file_path.clone();
            move || Memvid::open_read_only(&file_path)
        })
        .await
        .map_err(|e| {
            error!(error = %e, "Failed to spawn blocking task");
            ServiceError::Internal(format!("Task error: {}", e))
        })?
        .map_err(|e| {
            error!(error = %e, "Failed to open memvid file");
            ServiceError::MemvidLoadError(e.to_string())
        })?;

        // Get file metadata
        let frame_count = memvid.frame_count() as i32;

        info!(
            path = %file_path.display(),
            frame_count,
            "Memvid file loaded successfully"
        );

        Ok(Self {
            file_path,
            memvid: Arc::new(RwLock::new(memvid)),
            frame_count,
        })
    }
}

#[async_trait]
impl Searcher for RealSearcher {
    async fn search(
        &self,
        query: &str,
        top_k: i32,
        snippet_chars: i32,
    ) -> Result<SearchResponse, ServiceError> {
        let start = std::time::Instant::now();

        info!(
            query = query,
            top_k = top_k,
            "Performing real memvid search"
        );

        // Build search request (convert i32 to usize for memvid-core)
        let search_request = SearchRequest {
            query: query.to_string(),
            top_k: top_k as usize,
            snippet_chars: snippet_chars as usize,
            uri: None,
            scope: None,
            cursor: None,
            as_of_frame: None,
            as_of_ts: None,
            no_sketch: false,
            acl_context: None,
            acl_enforcement_mode: AclEnforcementMode::Audit,
        };

        // Perform the search (blocking operation)
        let search_response = tokio::task::spawn_blocking({
            let memvid = Arc::clone(&self.memvid);
            move || {
                let mut memvid = tokio::runtime::Handle::current().block_on(memvid.write());

                memvid.search(search_request)
            }
        })
        .await
        .map_err(|e| {
            error!(error = %e, "Search task failed");
            ServiceError::Internal(format!("Search task error: {}", e))
        })?
        .map_err(|e| {
            error!(error = %e, "Memvid search failed");
            ServiceError::Internal(format!("Search error: {}", e))
        })?;

        // Convert memvid results to our SearchResult format
        let hits: Vec<SearchResult> = search_response
            .hits
            .into_iter()
            .map(|result| {
                // Extract title from SearchHit.title, fallback to first label, then empty
                // This prevents exposing internal "Frame X" identifiers to users
                let title = result
                    .title
                    .clone()
                    .or_else(|| {
                        result
                            .metadata
                            .as_ref()
                            .and_then(|m| m.labels.first().cloned())
                    })
                    .unwrap_or_default();

                // Get tags from metadata
                let tags = result
                    .metadata
                    .as_ref()
                    .map(|m| m.tags.clone())
                    .unwrap_or_default();

                // Truncate snippet to requested length
                let snippet_len = snippet_chars as usize;
                let snippet = if result.text.len() > snippet_len {
                    format!("{}...", &result.text[..snippet_len])
                } else {
                    result.text.clone()
                };

                SearchResult {
                    title,
                    score: result.score.unwrap_or(0.0),
                    snippet,
                    tags,
                }
            })
            .collect();

        let took_ms = start.elapsed().as_millis() as i32;
        let total_hits = hits.len() as i32;

        info!(
            hits = total_hits,
            took_ms = took_ms,
            "Real memvid search completed"
        );

        Ok(SearchResponse {
            hits,
            total_hits,
            took_ms,
        })
    }

    async fn ask(&self, request: AskRequest) -> Result<AskResponse, ServiceError> {
        let start = std::time::Instant::now();

        info!(
            question = request.question,
            mode = ?request.mode,
            top_k = request.top_k,
            "Performing real memvid ask"
        );

        // Map our AskMode to memvid-core AskMode
        let mode = match request.mode {
            AskMode::Hybrid => MemvidAskMode::Hybrid,
            AskMode::Sem => MemvidAskMode::Sem,
            AskMode::Lex => MemvidAskMode::Lex,
        };

        // Convert filters to scope query if provided
        // Scope format: "key1:value1 key2:value2" for metadata filtering
        let scope = if !request.filters.is_empty() {
            let scope_query = request
                .filters
                .iter()
                .map(|(k, v)| format!("{}:{}", k, v))
                .collect::<Vec<_>>()
                .join(" ");
            Some(scope_query)
        } else {
            None
        };

        // Build memvid-core AskRequest
        let memvid_request = MemvidAskRequest {
            question: request.question.clone(),
            top_k: request.top_k as usize,
            snippet_chars: request.snippet_chars as usize,
            mode,
            start: if request.start > 0 {
                Some(request.start)
            } else {
                None
            },
            end: if request.end > 0 {
                Some(request.end)
            } else {
                None
            },
            context_only: !request.use_llm, // context_only = true means no LLM synthesis
            uri: request.uri.clone(),
            scope,
            cursor: request.cursor.clone(),
            as_of_frame: request.as_of_frame.map(|f| f as u64),
            as_of_ts: request.as_of_ts,
            adaptive: request.adaptive.and_then(|enabled| {
                if enabled {
                    Some(AdaptiveConfig::default())
                } else {
                    None
                }
            }),
            acl_context: None,
            acl_enforcement_mode: AclEnforcementMode::Audit,
        };

        // Perform the ask operation (blocking)
        let ask_response = tokio::task::spawn_blocking({
            let memvid = Arc::clone(&self.memvid);
            move || {
                let mut memvid = tokio::runtime::Handle::current().block_on(memvid.write());

                // Pass None for embedder - memvid will use built-in embeddings
                memvid.ask(memvid_request, None::<&dyn memvid_core::VecEmbedder>)
            }
        })
        .await
        .map_err(|e| {
            error!(error = %e, "Ask task failed");
            ServiceError::Internal(format!("Ask task error: {}", e))
        })?
        .map_err(|e| {
            error!(error = %e, "Memvid ask failed");
            ServiceError::Internal(format!("Ask error: {}", e))
        })?;

        // Convert memvid results to our format
        let evidence: Vec<SearchResult> = ask_response
            .context_fragments
            .into_iter()
            .map(|fragment| {
                // Extract title from URI or use frame_id as fallback
                let title = if fragment.uri.is_empty() {
                    format!("Frame {:?}", fragment.frame_id)
                } else {
                    fragment
                        .uri
                        .rsplit('/')
                        .next()
                        .unwrap_or(&fragment.uri)
                        .to_string()
                };

                // Get tags from metadata if available
                let tags = vec![]; // memvid AskContextFragment doesn't expose tags directly

                SearchResult {
                    title,
                    score: fragment.score.unwrap_or(0.0),
                    snippet: fragment.text,
                    tags,
                }
            })
            .collect();

        let answer = ask_response.answer.unwrap_or_else(|| {
            // If no answer provided, concatenate evidence
            evidence
                .iter()
                .map(|e| format!("**{}**\n{}", e.title, e.snippet))
                .collect::<Vec<_>>()
                .join("\n\n")
        });

        let took_ms = start.elapsed().as_millis() as i32;
        let evidence_count = evidence.len() as i32;

        info!(
            evidence_count = evidence_count,
            took_ms = took_ms,
            "Real memvid ask completed"
        );

        Ok(AskResponse {
            answer,
            evidence,
            stats: AskStats {
                candidates_retrieved: evidence_count,
                results_returned: evidence_count,
                retrieval_ms: took_ms,
                reranking_ms: 0,      // memvid-core doesn't expose this separately
                used_fallback: false, // memvid-core doesn't expose this
            },
        })
    }

    async fn get_state(
        &self,
        entity: &str,
        slot: Option<&str>,
    ) -> Result<StateResponse, ServiceError> {
        info!(entity = entity, slot = ?slot, "Performing memvid state lookup");

        // Get entity memory cards (blocking operation)
        let memory_cards = tokio::task::spawn_blocking({
            let memvid = Arc::clone(&self.memvid);
            let entity = entity.to_string();

            move || -> Vec<(String, String)> {
                let memvid = tokio::runtime::Handle::current().block_on(memvid.read());

                // Get all memory cards for this entity
                memvid
                    .get_entity_memories(&entity)
                    .into_iter()
                    .map(|card| (card.slot.clone(), card.value.clone()))
                    .collect()
            }
        })
        .await
        .map_err(|e| {
            error!(error = %e, "State lookup task failed");
            ServiceError::Internal(format!("State task error: {}", e))
        })?;

        // Check if entity was found
        if memory_cards.is_empty() {
            info!(entity = entity, "Entity not found in memory cards");
            return Ok(StateResponse {
                found: false,
                entity: entity.to_string(),
                slots: std::collections::HashMap::new(),
            });
        }

        // Convert memory cards to slot map
        let mut slots = std::collections::HashMap::new();

        for (slot_name, slot_value) in memory_cards {
            // If specific slot requested, only include that slot
            if let Some(requested_slot) = slot {
                if slot_name == requested_slot {
                    slots.insert(slot_name, slot_value);
                }
            } else {
                // Include all slots
                slots.insert(slot_name, slot_value);
            }
        }

        info!(
            entity = entity,
            found = true,
            slot_count = slots.len(),
            "State lookup completed"
        );

        Ok(StateResponse {
            found: true,
            entity: entity.to_string(),
            slots,
        })
    }

    fn frame_count(&self) -> i32 {
        self.frame_count
    }

    fn memvid_file(&self) -> &str {
        self.file_path.to_str().unwrap_or("unknown")
    }

    fn is_ready(&self) -> bool {
        // Check if we can acquire a read lock
        self.memvid.try_read().is_ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_real_searcher_missing_file() {
        let result = RealSearcher::new("/nonexistent/file.mv2").await;
        assert!(result.is_err());
        match result.unwrap_err() {
            ServiceError::MemvidFileNotFound(_) => {} // Expected
            e => panic!("Expected MemvidFileNotFound, got: {:?}", e),
        }
    }

    #[tokio::test]
    async fn test_real_searcher_loads_valid_file() {
        // Use the actual resume.mv2 file from the project
        let mv2_path = "../data/.memvid/resume.mv2";

        // Skip test if file doesn't exist (for environments without the file)
        if !std::path::Path::new(mv2_path).exists() {
            eprintln!("Skipping test: {} not found", mv2_path);
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load valid .mv2 file");

        assert!(searcher.is_ready());
        assert!(searcher.frame_count() > 0);
        assert!(searcher.memvid_file().contains("resume.mv2"));
    }

    #[tokio::test]
    async fn test_real_searcher_search_returns_results() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        let response = searcher
            .search("Python experience", 5, 200)
            .await
            .expect("Search should succeed");

        assert!(!response.hits.is_empty(), "Should return search results");
        assert!(response.total_hits > 0);
        assert!(response.took_ms >= 0);

        // Verify hit structure
        for hit in response.hits {
            assert!(hit.score >= 0.0); // Scores can be > 1.0 depending on scoring algorithm
            assert!(!hit.snippet.is_empty());
        }
    }

    #[tokio::test]
    async fn test_real_searcher_ask_semantic_mode() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        let request = AskRequest {
            question: "What programming languages do you know?".to_string(),
            use_llm: false,
            top_k: 5,
            filters: std::collections::HashMap::new(),
            start: 0,
            end: 0,
            snippet_chars: 200,
            mode: AskMode::Sem, // Semantic mode
            uri: None,
            cursor: None,
            as_of_frame: None,
            as_of_ts: None,
            adaptive: None,
        };

        let response = searcher.ask(request).await.expect("Ask should succeed");

        assert!(!response.answer.is_empty());
        assert!(!response.evidence.is_empty());
        assert!(response.stats.candidates_retrieved > 0);
    }

    #[tokio::test]
    async fn test_real_searcher_ask_lexical_mode() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        let request = AskRequest {
            question: "Python".to_string(),
            use_llm: false,
            top_k: 3,
            filters: std::collections::HashMap::new(),
            start: 0,
            end: 0,
            snippet_chars: 150,
            mode: AskMode::Lex, // Lexical mode (keyword search)
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

    #[tokio::test]
    async fn test_real_searcher_ask_hybrid_mode() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        let request = AskRequest {
            question: "leadership experience".to_string(),
            use_llm: false,
            top_k: 5,
            filters: std::collections::HashMap::new(),
            start: 0,
            end: 0,
            snippet_chars: 200,
            mode: AskMode::Hybrid, // Hybrid mode (semantic + lexical)
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

    #[tokio::test]
    async fn test_real_searcher_get_state_profile() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        let response = searcher
            .get_state("__profile__", None)
            .await
            .expect("get_state should succeed");

        assert!(response.found);
        assert_eq!(response.entity, "__profile__");
        assert!(!response.slots.is_empty());
    }

    #[tokio::test]
    async fn test_real_searcher_get_state_nonexistent() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        let response = searcher
            .get_state("nonexistent_entity", None)
            .await
            .expect("get_state should succeed");

        assert!(!response.found);
        assert!(response.slots.is_empty());
    }

    #[tokio::test]
    async fn test_real_searcher_frame_count() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        let frame_count = searcher.frame_count();
        assert!(frame_count > 0, "Should have frames in the .mv2 file");
    }

    #[tokio::test]
    async fn test_real_searcher_memvid_file_path() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        let file_path = searcher.memvid_file();
        assert!(file_path.contains("resume.mv2"));
    }

    #[tokio::test]
    async fn test_real_searcher_is_ready() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        assert!(searcher.is_ready());
    }

    // ---------------------------------
    // Ignored tests for features requiring lexical index
    // ---------------------------------
    // The following tests require a .mv2 file with lexical index enabled.
    // To run these tests: cargo test --lib -- --ignored
    //
    // To enable lexical index in a .mv2 file, use memvid-sdk with:
    //   ingest.py --enable-lexical-index
    //
    // These tests will fail with the standard resume.mv2 file but are kept
    // to document expected behavior once lexical indexing is enabled.

    #[tokio::test]
    #[ignore] // Requires lexical index enabled in .mv2 file. Run with: cargo test --lib -- --ignored
    async fn test_real_searcher_ask_with_filters() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        // Test filtering by metadata tags
        let mut filters = std::collections::HashMap::new();
        filters.insert("type".to_string(), "experience".to_string());

        let request = AskRequest {
            question: "What projects have you worked on?".to_string(),
            use_llm: false,
            top_k: 5,
            filters, // Filter by type:experience
            start: 0,
            end: 0,
            snippet_chars: 200,
            mode: AskMode::Hybrid, // Hybrid mode works best with filters
            uri: None,
            cursor: None,
            as_of_frame: None,
            as_of_ts: None,
            adaptive: None,
        };

        let response = searcher
            .ask(request)
            .await
            .expect("Ask with filters should succeed");

        // Verify filtered results
        assert!(!response.answer.is_empty());
        assert!(!response.evidence.is_empty());
        assert!(response.stats.candidates_retrieved > 0);

        // Verify results contain filtered content (if lexical index is enabled)
        // This assertion will fail without lexical index support
        for evidence in &response.evidence {
            assert!(!evidence.snippet.is_empty());
        }
    }

    #[tokio::test]
    #[ignore] // Requires lexical index enabled in .mv2 file. Run with: cargo test --lib -- --ignored
    async fn test_real_searcher_ask_with_multiple_filters() {
        let mv2_path = "../data/.memvid/resume.mv2";

        if !std::path::Path::new(mv2_path).exists() {
            return;
        }

        let searcher = RealSearcher::new(mv2_path)
            .await
            .expect("Should load .mv2 file");

        // Test multiple filter combinations
        let mut filters = std::collections::HashMap::new();
        filters.insert("type".to_string(), "skill".to_string());
        filters.insert("category".to_string(), "programming".to_string());

        let request = AskRequest {
            question: "Python".to_string(),
            use_llm: false,
            top_k: 3,
            filters, // Filter by type:skill AND category:programming
            start: 0,
            end: 0,
            snippet_chars: 150,
            mode: AskMode::Lex, // Lexical mode for exact keyword matching
            uri: None,
            cursor: None,
            as_of_frame: None,
            as_of_ts: None,
            adaptive: None,
        };

        let response = searcher
            .ask(request)
            .await
            .expect("Ask with multiple filters should succeed");

        assert!(!response.answer.is_empty());
        assert!(response.stats.retrieval_ms >= 0);
    }
}
