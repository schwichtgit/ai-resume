//! Standalone reproduction of memvid Bug C (GitHub issue #196).
//!
//! Bug: `ask()` fails with "Time index track is invalid: frame id out of
//! range" when operating on .mv2 files created by memvid-sdk 2.0.157 that
//! contain 12+ frames of varied content.
//!
//! This binary accepts one argument: the path to a .mv2 file created by
//! the companion `repro_bug_c.py` script (or any .mv2 with 12+ frames).
//!
//! Usage:
//!     # First, create the test .mv2 with Python:
//!     #   pip install memvid-sdk==2.0.157
//!     #   python repro_bug_c.py
//!     #   (note the path printed at the end)
//!
//!     cargo run --release -- <path-to-test.mv2>
//!
//! Versions:
//!     memvid-core 2.0.137 (crates.io)
//!     Rust stable (1.84+)

use memvid_core::Memvid;
use std::env;
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: repro-bug-c <path-to-.mv2>");
        eprintln!();
        eprintln!("Create a test .mv2 first with repro_bug_c.py, then pass its path here.");
        process::exit(1);
    }

    let path = &args[1];

    println!("================================================================");
    println!("Bug C (#196): ask() 'frame id out of range' -- Rust reproduction");
    println!("================================================================");
    println!();
    println!("  memvid-core: 2.0.137 (crates.io)");
    println!("  file:        {}", path);
    println!();

    // ------------------------------------------------------------------
    // Step 1 -- Open the file
    // ------------------------------------------------------------------
    println!("--- Step 1: Open .mv2 ---");
    let mut mem = match Memvid::open_read_only(path) {
        Ok(m) => {
            println!("  OK: frame_count = {}", m.frame_count());
            m
        }
        Err(e) => {
            eprintln!("  FAILED to open: {}", e);
            process::exit(1);
        }
    };
    println!();

    // ------------------------------------------------------------------
    // Step 2 -- search() baseline (usually succeeds)
    // ------------------------------------------------------------------
    println!("--- Step 2: search() baseline ---");
    let search_req = memvid_core::SearchRequest {
        query: "Python programming".to_string(),
        top_k: 5,
        snippet_chars: 300,
        uri: None,
        scope: None,
        cursor: None,
        as_of_frame: None,
        as_of_ts: None,
        no_sketch: false,
        acl_context: None,
        acl_enforcement_mode: memvid_core::AclEnforcementMode::Audit,
    };
    match mem.search(search_req) {
        Ok(results) => {
            println!("  OK: {} hits", results.hits.len());
            for (i, h) in results.hits.iter().enumerate().take(3) {
                println!("    [{}] score={:?}  text={:.80}", i, h.score, h.text);
            }
        }
        Err(e) => {
            eprintln!("  FAILED: {}", e);
        }
    }
    println!();

    // ------------------------------------------------------------------
    // Step 3 -- ask() with context_only=true (the bug trigger)
    // ------------------------------------------------------------------
    println!("--- Step 3: ask(context_only=true) -- the bug trigger ---");
    let ask_req = memvid_core::AskRequest {
        question: "What programming languages are discussed?".to_string(),
        top_k: 5,
        snippet_chars: 300,
        mode: memvid_core::AskMode::Hybrid,
        context_only: true,
        start: None,
        end: None,
        uri: None,
        scope: None,
        cursor: None,
        as_of_frame: None,
        as_of_ts: None,
        adaptive: None,
        acl_context: None,
        acl_enforcement_mode: memvid_core::AclEnforcementMode::Audit,
    };
    match mem.ask(ask_req, None::<&dyn memvid_core::VecEmbedder>) {
        Ok(resp) => {
            println!("  OK: {} context fragments", resp.context_fragments.len());
            if let Some(answer) = &resp.answer {
                println!("  answer: {:.200}", answer);
            } else {
                println!("  answer: <none, context_only mode>");
            }
        }
        Err(e) => {
            eprintln!("  FAILED: {}", e);
            eprintln!();
            eprintln!("--- Verdict ---");
            eprintln!(
                "FAIL: ask() raises '{}' on a file with {} frames.",
                e,
                mem.frame_count()
            );
            eprintln!("Bug #196 is NOT fixed.");
            eprintln!();
            eprintln!("Workaround: memvid doctor --rebuild-time-index <path>");
            process::exit(1);
        }
    }
    println!();

    // ------------------------------------------------------------------
    // Step 4 -- Determinism (5 trials)
    // ------------------------------------------------------------------
    println!("--- Step 4: Determinism check (5 trials) ---");
    let mut passes = 0u32;
    let mut fails = 0u32;
    for trial in 1..=5 {
        let req = memvid_core::AskRequest {
            question: "Tell me about cloud experience".to_string(),
            top_k: 5,
            snippet_chars: 300,
            mode: memvid_core::AskMode::Hybrid,
            context_only: true,
            start: None,
            end: None,
            uri: None,
            scope: None,
            cursor: None,
            as_of_frame: None,
            as_of_ts: None,
            adaptive: None,
            acl_context: None,
            acl_enforcement_mode: memvid_core::AclEnforcementMode::Audit,
        };
        match mem.ask(req, None::<&dyn memvid_core::VecEmbedder>) {
            Ok(_) => {
                passes += 1;
                println!("  Trial {}: PASS", trial);
            }
            Err(e) => {
                fails += 1;
                println!("  Trial {}: FAIL -- {}", trial, e);
            }
        }
    }
    println!("  Result: {}/5 passed, {}/5 failed", passes, fails);
    println!();

    // ------------------------------------------------------------------
    // Verdict
    // ------------------------------------------------------------------
    println!("--- Verdict ---");
    if fails == 0 {
        println!("PASS: ask() works. Bug appears FIXED.");
    } else {
        println!(
            "FAIL: ask() raises 'frame id out of range' ({}/5 deterministic failures).",
            fails
        );
        println!("Bug #196 is NOT fixed.");
        println!();
        println!("Workaround: memvid doctor --rebuild-time-index <path>");
    }
}
