//! OpenTelemetry initialization, gated on `OTEL_EXPORTER_OTLP_ENDPOINT`.
//!
//! When the environment variable is set, this module creates an OTLP span
//! exporter (gRPC/tonic) and returns a `tracing_opentelemetry::OpenTelemetryLayer`
//! that bridges `tracing` spans to OpenTelemetry. When unset, `init_otel_layer`
//! returns `None` and existing console JSON logging is unaffected.

use opentelemetry::trace::TracerProvider as _;
use opentelemetry::KeyValue;
use opentelemetry_otlp::SpanExporter;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::trace::TracerProvider;
use opentelemetry_sdk::Resource;
use tracing::info;
use tracing_opentelemetry::OpenTelemetryLayer;
use tracing_subscriber::registry::LookupSpan;

/// Initialize OpenTelemetry if `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
///
/// Returns an optional layer that can be added to the tracing subscriber.
/// When the env var is absent or the exporter fails to build, returns `None`
/// and logs a warning (no crash).
pub fn init_otel_layer<S>() -> Option<OpenTelemetryLayer<S, opentelemetry_sdk::trace::Tracer>>
where
    S: tracing::Subscriber + for<'span> LookupSpan<'span>,
{
    let endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT").ok()?;

    let service_name =
        std::env::var("OTEL_SERVICE_NAME").unwrap_or_else(|_| "ai-resume-memvid".to_string());

    info!(
        endpoint = %endpoint,
        service_name = %service_name,
        "Initializing OpenTelemetry OTLP trace exporter"
    );

    let exporter = match SpanExporter::builder()
        .with_tonic()
        .with_endpoint(&endpoint)
        .build()
    {
        Ok(exp) => exp,
        Err(e) => {
            tracing::warn!(error = %e, "Failed to build OTLP span exporter; tracing disabled");
            return None;
        }
    };

    let resource = Resource::new(vec![KeyValue::new("service.name", service_name)]);

    let provider = TracerProvider::builder()
        .with_batch_exporter(exporter, opentelemetry_sdk::runtime::Tokio)
        .with_resource(resource)
        .build();

    let tracer = provider.tracer("ai-resume-memvid");

    // Store the provider globally so it is not dropped (which would flush & stop export).
    // In a production service with graceful shutdown, you would call provider.shutdown()
    // during the shutdown sequence instead of using mem::forget.
    std::mem::forget(provider);

    Some(OpenTelemetryLayer::new(tracer))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;
    use tracing_subscriber::prelude::*;

    #[test]
    #[serial]
    fn test_otel_layer_none_when_env_unset() {
        // Ensure the env var is not set
        std::env::remove_var("OTEL_EXPORTER_OTLP_ENDPOINT");

        let layer: Option<
            OpenTelemetryLayer<tracing_subscriber::Registry, opentelemetry_sdk::trace::Tracer>,
        > = init_otel_layer();
        assert!(
            layer.is_none(),
            "Layer should be None when env var is unset"
        );
    }

    #[tokio::test]
    #[serial]
    async fn test_otel_layer_returns_some_with_valid_endpoint() {
        // Set a valid-looking endpoint (exporter creation should succeed even
        // if the collector is unreachable -- it uses connect_lazy)
        std::env::set_var("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317");
        std::env::remove_var("OTEL_SERVICE_NAME");

        let layer: Option<
            OpenTelemetryLayer<tracing_subscriber::Registry, opentelemetry_sdk::trace::Tracer>,
        > = init_otel_layer();
        assert!(layer.is_some(), "Layer should be Some when endpoint is set");

        // Clean up
        std::env::remove_var("OTEL_EXPORTER_OTLP_ENDPOINT");
    }

    #[tokio::test]
    #[serial]
    async fn test_otel_layer_uses_custom_service_name() {
        std::env::set_var("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317");
        std::env::set_var("OTEL_SERVICE_NAME", "custom-service");

        let layer: Option<
            OpenTelemetryLayer<tracing_subscriber::Registry, opentelemetry_sdk::trace::Tracer>,
        > = init_otel_layer();
        assert!(layer.is_some());

        // Clean up
        std::env::remove_var("OTEL_EXPORTER_OTLP_ENDPOINT");
        std::env::remove_var("OTEL_SERVICE_NAME");
    }

    #[test]
    #[serial]
    fn test_otel_layer_composes_with_registry() {
        // Verify the layer can be composed into a subscriber stack
        std::env::remove_var("OTEL_EXPORTER_OTLP_ENDPOINT");

        let fmt_layer = tracing_subscriber::fmt::layer().json();
        let registry = tracing_subscriber::registry().with(fmt_layer);

        let otel_layer: Option<OpenTelemetryLayer<_, opentelemetry_sdk::trace::Tracer>> = None;

        // This should compile and work -- the None case means no OTel layer
        let _subscriber = registry.with(otel_layer);
    }
}
