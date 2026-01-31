//! Error types for the memvid service.

use tonic::Status;

/// Service-level errors that can occur during operation.
#[derive(Debug, thiserror::Error)]
pub enum ServiceError {
    #[error("Memvid file not found: {0}")]
    MemvidFileNotFound(String),

    #[error("Failed to load memvid index: {0}")]
    MemvidLoadError(String),

    #[error("Search failed: {0}")]
    SearchError(String),

    #[error("Invalid request: {0}")]
    InvalidRequest(String),

    #[error("Service not ready")]
    NotReady,

    #[error("Internal error: {0}")]
    Internal(String),
}

impl From<ServiceError> for Status {
    fn from(err: ServiceError) -> Self {
        match err {
            ServiceError::MemvidFileNotFound(msg) => Status::not_found(msg),
            ServiceError::MemvidLoadError(msg) => Status::internal(msg),
            ServiceError::SearchError(msg) => Status::internal(msg),
            ServiceError::InvalidRequest(msg) => Status::invalid_argument(msg),
            ServiceError::NotReady => Status::unavailable("Service not ready"),
            ServiceError::Internal(msg) => Status::internal(msg),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tonic::Code;

    #[test]
    fn test_memvid_file_not_found_converts_to_not_found() {
        let err = ServiceError::MemvidFileNotFound("test.mv2".into());
        let status: Status = err.into();
        assert_eq!(status.code(), Code::NotFound);
        assert!(status.message().contains("test.mv2"));
    }

    #[test]
    fn test_memvid_load_error_converts_to_internal() {
        let err = ServiceError::MemvidLoadError("corrupt file".into());
        let status: Status = err.into();
        assert_eq!(status.code(), Code::Internal);
        assert!(status.message().contains("corrupt file"));
    }

    #[test]
    fn test_search_error_converts_to_internal() {
        let err = ServiceError::SearchError("index error".into());
        let status: Status = err.into();
        assert_eq!(status.code(), Code::Internal);
        assert!(status.message().contains("index error"));
    }

    #[test]
    fn test_invalid_request_converts_to_invalid_argument() {
        let err = ServiceError::InvalidRequest("empty query".into());
        let status: Status = err.into();
        assert_eq!(status.code(), Code::InvalidArgument);
        assert!(status.message().contains("empty query"));
    }

    #[test]
    fn test_not_ready_converts_to_unavailable() {
        let err = ServiceError::NotReady;
        let status: Status = err.into();
        assert_eq!(status.code(), Code::Unavailable);
        assert!(status.message().contains("not ready"));
    }

    #[test]
    fn test_error_display() {
        let err = ServiceError::MemvidFileNotFound("missing.mv2".into());
        assert_eq!(format!("{}", err), "Memvid file not found: missing.mv2");

        let err = ServiceError::NotReady;
        assert_eq!(format!("{}", err), "Service not ready");
    }
}
