//! gRPC service implementations for MemvidService and Health.

use std::sync::Arc;
use tonic::{Request, Response, Status};
use tracing::{info, instrument};

use crate::generated::memvid::v1::{
    health_check_response::Status as HealthStatus,
    health_server::Health,
    memvid_service_server::MemvidService,
    AskMode as ProtoAskMode, AskRequest, AskResponse, AskStats, GetStateRequest,
    GetStateResponse, HealthCheckRequest, HealthCheckResponse, SearchHit, SearchRequest,
    SearchResponse,
};
use crate::memvid::{AskMode as SearcherAskMode, AskRequest as SearcherAskRequest, Searcher};
use crate::metrics;

/// gRPC implementation of the MemvidService.
pub struct MemvidGrpcService {
    searcher: Arc<dyn Searcher>,
}

impl MemvidGrpcService {
    /// Create a new MemvidGrpcService with the given searcher implementation.
    pub fn new(searcher: Arc<dyn Searcher>) -> Self {
        Self { searcher }
    }
}

#[tonic::async_trait]
impl MemvidService for MemvidGrpcService {
    #[instrument(skip(self, request), fields(query))]
    async fn search(
        &self,
        request: Request<SearchRequest>,
    ) -> Result<Response<SearchResponse>, Status> {
        let req = request.into_inner();

        // Record the query in span
        tracing::Span::current().record("query", &req.query);

        info!(
            query = %req.query,
            top_k = req.top_k,
            "Processing search request"
        );

        // Apply defaults
        let top_k = if req.top_k == 0 { 5 } else { req.top_k };
        let snippet_chars = if req.snippet_chars == 0 {
            200
        } else {
            req.snippet_chars
        };

        // Perform search
        let result = self
            .searcher
            .search(&req.query, top_k, snippet_chars)
            .await
            .map_err(|e| Status::from(e))?;

        // Record metrics
        metrics::record_search_latency(result.took_ms as f64);
        metrics::increment_search_count();

        // Convert to gRPC response
        let hits: Vec<SearchHit> = result
            .hits
            .into_iter()
            .map(|h| SearchHit {
                title: h.title,
                score: h.score,
                snippet: h.snippet,
                tags: h.tags,
            })
            .collect();

        let response = SearchResponse {
            hits,
            total_hits: result.total_hits,
            took_ms: result.took_ms,
        };

        Ok(Response::new(response))
    }

    #[instrument(skip(self, request), fields(question))]
    async fn ask(
        &self,
        request: Request<AskRequest>,
    ) -> Result<Response<AskResponse>, Status> {
        let req = request.into_inner();

        // Record the question in span
        tracing::Span::current().record("question", &req.question);

        info!(
            question = %req.question,
            mode = ?req.mode,
            top_k = req.top_k,
            "Processing ask request"
        );

        // Apply defaults
        let top_k = if req.top_k == 0 { 5 } else { req.top_k };
        let snippet_chars = if req.snippet_chars == 0 {
            200
        } else {
            req.snippet_chars
        };

        // Map proto AskMode to searcher AskMode
        let mode = match ProtoAskMode::try_from(req.mode) {
            Ok(ProtoAskMode::Sem) => SearcherAskMode::Sem,
            Ok(ProtoAskMode::Lex) => SearcherAskMode::Lex,
            _ => SearcherAskMode::Hybrid, // Default to Hybrid
        };

        // Build searcher request
        let ask_request = SearcherAskRequest {
            question: req.question.clone(),
            use_llm: req.use_llm,
            top_k,
            filters: req.filters,
            start: req.start,
            end: req.end,
            snippet_chars,
            mode,
            uri: if req.uri.is_empty() {
                None
            } else {
                Some(req.uri)
            },
            cursor: if req.cursor.is_empty() {
                None
            } else {
                Some(req.cursor)
            },
            as_of_frame: req.as_of_frame,
            as_of_ts: req.as_of_ts,
            adaptive: req.adaptive,
        };

        // Perform ask operation
        let result = self
            .searcher
            .ask(ask_request)
            .await
            .map_err(|e| Status::from(e))?;

        // Convert to gRPC response
        let evidence: Vec<SearchHit> = result
            .evidence
            .into_iter()
            .map(|e| SearchHit {
                title: e.title,
                score: e.score,
                snippet: e.snippet,
                tags: e.tags,
            })
            .collect();

        let response = AskResponse {
            answer: result.answer,
            evidence,
            stats: Some(AskStats {
                candidates_retrieved: result.stats.candidates_retrieved,
                results_returned: result.stats.results_returned,
                retrieval_ms: result.stats.retrieval_ms,
                reranking_ms: result.stats.reranking_ms,
                used_fallback: result.stats.used_fallback,
            }),
        };

        Ok(Response::new(response))
    }

    #[instrument(skip(self, request), fields(entity))]
    async fn get_state(
        &self,
        request: Request<GetStateRequest>,
    ) -> Result<Response<GetStateResponse>, Status> {
        let req = request.into_inner();

        // Record the entity in span
        tracing::Span::current().record("entity", &req.entity);

        info!(
            entity = %req.entity,
            slot = %req.slot,
            "Processing get_state request"
        );

        // Convert empty slot string to None
        let slot = if req.slot.is_empty() {
            None
        } else {
            Some(req.slot.as_str())
        };

        // Perform state lookup
        let result = self
            .searcher
            .get_state(&req.entity, slot)
            .await
            .map_err(|e| Status::from(e))?;

        // Convert to gRPC response
        let response = GetStateResponse {
            found: result.found,
            entity: result.entity,
            slots: result.slots,
        };

        Ok(Response::new(response))
    }
}

/// gRPC implementation of the Health service.
pub struct HealthService {
    searcher: Arc<dyn Searcher>,
}

impl HealthService {
    /// Create a new HealthService with the given searcher implementation.
    pub fn new(searcher: Arc<dyn Searcher>) -> Self {
        Self { searcher }
    }
}

#[tonic::async_trait]
impl Health for HealthService {
    async fn check(
        &self,
        _request: Request<HealthCheckRequest>,
    ) -> Result<Response<HealthCheckResponse>, Status> {
        let status = if self.searcher.is_ready() {
            HealthStatus::Serving
        } else {
            HealthStatus::NotServing
        };

        let response = HealthCheckResponse {
            status: status.into(),
            frame_count: self.searcher.frame_count(),
            memvid_file: self.searcher.memvid_file().to_string(),
        };

        Ok(Response::new(response))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::memvid::MockSearcher;
    use std::sync::Once;

    // Global metrics initialization - only happens once across all tests
    static INIT_METRICS: Once = Once::new();

    fn init_test_metrics() {
        INIT_METRICS.call_once(|| {
            let _ = crate::metrics::init_metrics();
        });
    }

    #[tokio::test]
    async fn test_search_with_defaults() {
        init_test_metrics();

        let searcher = Arc::new(MockSearcher::new());
        let service = MemvidGrpcService::new(searcher);

        let request = Request::new(SearchRequest {
            query: "Python experience".to_string(),
            top_k: 0,        // Should default to 5
            snippet_chars: 0, // Should default to 200
        });

        let response = service.search(request).await.unwrap();
        let inner = response.into_inner();

        assert!(!inner.hits.is_empty());
        assert!(inner.hits.len() <= 5);
        assert!(inner.took_ms >= 0);
    }

    #[tokio::test]
    async fn test_search_with_custom_params() {
        init_test_metrics();

        let searcher = Arc::new(MockSearcher::new());
        let service = MemvidGrpcService::new(searcher);

        let request = Request::new(SearchRequest {
            query: "Rust programming".to_string(),
            top_k: 3,
            snippet_chars: 100,
        });

        let response = service.search(request).await.unwrap();
        let inner = response.into_inner();

        assert!(inner.hits.len() <= 3);
        for hit in &inner.hits {
            assert!(hit.score > 0.0);
            assert!(hit.score <= 1.0);
            assert!(!hit.title.is_empty());
        }
    }

    #[tokio::test]
    async fn test_search_returns_tags() {
        init_test_metrics();

        let searcher = Arc::new(MockSearcher::new());
        let service = MemvidGrpcService::new(searcher);

        let request = Request::new(SearchRequest {
            query: "skills".to_string(),
            top_k: 5,
            snippet_chars: 200,
        });

        let response = service.search(request).await.unwrap();
        let inner = response.into_inner();

        // At least one hit should have tags
        let has_tags = inner.hits.iter().any(|h| !h.tags.is_empty());
        assert!(has_tags);
    }

    #[tokio::test]
    async fn test_health_check_serving() {
        let searcher = Arc::new(MockSearcher::new());
        let service = HealthService::new(searcher);

        let request = Request::new(HealthCheckRequest {
            service: String::new(),
        });

        let response = service.check(request).await.unwrap();
        let inner = response.into_inner();

        assert_eq!(inner.status, HealthStatus::Serving as i32);
        assert!(inner.frame_count > 0);
        assert!(!inner.memvid_file.is_empty());
    }

    #[tokio::test]
    async fn test_memvid_grpc_service_new() {
        let searcher = Arc::new(MockSearcher::new());
        let _service = MemvidGrpcService::new(searcher);
        // Service created successfully
    }

    #[tokio::test]
    async fn test_health_service_new() {
        let searcher = Arc::new(MockSearcher::new());
        let _service = HealthService::new(searcher);
        // Service created successfully
    }

    #[tokio::test]
    async fn test_get_state_profile_found() {
        let searcher = Arc::new(MockSearcher::new());
        let service = MemvidGrpcService::new(searcher);

        let request = Request::new(GetStateRequest {
            entity: "__profile__".to_string(),
            slot: String::new(), // Request all slots
        });

        let response = service.get_state(request).await.unwrap();
        let inner = response.into_inner();

        assert!(inner.found);
        assert_eq!(inner.entity, "__profile__");
        assert!(!inner.slots.is_empty());
        assert!(inner.slots.contains_key("data"));

        // Verify profile JSON structure
        let profile_json = inner.slots.get("data").unwrap();
        assert!(profile_json.contains("Frank Schwichtenberg"));
    }

    #[tokio::test]
    async fn test_get_state_with_specific_slot() {
        let searcher = Arc::new(MockSearcher::new());
        let service = MemvidGrpcService::new(searcher);

        let request = Request::new(GetStateRequest {
            entity: "__profile__".to_string(),
            slot: "data".to_string(),
        });

        let response = service.get_state(request).await.unwrap();
        let inner = response.into_inner();

        assert!(inner.found);
        assert!(inner.slots.contains_key("data"));
    }

    #[tokio::test]
    async fn test_get_state_entity_not_found() {
        let searcher = Arc::new(MockSearcher::new());
        let service = MemvidGrpcService::new(searcher);

        let request = Request::new(GetStateRequest {
            entity: "nonexistent_entity".to_string(),
            slot: String::new(),
        });

        let response = service.get_state(request).await.unwrap();
        let inner = response.into_inner();

        assert!(!inner.found);
        assert_eq!(inner.entity, "nonexistent_entity");
        assert!(inner.slots.is_empty());
    }

    #[tokio::test]
    async fn test_get_state_invalid_slot() {
        let searcher = Arc::new(MockSearcher::new());
        let service = MemvidGrpcService::new(searcher);

        let request = Request::new(GetStateRequest {
            entity: "__profile__".to_string(),
            slot: "nonexistent_slot".to_string(),
        });

        let response = service.get_state(request).await.unwrap();
        let inner = response.into_inner();

        assert!(inner.found); // Entity exists
        assert!(inner.slots.is_empty()); // But requested slot doesn't
    }
}
