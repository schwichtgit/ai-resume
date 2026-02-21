# Memvid Upstream Bug Report

**Date:** 2026-02-20
**Reporter:** Frank Schwichtenberg (ai-resume project)
**Repository:** https://github.com/schwichtgit/ai-resume

---

## Summary

We retested all three previously reported issues against the latest available
releases. One issue is now resolved; two remain.

| Issue | Title | Status | Versions Tested |
|-------|-------|--------|-----------------|
| [#194](https://github.com/memvid/memvid/issues/194) | `vec_enabled`/`lex_enabled` reset to `None` on re-open | **NOT FIXED** | SDK 2.0.157, Core 2.0.137 |
| [#195](https://github.com/memvid/memvid/issues/195) | Cross-version deserialization failure (SDK vs crates.io) | **FIXED** | SDK 2.0.157, Core 2.0.137 |
| [#196](https://github.com/memvid/memvid/issues/196) | `ask()` "frame id out of range" on fresh .mv2 files | **NOT FIXED** | SDK 2.0.157, Core 2.0.137 |

## Test Environment

| Component | Version |
|-----------|---------|
| memvid-sdk (PyPI) | 2.0.157 |
| memvid-core (bundled in SDK) | 2.0.137 |
| memvid-core (crates.io) | 2.0.137 |
| Python | 3.12 |
| Rust | stable 1.84 |
| Platform | macOS Darwin 25.3.0 (arm64) |

---

## Issue #195 -- FIXED (Thank You)

**Cross-version deserialization failure between SDK-bundled core and crates.io core.**

This is resolved. SDK 2.0.157 now bundles memvid-core 2.0.137, which matches
the latest crates.io release. Files created by the SDK can be opened by
standalone Rust code linked against `memvid-core = "2.0.137"` without
deserialization errors. We verified this with both newly created files and the
original test artifact from the initial report.

Thank you for addressing this.

---

## Issue #194 -- NOT FIXED

### Title

`vec_enabled` and `lex_enabled` reset to `None` after close/re-open

### Severity

Medium-High. Semantic search (`mode="semantic"`) is completely broken after
re-opening a file. Hybrid search silently degrades to lexical-only, returning
lower-quality results without any indication to the caller.

### Reproduction

**Minimal steps:**

```python
import os, tempfile, memvid_sdk

with tempfile.TemporaryDirectory() as tmpdir:
    path = os.path.join(tmpdir, "test.mv2")

    # 1. Create with both indexes enabled
    mem = memvid_sdk.create(path, kind="basic", enable_lex=True, enable_vec=True)
    mem.put(title="Doc 1", text="Python is a programming language.", tags=["t"])
    mem.put(title="Doc 2", text="Rust is a systems language.", tags=["t"])
    mem.put(title="Doc 3", text="TypeScript adds types to JavaScript.", tags=["t"])
    print(mem.stats())
    # -> lex_enabled: True, vec_enabled: True, has_lex_index: True, has_vec_index: True
    mem.close()

    # 2. Re-open
    mem2 = memvid_sdk.use("basic", path)
    print(mem2.stats())
    # -> lex_enabled: None, vec_enabled: None  <-- BUG

    # 3. Semantic search fails
    mem2.find("Python", k=2, mode="semantic")
    # -> VecIndexDisabledError [MV011]

    # 4. Hybrid silently degrades to lexical-only
    mem2.find("Python", k=2, mode="hybrid")
    # -> Returns results, but only from lexical index (no vector component)
```

**Self-contained script:** `repro_bug_a.py` (attached)

### Expected Behavior

After `memvid_sdk.use("basic", path)`, `stats()` should report
`lex_enabled: True` and `vec_enabled: True` (matching the flags used at
creation time), and all three find modes (lexical, semantic, hybrid) should
work.

### Actual Behavior

- `stats()` reports `lex_enabled: None` and `vec_enabled: None`
- `find(mode="semantic")` raises `VecIndexDisabledError [MV011]`
- `find(mode="hybrid")` returns results but uses lexical scoring only
- `has_lex_index` and `has_vec_index` remain `True`, confirming the index
  data is present in the file -- only the enabled flags are lost

### Impact on Our Project

We use memvid for a gRPC semantic search service. After the gRPC server
re-opens a `.mv2` file (normal startup behavior), semantic search is
unavailable. We currently have no workaround for this bug -- our service
falls back to lexical-only search, which significantly reduces retrieval
quality for natural-language queries.

### Suspected Root Cause

The `enable_lex` / `enable_vec` flags are not being persisted in the .mv2
file metadata (or are not being read back during deserialization). The index
data itself is serialized correctly (`has_lex_index` / `has_vec_index` are
true), but the feature-gate flags that control whether the indexes are
*used* during search are lost on re-open.

---

## Issue #196 -- NOT FIXED

### Title

`ask()` fails with "Time index track is invalid: frame id out of range"
on fresh .mv2 files

### Severity

High. `ask()` is completely unusable on files with 12+ frames of varied
content unless the user manually runs `memvid doctor --rebuild-time-index`
after every file creation. This defeats the purpose of the SDK's
create-then-query workflow.

### Reproduction

**Minimal steps:**

```python
import tempfile, os, memvid_sdk

# 12 varied-content chunks (simulating a real resume)
docs = [
    ("Summary", "Technology leader with 15+ years in software engineering."),
    ("Company A", "Led 50+ engineers. Microservices migration. CI/CD automation."),
    ("Company B", "Real-time pipeline, 10M events/day. Hybrid search system."),
    ("Company C", "Managed 12 engineers. TypeScript migration. API platform."),
    ("Strong Skills", "Python, Rust, TypeScript, React, FastAPI, gRPC, K8s."),
    ("Moderate Skills", "Go, Java, Terraform, Azure, GCP, MongoDB."),
    ("Gaps", "Solidity, blockchain, mobile dev, game dev, embedded."),
    ("Education", "MS Computer Science. BS Mathematics."),
    ("Certifications", "AWS SA Pro, CKA, Terraform Associate."),
    ("Publications", "Distributed consensus paper. Technical blog posts."),
    ("Fit Strong", "VP Engineering at startup. 4-star rating."),
    ("Fit Weak", "Executive Chef. Different domain. 1-star rating."),
]

with tempfile.TemporaryDirectory() as tmpdir:
    path = os.path.join(tmpdir, "test.mv2")
    mem = memvid_sdk.create(path, kind="basic", enable_lex=True, enable_vec=True)
    for title, text in docs:
        mem.put(title=title, text=text, tags=["resume"])
    mem.close()

    mem2 = memvid_sdk.use("basic", path)
    memvid_sdk.ask(mem2, "What languages are discussed?", top_k=3)
    # -> ERROR: "Time index track is invalid: frame id out of range"
```

**Self-contained scripts:**
- `repro_bug_c.py` -- Python reproduction (attached)
- `repro_bug_c_rust/` -- Rust reproduction using `memvid-core = "2.0.137"` (attached)

### Expected Behavior

`ask()` should return context fragments (and optionally an answer) from a
freshly created .mv2 file without requiring any post-creation repair step.

### Actual Behavior

`ask()` raises:

```
Time index track is invalid: frame id out of range
```

- **Deterministic:** Fails 5/5 trials on the same file.
- **Content-dependent:** Requires 12+ frames of varied content to trigger.
  Files with fewer frames or uniform short content may not trigger the bug.
- **search() unaffected:** `mem.search()` / `mem.find(mode="lexical")` work
  fine on the same file. The bug is specific to the `ask()` code path (and
  its time-index traversal logic).
- **Timestamps not required:** The bug occurs with or without explicit
  `timestamp` parameters on `put()`.

### Characterization from Testing

We ran extensive boundary testing to characterize the trigger conditions:

| Frames | Content | Timestamps | ask() Result |
|--------|---------|------------|--------------|
| 1-7 | Short uniform | No | PASS |
| 1-7 | Short uniform | Yes | PASS |
| 5 | Medium varied | No | PASS |
| 5 | Medium varied | Yes | PASS |
| 12 | Realistic varied | No | **FAIL** |
| 12 | Realistic varied | Yes | **FAIL** |

The trigger appears related to the total content volume and frame count
rather than the presence of explicit timestamps.

### Workaround

Running `memvid doctor --rebuild-time-index <path>` after file creation
resolves the issue. We have integrated this into our ingestion pipeline
as a post-processing step:

```bash
# After creating the .mv2 file:
memvid doctor --rebuild-time-index data/.memvid/resume.mv2
```

This is functional but adds an extra step and dependency on the CLI tool
being available in the deployment environment.

### Suspected Root Cause

The time-index track built during `create()` + `put()` + `close()` contains
frame ID references that are inconsistent with the final frame layout.
Possibly the time-index is being built incrementally during `put()` but
references frame IDs that are renumbered or compacted during `close()`.
The `doctor --rebuild-time-index` command reconstructs the index from the
final frame layout, which is why it fixes the problem.

---

## Attached Artifacts

This report is distributed as a zip archive containing:

```
UPSTREAM_REPORT.md           -- This document
repro_bug_a.py               -- Self-contained Python reproduction for #194
repro_bug_c.py               -- Self-contained Python reproduction for #196
repro_bug_c_rust/
    Cargo.toml               -- Minimal Rust project for #196 reproduction
    src/main.rs              -- Rust reproduction binary
2/output/
    cross_version_test.mv2   -- Original #195 test artifact (for reference)
3/output/
    time_index_test.mv2      -- Original #196 test artifact (pre-fix .mv2)
```

### Running the Python reproductions

```bash
pip install memvid-sdk==2.0.157
python repro_bug_a.py
python repro_bug_c.py
```

### Running the Rust reproduction

```bash
# First create a test .mv2 with the Python script:
python repro_bug_c.py
# Note the .mv2 path from the output, then:
cd repro_bug_c_rust
cargo run --release -- /path/to/bug_c_test.mv2
```

### Pre-built test artifacts

The `2/output/cross_version_test.mv2` and `3/output/time_index_test.mv2`
files were created during the original bug reporting session (2026-02-07)
using earlier SDK/core versions. They are included for reference and
historical comparison. The reproduction scripts create fresh files using
the latest versions.

---

## Request

We would appreciate any guidance on:

1. **Issue #194:** Is there a planned fix for the `enable_lex`/`enable_vec`
   flag persistence? Is there a workaround we may be missing (e.g., a
   different API to re-open files that preserves the flags)?

2. **Issue #196:** Is the `doctor --rebuild-time-index` workaround expected
   to remain stable? Would it be feasible to run the time-index rebuild
   automatically during `close()` to prevent the inconsistency?

Thank you for your work on memvid. We are happy to provide additional test
data or run further experiments if that would help with diagnosis.
