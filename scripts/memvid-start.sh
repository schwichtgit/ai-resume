#!/bin/bash
# Start the memvid gRPC service locally on macOS
# Usage: ./memvid-start.sh [options]
#
# Options:
#   --mock           Use mock data (for testing without resume.mv2)
#   --port PORT      Set gRPC port (default: 50051)
#   --metrics PORT   Set metrics port (default: 9090)

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY="$SCRIPT_DIR/memvid-service/target/release/memvid-service"

# Check if binary exists
if [ ! -f "$BINARY" ]; then
    echo "Error: memvid-service binary not found at $BINARY"
    echo "Please run: cd memvid-service && cargo build --release"
    exit 1
fi

# Parse arguments
MOCK_MEMVID=false
GRPC_PORT=50051
METRICS_PORT=9090

while [[ $# -gt 0 ]]; do
    case $1 in
        --mock)
            MOCK_MEMVID=true
            shift
            ;;
        --port)
            GRPC_PORT=$2
            shift 2
            ;;
        --metrics)
            METRICS_PORT=$2
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--mock] [--port PORT] [--metrics PORT]"
            exit 1
            ;;
    esac
done

# Set environment variables
export MOCK_MEMVID=$MOCK_MEMVID
export GRPC_PORT=$GRPC_PORT
export METRICS_PORT=$METRICS_PORT
export MEMVID_FILE_PATH="$SCRIPT_DIR/data/.memvid/resume.mv2"
export RUST_LOG=info

echo "Starting memvid gRPC service..."
echo "  Binary: $BINARY"
echo "  gRPC Port: $GRPC_PORT"
echo "  Metrics Port: $METRICS_PORT"
echo "  Mock Mode: $MOCK_MEMVID"
if [ "$MOCK_MEMVID" = "false" ]; then
    echo "  Resume File: $MEMVID_FILE_PATH"
fi
echo ""
echo "Endpoints:"
echo "  gRPC: localhost:$GRPC_PORT"
echo "  Metrics: http://localhost:$METRICS_PORT/metrics"
echo ""

# Run the service
exec "$BINARY"
