//! Configuration module for the memvid service.
//!
//! All configuration is loaded from environment variables with sensible defaults.

use std::env;

/// Service configuration loaded from environment variables.
#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct Config {
    /// Path to the .mv2 memvid file
    pub memvid_file_path: String,
    /// gRPC server port
    pub grpc_port: u16,
    /// Prometheus metrics HTTP port
    pub metrics_port: u16,
    /// Bind address (supports IPv4, IPv6, or dual-stack)
    pub bind_address: String,
    /// Use mock searcher instead of real memvid (opt-in via MOCK_MEMVID)
    pub mock_memvid: bool,
    /// Log level (trace, debug, info, warn, error)
    pub log_level: String,
}

impl Config {
    /// Load configuration from environment variables.
    ///
    /// # Environment Variables
    /// - `MEMVID_FILE_PATH` - Path to .mv2 file (required unless MOCK_MEMVID=true)
    /// - `GRPC_PORT` - gRPC listen port (default: 50051)
    /// - `METRICS_PORT` - Prometheus metrics port (default: 9090)
    /// - `BIND_ADDRESS` - Bind address (default: auto-detect [::]  or 0.0.0.0)
    /// - `MOCK_MEMVID` - Use mock searcher for testing (default: false)
    /// - `RUST_LOG` - Log level (default: info)
    pub fn from_env() -> Result<Self, ConfigError> {
        let mock_memvid = env::var("MOCK_MEMVID")
            .map(|v| v.to_lowercase() == "true" || v == "1")
            .unwrap_or(false);

        let memvid_file_path = env::var("MEMVID_FILE_PATH").unwrap_or_else(|_| {
            if mock_memvid {
                String::new()
            } else {
                // Default path for development
                "data/.memvid/resume.mv2".to_string()
            }
        });

        // Validate memvid file path is set when not in mock mode
        if !mock_memvid && memvid_file_path.is_empty() {
            return Err(ConfigError::MissingRequired("MEMVID_FILE_PATH"));
        }

        let grpc_port = env::var("GRPC_PORT")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(50051);

        let metrics_port = env::var("METRICS_PORT")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(9090);

        let log_level = env::var("RUST_LOG").unwrap_or_else(|_| "info".to_string());

        // Bind address with auto-detect fallback
        // Try dual-stack (::) first, fall back to IPv4-only (0.0.0.0) if needed
        let bind_address = env::var("BIND_ADDRESS").unwrap_or_else(|_| "auto".to_string());

        Ok(Config {
            memvid_file_path,
            grpc_port,
            metrics_port,
            bind_address,
            mock_memvid,
            log_level,
        })
    }
}

/// Configuration errors.
#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("Missing required environment variable: {0}")]
    MissingRequired(&'static str),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_defaults_with_mock_memvid() {
        // Set mock mode to bypass memvid file requirement
        env::set_var("MOCK_MEMVID", "true");
        env::remove_var("MEMVID_FILE_PATH");
        env::remove_var("GRPC_PORT");
        env::remove_var("METRICS_PORT");

        let config = Config::from_env().unwrap();
        assert!(config.mock_memvid);
        assert_eq!(config.grpc_port, 50051);
        assert_eq!(config.metrics_port, 9090);

        env::remove_var("MOCK_MEMVID");
    }
}
