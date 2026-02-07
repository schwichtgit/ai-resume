#!/usr/bin/env python3
"""
Startup wrapper for AI Resume API with IPv4/IPv6 auto-detection.

This script attempts to bind to dual-stack (::) first, falling back to
IPv4-only (0.0.0.0) if IPv6 is not available on the system.

Supports environment variables:
- BIND_ADDRESS: Explicit bind address (default: auto-detect)
- PORT: HTTP port (default: 3000)
"""

import os
import socket
import sys
import subprocess

# Ensure we're in /app for module imports
# The ai_resume_api module needs to be importable
os.chdir("/app")
sys.path.insert(0, "/app")


def can_bind_ipv6_dualstack(port: int) -> bool:
    """Test if we can bind to IPv6 with dual-stack support on the given port.

    Returns True only if both IPv6 and IPv4 will work via the :: binding.
    """
    try:
        # Create IPv6 socket and explicitly disable IPv6-only mode
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Disable IPV6_V6ONLY to enable dual-stack (IPv4 + IPv6)
        # This makes :: bind to both IPv4 and IPv6
        try:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            # IPV6_V6ONLY not supported or can't be disabled
            sock.close()
            return False

        sock.bind(("::", port))
        sock.close()
        return True
    except (OSError, socket.error):
        return False


def main() -> None:
    """Start uvicorn with auto-detected or explicit bind address."""
    port = int(os.getenv("PORT", "3000"))
    bind_address = os.getenv("BIND_ADDRESS", "auto")

    if bind_address == "auto":
        # Auto-detect: Try IPv6 first, fall back to IPv4
        if can_bind_ipv6_dualstack(port):
            host = "::"
            print(f"Auto-detected dual-stack support, binding to [::]:{port}", file=sys.stderr)
        else:
            host = "0.0.0.0"
            print(f"IPv6 not available, binding to 0.0.0.0:{port}", file=sys.stderr)
    else:
        host = bind_address
        print(f"Using explicit bind address: {host}:{port}", file=sys.stderr)

    # Start uvicorn programmatically to control socket options
    if host == "::":
        # Use programmatic API to ensure IPV6_V6ONLY=0 is set
        import uvicorn
        import asyncio

        print(f"Starting uvicorn with dual-stack socket [::]:{port}", file=sys.stderr)
        print("Note: Setting IPV6_V6ONLY=0 for dual-stack support", file=sys.stderr)

        async def run_server() -> None:
            # Create socket with proper options
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # Enable dual-stack
            sock.bind(("::", port))
            sock.listen(128)
            sock.setblocking(False)

            # Pass socket to uvicorn
            config_with_socket = uvicorn.Config("ai_resume_api.main:app", log_level="info")
            server_with_socket = uvicorn.Server(config_with_socket)
            await server_with_socket.serve(sockets=[sock])

        asyncio.run(run_server())
    else:
        # IPv4-only - use CLI for simplicity
        cmd = [
            "uvicorn",
            "ai_resume_api.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ]
        print(f"Starting: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
