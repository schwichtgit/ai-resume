//! Real memvid searcher implementation using memvid-core.
//!
//! Loads .mv2 files and performs semantic search on resume data.

use async_trait::async_trait;
use memvid_core::{Memvid, SearchRequest};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{error, info};

use crate::error::ServiceError;
use crate::memvid::searcher::{SearchResponse, SearchResult, Searcher, StateResponse};

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
        };

        // Perform the search (blocking operation)
        let search_response = tokio::task::spawn_blocking({
            let memvid = Arc::clone(&self.memvid);
            move || {
                let mut memvid = tokio::runtime::Handle::current()
                    .block_on(memvid.write());

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
                let memvid = tokio::runtime::Handle::current()
                    .block_on(memvid.read());

                // Get all memory cards for this entity
                memvid.get_entity_memories(&entity)
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
}
