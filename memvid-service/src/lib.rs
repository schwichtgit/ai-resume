//! Memvid gRPC service library.
//!
//! This library exposes the core modules for integration testing while
//! keeping the actual binary entry point in main.rs.

pub mod config;
pub mod error;
pub mod grpc;
pub mod memvid;
pub mod metrics;

// Include generated proto code from build script
pub mod generated {
    pub mod memvid {
        pub mod v1 {
            include!(concat!(env!("OUT_DIR"), "/memvid.v1.rs"));
        }
    }
}
