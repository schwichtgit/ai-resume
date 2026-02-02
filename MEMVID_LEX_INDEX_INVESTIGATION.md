# Memvid Lexical Index Disabled Investigation

**Branch**: `investigate/memvid-lex-index-disabled`
**Issue**: Lexical (BM25) and vector (semantic) indexes marked as disabled at runtime
**Status**: 🔍 Active Investigation
**Discovered**: 2026-02-02

## Problem Statement

The `.mv2` file created by `memvid-sdk` (PyPI v2.0.153) has indexes physically present but disabled at runtime:

```
File: data/.memvid/resume.mv2
Size: 306,149 bytes
Frames: 20

Index Storage      │ Index Runtime
─────────────────────────────────
✓ lex_index_bytes: 63,168 bytes │ ✗ lex_enabled: false
✓ vec_index_bytes: 49,440 bytes │ ✗ vec_enabled: false
```

### Symptom
All semantic/lexical queries fail:
```
mem.find("query", mode="lex")  → LexIndexDisabledError: MV004
mem.find("query", mode="sem")  → MV011: Vector index is not enabled
mem.find("query", mode="auto") → LexIndexDisabledError: MV004
```

### Workaround Available
O(1) profile state lookup works fine:
```python
mem.state("__profile__")  → ✓ Returns full profile JSON
```

## Hypothesis Chain

### H1: SDK/Core Serialization Mismatch (Likely)
- **memvid-sdk** (v2.0.153, PyPI): Uses newer internal Rust core
- **memvid-core** (v2.0.135, crates.io): Cannot decode lex/vec indexes
- **Result**: Indexes exist but fail deserialization → marked as disabled

**Evidence**:
- Matches issue reported to Saleban Olow
- Python SDK's own `find()` fails identically
- File metadata shows `has_lex_index=true` but `lex_enabled=false`

### H2: Ingest Script Configuration
- `ingest.py` calls `memvid_sdk.create(..., enable_lex=True, enable_vec=True)`
- Indexes are built and serialized at creation time
- Something disables them on re-open

**Test**: Check if re-creating the .mv2 with different settings helps

### H3: File Corruption or Incomplete Write
- File size: 306,149 bytes (reasonable)
- No checksums or validation errors reported
- Unlikely but possible

## Investigation Plan

### Phase 1: Reproduce with Minimal Example ✅
- [x] Test with basic memvid-sdk operations
- [x] Confirm indexes can't be read back
- [x] Verify API fallback works

**Result**: Confirmed - indexes disabled at runtime despite data present

### Phase 2: Test SDK Versions (TODO)
- [ ] Try memvid-sdk v2.0.152 (older)
- [ ] Try memvid-sdk v2.0.154 (if available)
- [ ] Document which versions have working lex/vec

### Phase 3: Test Ingest Configuration (TODO)
- [ ] Reingest with `enable_lex=False, enable_vec=False`
- [ ] Reingest with `enable_lex=True, enable_vec=False` (lex only)
- [ ] Reingest with alternative chunking strategy

### Phase 4: Core Version Compatibility (TODO)
- [ ] Check if memvid-core has newer release
- [ ] Test if Rust wrapper can read the indexes

## Testing Commands

### Activate Environment
```bash
source ingest/.venv/bin/activate
```

### Run Diagnostic
```bash
python ingest/test_memvid.py  # TODO: Create this script
```

### Check Current Status
```bash
python << 'EOF'
import memvid_sdk

mem = memvid_sdk.use("basic", "data/.memvid/resume.mv2")
stats = mem.stats()

print(f"has_lex_index: {stats.get('has_lex_index')}")
print(f"lex_enabled: {stats.get('lex_enabled')}")
print(f"has_vec_index: {stats.get('has_vec_index')}")
print(f"vec_enabled: {stats.get('vec_enabled')}")

mem.close()
EOF
```

## Communication with Saleban

**Reported**: Issue acknowledged by Saleban Olow
**Status**: Waiting for memvid v2.0.136+ release with fix
**Reference**: Email thread on SDK/Core compatibility

## Deployment Impact

**Current State**:
- ✓ Profile API endpoint works (O(1) lookup)
- ✗ Semantic search endpoint degraded
- ✗ FAQ/context retrieval broken
- Fallback: Mock search in api-service active

**Fix Priority**: High (blocks key features)

## Next Steps

1. Monitor [memvid/memvid](https://github.com/memvid/memvid/releases) for v2.0.136+
2. Test new SDK version when available
3. If not resolved, explore:
   - Rolling back SDK version
   - Reimplementing search fallback
   - Alternative embedding provider
4. Document findings in this branch

## Related Files

- `ingest/ingest.py` - Creates .mv2 file (lines 583-588)
- `api-service/ai_resume_api/memvid_client.py` - Queries .mv2 file
- `data/.memvid/resume.mv2` - Affected file
- TRIAGE_REPORT.md - Initial investigation (scratchpad)

## References

- SDK Issue: [memvid-sdk PyPI](https://pypi.org/project/memvid-sdk/)
- Core Crate: [memvid-core crates.io](https://crates.io/crates/memvid-core)
- GitHub: [memvid/memvid](https://github.com/memvid/memvid)
