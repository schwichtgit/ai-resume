//! Memvid gRPC service for AI Resume.
//!
//! This service provides semantic search over resume content stored in .mv2 files.
//! It exposes a gRPC API for the Python FastAPI orchestration layer.
//!
//! # Environment Variables
//! - `MEMVID_FILE_PATH` - Path to .mv2 file (required unless MOCK_MEMVID=true)
//! - `GRPC_PORT` - gRPC listen port (default: 50051)
//! - `METRICS_PORT` - Prometheus metrics port (default: 9090)
//! - `MOCK_MEMVID` - Use mock searcher for testing (default: false)
//! - `RUST_LOG` - Log level (default: info)

use std::sync::Arc;
use tonic::transport::Server;
use tracing::{error, info, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

mod config;
mod error;
mod grpc;
mod memvid;
mod metrics;

// Include generated proto code from build script
mod generated {
    pub mod memvid {
        pub mod v1 {
            include!(concat!(env!("OUT_DIR"), "/memvid.v1.rs"));
        }
    }
}

use config::Config;
use generated::memvid::v1::{
    health_server::HealthServer, memvid_service_server::MemvidServiceServer,
};
use grpc::{HealthService, MemvidGrpcService};
use memvid::{MockSearcher, RealSearcher, Searcher};

/// Run healthcheck: TCP connect to gRPC port to verify service is listening.
/// Tries both IPv4 and IPv6 for dual-stack support.
async fn run_healthcheck() -> Result<(), Box<dyn std::error::Error>> {
    let port: u16 = std::env::var("GRPC_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(50051);

    let addrs = [
        std::net::SocketAddr::from(([127, 0, 0, 1], port)),
        std::net::SocketAddr::from(([0, 0, 0, 0, 0, 0, 0, 1], port)),
    ];

    for addr in &addrs {
        match tokio::time::timeout(
            std::time::Duration::from_secs(2),
            tokio::net::TcpStream::connect(addr),
        )
        .await
        {
            Ok(Ok(_)) => {
                eprintln!("healthcheck: service is listening on {}", addr);
                std::process::exit(0);
            }
            _ => continue,
        }
    }

    eprintln!("healthcheck: failed to connect on port {}", port);
    std::process::exit(1);
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing (use RUST_LOG env var to control log level)
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .with(tracing_subscriber::fmt::layer().json())
        .init();

    // Check if running in healthcheck mode
    if std::env::args().any(|arg| arg == "--health") {
        return run_healthcheck().await;
    }

    info!("Starting memvid gRPC service");

    // Load configuration
    let config = Config::from_env().map_err(|e| {
        error!("Configuration error: {}", e);
        e
    })?;

    info!(
        grpc_port = config.grpc_port,
        metrics_port = config.metrics_port,
        mock_memvid = config.mock_memvid,
        "Configuration loaded"
    );

    // Initialize metrics
    let metrics_handle = metrics::init_metrics();

    // Create searcher (mock or real based on config)
    // STRICT POLICY: No silent fallbacks - fail loudly if real implementation unavailable
    let searcher: Arc<dyn memvid::Searcher> = if config.mock_memvid {
        info!("MOCK_MEMVID=true: Using mock searcher for testing");
        Arc::new(MockSearcher::new())
    } else {
        info!(
            memvid_file = %config.memvid_file_path,
            "MOCK_MEMVID=false: Loading real memvid searcher (will exit on failure)"
        );
        match RealSearcher::new(&config.memvid_file_path).await {
            Ok(searcher) => {
                let fc = searcher.frame_count();
                if fc == 0 {
                    warn!(
                        memvid_file = %config.memvid_file_path,
                        "Memvid file loaded but contains 0 frames -- search results will be empty"
                    );
                }
                info!(frame_count = fc, "Real memvid searcher loaded successfully");
                Arc::new(searcher)
            }
            Err(e) => {
                error!(
                    error = %e,
                    memvid_file = %config.memvid_file_path,
                    "FATAL: Failed to load memvid file with MOCK_MEMVID=false. Set MOCK_MEMVID=true for testing."
                );
                return Err(e.into());
            }
        }
    };

    // Create gRPC services
    let memvid_service = MemvidGrpcService::new(Arc::clone(&searcher));
    let health_service = HealthService::new(Arc::clone(&searcher));

    // Start metrics server in background
    let metrics_port = config.metrics_port;
    tokio::spawn(async move {
        metrics::start_metrics_server(metrics_port, metrics_handle).await;
    });

    // Start gRPC server with configurable bind address
    // Supports: auto-detect, explicit IPv4 (0.0.0.0), IPv6 (::), or dual-stack ([::])
    let grpc_addr = if config.bind_address == "auto" {
        // Auto-detect: Try dual-stack first, fall back to IPv4-only
        match format!("[::]:{}", config.grpc_port).parse::<std::net::SocketAddr>() {
            Ok(addr) => {
                // Test if we can actually bind to IPv6
                match tokio::net::TcpListener::bind(addr).await {
                    Ok(_) => {
                        info!("Auto-detected dual-stack support, using [::]");
                        addr
                    }
                    Err(_) => {
                        info!("IPv6 not available, falling back to IPv4 (0.0.0.0)");
                        format!("0.0.0.0:{}", config.grpc_port).parse()?
                    }
                }
            }
            Err(_) => {
                info!("IPv6 parsing failed, using IPv4 (0.0.0.0)");
                format!("0.0.0.0:{}", config.grpc_port).parse()?
            }
        }
    } else {
        // Explicit bind address provided
        // Add brackets if it's an IPv6 address without them
        let bind_str = if config.bind_address.contains(':') && !config.bind_address.starts_with('[')
        {
            format!("[{}]:{}", config.bind_address, config.grpc_port)
        } else {
            format!("{}:{}", config.bind_address, config.grpc_port)
        };
        bind_str.parse()?
    };

    info!(addr = %grpc_addr, "Starting gRPC server");

    Server::builder()
        .add_service(MemvidServiceServer::new(memvid_service))
        .add_service(HealthServer::new(health_service))
        .serve(grpc_addr)
        .await?;

    Ok(())
}
