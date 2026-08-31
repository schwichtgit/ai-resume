#!/bin/bash
# Fail if the committed protobuf stubs are stale relative to the locked
# grpcio-tools.
#
# The stubs under api-service/ai_resume_api/proto/ are generated artifacts that
# are checked in, and they carry import-time guards -- GRPC_GENERATED_VERSION
# and ValidateProtobufRuntimeVersion -- that raise RuntimeError, not a warning,
# when the installed runtime is older than whatever generated them. Nothing
# regenerates them automatically, so a grpcio-tools bump silently widens the gap
# between the declared generator and the committed output. This closes that:
# regenerate, compare, restore, and report.
#
# The working tree is left exactly as found, pass or fail.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

STUB_DIR="api-service/ai_resume_api/proto/memvid/v1"
STUBS=("memvid_pb2.py" "memvid_pb2_grpc.py")

SNAPSHOT="$(mktemp -d)"
restore() {
    local f
    for f in "${STUBS[@]}"; do
        [ -f "$SNAPSHOT/$f" ] && cp "$SNAPSHOT/$f" "$STUB_DIR/$f"
    done
    rm -rf "$SNAPSHOT"
}
trap restore EXIT

for f in "${STUBS[@]}"; do
    cp "$STUB_DIR/$f" "$SNAPSHOT/$f"
done

./scripts/gen-proto.sh >/dev/null

DRIFTED=0
for f in "${STUBS[@]}"; do
    if ! diff -q "$SNAPSHOT/$f" "$STUB_DIR/$f" >/dev/null; then
        DRIFTED=1
        echo "DRIFT: $STUB_DIR/$f differs from freshly generated output" >&2
        diff -u "$SNAPSHOT/$f" "$STUB_DIR/$f" | head -40 >&2
    fi
done

if [ "$DRIFTED" -ne 0 ]; then
    cat >&2 <<'MSG'

The committed stubs do not match what the locked grpcio-tools generates.
Regenerate and commit them in the same change that moved the tooling:

    ./scripts/gen-proto.sh

Check the resulting GRPC_GENERATED_VERSION and ValidateProtobufRuntimeVersion
values -- if they rose, the grpcio / protobuf floors in
api-service/pyproject.toml must rise with them, or the service will fail at
import wherever an older runtime resolves.
MSG
    exit 1
fi

echo "Protobuf stubs are in sync with the locked grpcio-tools."
