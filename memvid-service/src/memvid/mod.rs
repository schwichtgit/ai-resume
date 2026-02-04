//! Memvid search module providing semantic search over .mv2 files.
//!
//! This module provides a `Searcher` trait and implementations:
//! - `MockSearcher` - Returns hardcoded results for testing
//! - `RealSearcher` - Real memvid-core integration

mod mock;
mod real;
mod searcher;

pub use mock::MockSearcher;
pub use real::RealSearcher;
pub use searcher::{AskMode, AskRequest, Searcher};
