#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# package-report.sh -- Bundle the upstream bug report and artifacts into a
# distributable zip archive.
#
# Usage:
#     cd memvid_issues/
#     ./package-report.sh
#
# Output:
#     memvid_issues/memvid-bug-report-2026-02-20.zip
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DATE="2026-02-20"
ARCHIVE="memvid-bug-report-${DATE}.zip"

echo "Packaging upstream bug report..."
echo

# Verify required files exist
REQUIRED_FILES=(
    "UPSTREAM_REPORT.md"
    "repro_bug_a.py"
    "repro_bug_c.py"
    "repro_bug_c_rust/Cargo.toml"
    "repro_bug_c_rust/src/main.rs"
)

MISSING=0
for f in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$f" ]; then
        echo "  MISSING: $f"
        MISSING=$((MISSING + 1))
    fi
done
if [ "$MISSING" -gt 0 ]; then
    echo "ERROR: ${MISSING} required file(s) missing. Aborting."
    exit 1
fi

# Build file list
FILES_TO_ZIP=()
for f in "${REQUIRED_FILES[@]}"; do
    FILES_TO_ZIP+=("$f")
done

# Include test artifacts if present
if [ -f "2/output/cross_version_test.mv2" ]; then
    FILES_TO_ZIP+=("2/output/cross_version_test.mv2")
    echo "  Including artifact: 2/output/cross_version_test.mv2"
fi
if [ -f "3/output/time_index_test.mv2" ]; then
    FILES_TO_ZIP+=("3/output/time_index_test.mv2")
    echo "  Including artifact: 3/output/time_index_test.mv2"
fi

echo

# Remove old archive if present
rm -f "$ARCHIVE"

# Create zip
zip -r "$ARCHIVE" "${FILES_TO_ZIP[@]}"

echo
echo "Archive created: ${SCRIPT_DIR}/${ARCHIVE}"
echo "Size: $(du -h "$ARCHIVE" | cut -f1)"
echo
echo "Contents:"
unzip -l "$ARCHIVE"
