//! gRPC service implementations for the memvid service.

mod service;

pub use service::{HealthService, MemvidGrpcService};
