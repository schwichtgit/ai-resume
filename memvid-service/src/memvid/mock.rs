//! Mock searcher implementation for testing without memvid-core.

use async_trait::async_trait;
use std::time::Instant;
use tracing::info;

use super::searcher::{SearchResponse, SearchResult, Searcher, StateResponse};
use crate::error::ServiceError;

/// Mock searcher that returns hardcoded results for testing.
///
/// This implementation simulates memvid search behavior without requiring
/// the actual memvid-core library or a .mv2 file.
pub struct MockSearcher {
    frame_count: i32,
    memvid_file: String,
}

impl MockSearcher {
    /// Create a new mock searcher.
    pub fn new() -> Self {
        info!("Initializing MockSearcher with sample resume data");
        Self {
            frame_count: 42, // Simulated frame count
            memvid_file: "mock://sample-resume.mv2".to_string(),
        }
    }

    /// Generate mock search results based on query keywords.
    fn generate_results(&self, query: &str, top_k: i32, snippet_chars: i32) -> Vec<SearchResult> {
        let query_lower = query.to_lowercase();
        let mut results = Vec::new();

        // Sample resume data - would come from .mv2 in real implementation
        let sample_data = vec![
            (
                "Senior Engineering Manager at Siemens",
                0.95,
                "Led cross-functional team of 12 engineers building industrial IoT platform. \
                 Implemented CI/CD pipelines reducing deployment time by 60%. \
                 Drove adoption of Rust for performance-critical edge services.",
                vec!["experience", "leadership", "siemens"],
            ),
            (
                "Technical Skills - Programming Languages",
                0.88,
                "Proficient in Rust, Python, TypeScript, Go. \
                 Experience with systems programming, web services, and ML pipelines. \
                 Strong background in performance optimization and memory-safe code.",
                vec!["skills", "programming", "languages"],
            ),
            (
                "GenAI and Machine Learning Experience",
                0.92,
                "Built RAG systems using vector databases and LLM APIs. \
                 Implemented semantic search with memvid for resume applications. \
                 Experience with OpenAI, Anthropic Claude, and open-source models.",
                vec!["skills", "ai", "ml", "genai"],
            ),
            (
                "Security Engineering Background",
                0.85,
                "Implemented zero-trust architecture for industrial control systems. \
                 Led security audits and penetration testing initiatives. \
                 Designed secure communication protocols for edge devices.",
                vec!["experience", "security", "architecture"],
            ),
            (
                "VP Engineering Qualifications",
                0.90,
                "10+ years of engineering leadership experience. \
                 Built and scaled teams from 5 to 50+ engineers. \
                 Track record of delivering complex technical projects on time.",
                vec!["leadership", "management", "executive"],
            ),
            (
                "Education - Computer Science",
                0.75,
                "M.S. Computer Science with focus on distributed systems. \
                 Research in fault-tolerant computing and consensus algorithms. \
                 Published papers on edge computing architectures.",
                vec!["education", "academic"],
            ),
        ];

        // Score and filter results based on query relevance
        for (title, base_score, snippet, tags) in sample_data {
            let mut score: f32 = base_score;

            // Boost score if query matches tags or content
            for tag in &tags {
                if query_lower.contains(tag) {
                    score += 0.05;
                }
            }
            if snippet.to_lowercase().contains(&query_lower) {
                score += 0.03;
            }
            if title.to_lowercase().contains(&query_lower) {
                score += 0.02;
            }

            // Clamp score to 1.0
            score = score.min(1.0);

            // Truncate snippet to requested length
            let truncated_snippet = if snippet.len() > snippet_chars as usize {
                format!("{}...", &snippet[..snippet_chars as usize - 3])
            } else {
                snippet.to_string()
            };

            results.push(SearchResult {
                title: title.to_string(),
                score,
                snippet: truncated_snippet,
                tags: tags.into_iter().map(String::from).collect(),
            });
        }

        // Sort by score descending
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());

        // Limit to top_k
        results.truncate(top_k as usize);

        results
    }
}

impl Default for MockSearcher {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Searcher for MockSearcher {
    async fn search(
        &self,
        query: &str,
        top_k: i32,
        snippet_chars: i32,
    ) -> Result<SearchResponse, ServiceError> {
        let start = Instant::now();

        // Validate inputs
        if query.trim().is_empty() {
            return Err(ServiceError::InvalidRequest("Query cannot be empty".into()));
        }

        let top_k = top_k.clamp(1, 20);
        let snippet_chars = snippet_chars.clamp(50, 1000);

        // Simulate some processing time (real memvid would be ~1-5ms)
        tokio::time::sleep(tokio::time::Duration::from_millis(2)).await;

        let hits = self.generate_results(query, top_k, snippet_chars);
        let total_hits = hits.len() as i32;
        let took_ms = start.elapsed().as_millis() as i32;

        info!(
            query = %query,
            hits = total_hits,
            took_ms = took_ms,
            "Mock search completed"
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
        info!(entity = %entity, slot = ?slot, "Mock get_state called");

        // Only support __profile__ entity in mock
        if entity != "__profile__" {
            return Ok(StateResponse {
                found: false,
                entity: entity.to_string(),
                slots: std::collections::HashMap::new(),
            });
        }

        // Mock profile data as JSON
        let profile_json = r#"{
  "name": "Frank Schwichtenberg",
  "title": "Senior Engineering Manager",
  "email": "frank@example.com",
  "linkedin": "https://linkedin.com/in/franksch",
  "location": "San Francisco, CA",
  "status": "Open to opportunities",
  "suggested_questions": [
    "Tell me about your engineering leadership experience",
    "What's your approach to building high-performing teams?"
  ],
  "tags": ["engineering", "leadership", "platform"],
  "system_prompt": "You are an AI representing Frank's resume...",
  "experience": [
    {"company": "Siemens", "role": "Engineering Manager", "period": "2020-2024"}
  ],
  "skills": {
    "strong": ["Python", "Rust"],
    "moderate": ["Go"],
    "gaps": []
  },
  "fit_assessment_examples": []
}"#;

        let mut slots = std::collections::HashMap::new();

        // If specific slot requested, only return that slot
        if let Some(slot_name) = slot {
            if slot_name == "data" {
                slots.insert("data".to_string(), profile_json.to_string());
            }
        } else {
            // Return all slots (just "data" in this case)
            slots.insert("data".to_string(), profile_json.to_string());
        }

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
        &self.memvid_file
    }

    fn is_ready(&self) -> bool {
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_mock_search() {
        let searcher = MockSearcher::new();
        let response = searcher.search("Python experience", 5, 200).await.unwrap();

        assert!(!response.hits.is_empty());
        assert!(response.took_ms >= 0);
        assert!(response.hits[0].score > 0.0);
    }

    #[tokio::test]
    async fn test_empty_query_error() {
        let searcher = MockSearcher::new();
        let result = searcher.search("", 5, 200).await;

        assert!(result.is_err());
    }

    #[test]
    fn test_frame_count() {
        let searcher = MockSearcher::new();
        assert_eq!(searcher.frame_count(), 42);
    }

    #[tokio::test]
    async fn test_get_state_profile_found() {
        let searcher = MockSearcher::new();
        let response = searcher.get_state("__profile__", None).await.unwrap();

        assert!(response.found);
        assert_eq!(response.entity, "__profile__");
        assert!(response.slots.contains_key("data"));

        // Verify the JSON can be parsed
        let profile_json = response.slots.get("data").unwrap();
        assert!(profile_json.contains("Frank Schwichtenberg"));
        assert!(profile_json.contains("Senior Engineering Manager"));
    }

    #[tokio::test]
    async fn test_get_state_with_specific_slot() {
        let searcher = MockSearcher::new();
        let response = searcher.get_state("__profile__", Some("data")).await.unwrap();

        assert!(response.found);
        assert_eq!(response.slots.len(), 1);
        assert!(response.slots.contains_key("data"));
    }

    #[tokio::test]
    async fn test_get_state_entity_not_found() {
        let searcher = MockSearcher::new();
        let response = searcher.get_state("nonexistent", None).await.unwrap();

        assert!(!response.found);
        assert_eq!(response.entity, "nonexistent");
        assert!(response.slots.is_empty());
    }

    #[tokio::test]
    async fn test_get_state_invalid_slot() {
        let searcher = MockSearcher::new();
        let response = searcher.get_state("__profile__", Some("invalid_slot")).await.unwrap();

        assert!(response.found);
        assert!(response.slots.is_empty()); // Requested slot doesn't exist
    }
}
