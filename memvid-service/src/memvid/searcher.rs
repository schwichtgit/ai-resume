//! Searcher trait defining the interface for memvid search operations.

use async_trait::async_trait;

use crate::error::ServiceError;

/// A single search result from memvid.
#[derive(Debug, Clone)]
pub struct SearchResult {
    /// Title or heading of the matched section
    pub title: String,
    /// Relevance score (0.0 to 1.0)
    pub score: f32,
    /// Text snippet from the matched content
    pub snippet: String,
    /// Tags/metadata (e.g., "skills", "experience", "education")
    pub tags: Vec<String>,
}

/// Search response containing results and metadata.
#[derive(Debug, Clone)]
pub struct SearchResponse {
    /// The search results ordered by relevance
    pub hits: Vec<SearchResult>,
    /// Total number of hits found
    pub total_hits: i32,
    /// Time taken for the search in milliseconds
    pub took_ms: i32,
}

/// State response for memory card entity lookup.
#[derive(Debug, Clone)]
pub struct StateResponse {
    /// Whether the entity was found
    pub found: bool,
    /// The entity name
    pub entity: String,
    /// Map of slot names to values
    pub slots: std::collections::HashMap<String, String>,
}

/// Trait defining the interface for memvid search operations.
///
/// Implementations include:
/// - `MockSearcher` - Returns hardcoded results for testing
/// - `MemvidSearcher` - Real memvid-core integration
#[async_trait]
pub trait Searcher: Send + Sync {
    /// Perform a semantic search over the loaded index.
    ///
    /// # Arguments
    /// * `query` - Natural language search query
    /// * `top_k` - Maximum number of results to return
    /// * `snippet_chars` - Maximum characters per snippet
    ///
    /// # Returns
    /// Search results ordered by relevance score (descending)
    async fn search(
        &self,
        query: &str,
        top_k: i32,
        snippet_chars: i32,
    ) -> Result<SearchResponse, ServiceError>;

    /// Get memory card state for an entity (O(1) lookup).
    ///
    /// This provides direct access to memory card slots without search truncation.
    /// Typically used for retrieving profile metadata stored via add_memory_cards().
    ///
    /// # Arguments
    /// * `entity` - Entity name (e.g., "__profile__")
    /// * `slot` - Optional specific slot to retrieve (empty returns all slots)
    ///
    /// # Returns
    /// State response with entity slots if found
    async fn get_state(
        &self,
        entity: &str,
        slot: Option<&str>,
    ) -> Result<StateResponse, ServiceError>;

    /// Get the number of frames/chunks in the loaded index.
    fn frame_count(&self) -> i32;

    /// Get the path to the loaded memvid file.
    fn memvid_file(&self) -> &str;

    /// Check if the searcher is ready to handle requests.
    fn is_ready(&self) -> bool;
}
