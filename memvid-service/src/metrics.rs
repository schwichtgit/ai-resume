//! Prometheus metrics for the memvid service.
//!
//! Exposes an HTTP endpoint for Prometheus scraping.

use axum::{routing::get, Router};
use metrics::{counter, describe_counter, describe_histogram, histogram};
use metrics_exporter_prometheus::{PrometheusBuilder, PrometheusHandle};
use tracing::info;

/// Initialize the metrics system and return the Prometheus handle.
pub fn init_metrics() -> PrometheusHandle {
    // Register metric descriptions
    describe_histogram!(
        "memvid_search_latency_ms",
        "Time taken for memvid search operations in milliseconds"
    );
    describe_counter!(
        "memvid_search_total",
        "Total number of search requests processed"
    );
    describe_counter!(
        "memvid_search_errors_total",
        "Total number of search errors"
    );

    // Build Prometheus exporter
    PrometheusBuilder::new()
        .install_recorder()
        .expect("Failed to install Prometheus recorder")
}

/// Record a search latency measurement.
pub fn record_search_latency(latency_ms: f64) {
    histogram!("memvid_search_latency_ms").record(latency_ms);
}

/// Increment the search count.
pub fn increment_search_count() {
    counter!("memvid_search_total").increment(1);
}

/// Increment the search error count.
#[allow(dead_code)]
pub fn increment_search_errors() {
    counter!("memvid_search_errors_total").increment(1);
}

/// Create an Axum router for the metrics HTTP endpoint.
pub fn metrics_router(handle: PrometheusHandle) -> Router {
    Router::new().route("/metrics", get(move || std::future::ready(handle.render())))
}

/// Start the metrics HTTP server on the given port with auto-detect binding.
pub async fn start_metrics_server(port: u16, handle: PrometheusHandle) {
    let app = metrics_router(handle);

    // Auto-detect: Try dual-stack first, fall back to IPv4-only
    let bind_host = match format!("[::]:{}", port).parse::<std::net::SocketAddr>() {
        Ok(addr) => {
            match tokio::net::TcpListener::bind(addr).await {
                Ok(listener) => {
                    info!(port = port, bind = "::", "Starting metrics server (dual-stack)");
                    axum::serve(listener, app)
                        .await
                        .expect("Metrics server failed");
                    return;
                }
                Err(_) => "0.0.0.0"
            }
        }
        Err(_) => "0.0.0.0"
    };

    let addr = format!("{}:{}", bind_host, port);
    info!(port = port, bind = %bind_host, "Starting metrics server (IPv4-only fallback)");

    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("Failed to bind metrics server");

    axum::serve(listener, app)
        .await
        .expect("Metrics server failed");
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use tower::ServiceExt;

    #[test]
    fn test_record_search_latency() {
        // This should not panic even without metrics initialized
        // (metrics crate uses NoOp recorder by default)
        record_search_latency(5.0);
        record_search_latency(10.5);
        record_search_latency(0.1);
    }

    #[test]
    fn test_increment_search_count() {
        // This should not panic
        increment_search_count();
        increment_search_count();
    }

    #[test]
    fn test_increment_search_errors() {
        // This should not panic
        increment_search_errors();
    }

    #[tokio::test]
    async fn test_metrics_router_returns_metrics() {
        // Create a test handle
        let handle = PrometheusBuilder::new()
            .build_recorder()
            .handle();

        let app = metrics_router(handle);

        let request = Request::builder()
            .uri("/metrics")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_metrics_endpoint_content_type() {
        let handle = PrometheusBuilder::new()
            .build_recorder()
            .handle();

        let app = metrics_router(handle);

        let request = Request::builder()
            .uri("/metrics")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        // Prometheus metrics should be plain text
        let content_type = response.headers().get("content-type");
        assert!(content_type.is_some());
    }

    #[tokio::test]
    async fn test_start_metrics_server_binds_and_serves() {
        use http_body_util::Empty;
        use hyper::body::Bytes;
        use std::net::TcpListener as StdTcpListener;

        // Find an available port
        let listener = StdTcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener); // Release the port so the server can bind to it

        let handle = PrometheusBuilder::new().build_recorder().handle();

        // Start server in background task
        let server_handle = tokio::spawn(async move {
            start_metrics_server(port, handle).await;
        });

        // Give the server time to start
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        // Make HTTP request to the server
        let client: hyper_util::client::legacy::Client<_, Empty<Bytes>> =
            hyper_util::client::legacy::Client::builder(hyper_util::rt::TokioExecutor::new())
                .build_http();

        let uri: hyper::Uri = format!("http://127.0.0.1:{}/metrics", port)
            .parse()
            .unwrap();
        let response = client.get(uri).await.unwrap();

        assert_eq!(response.status(), StatusCode::OK);

        // Abort the server task (it runs forever otherwise)
        server_handle.abort();
    }

    #[tokio::test]
    async fn test_metrics_server_returns_prometheus_format() {
        use http_body_util::{BodyExt, Empty};
        use hyper::body::Bytes;
        use std::net::TcpListener as StdTcpListener;

        // Find an available port
        let listener = StdTcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);

        let handle = PrometheusBuilder::new().build_recorder().handle();

        let server_handle = tokio::spawn(async move {
            start_metrics_server(port, handle).await;
        });

        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        let client: hyper_util::client::legacy::Client<_, Empty<Bytes>> =
            hyper_util::client::legacy::Client::builder(hyper_util::rt::TokioExecutor::new())
                .build_http();

        let uri: hyper::Uri = format!("http://127.0.0.1:{}/metrics", port)
            .parse()
            .unwrap();
        let response = client.get(uri).await.unwrap();

        // Read the body
        let body_bytes = response.into_body().collect().await.unwrap().to_bytes();
        let body_str = String::from_utf8_lossy(&body_bytes);

        // Prometheus format check - should be empty or contain valid prometheus text
        // (empty is valid when no metrics have been recorded)
        assert!(body_str.is_empty() || !body_str.contains("<html>"));

        server_handle.abort();
    }
}
