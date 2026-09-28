#!/usr/bin/env bash
# shellcheck shell=bash
# cpf-shellcheck.sh -- run the shellcheck version pinned in the project's
# .tool-versions (asdf format: `shellcheck 0.11.0`).
#
# On first use, downloads the upstream release tarball for this OS/arch,
# verifies its sha256 against the table below, and caches the binary under
# ${CPF_TOOLS_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/cpf-dev-tools}. All
# arguments are passed through. `--print-path` prints the binary path
# instead of running it. Exits 1 when the project pins no shellcheck
# version (callers then fall back to an unpinned shellcheck, if any).
#
# The project root is CPF_PROJECT_ROOT, else $CLAUDE_PROJECT_DIR, else the
# git top level, else $PWD. To support a new version, add its checksums
# (sha256 of each .tar.xz release asset) to sha256_for.
set -euo pipefail

PROJECT_ROOT="${CPF_PROJECT_ROOT:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
VERSION=""
if [[ -f "$PROJECT_ROOT/.tool-versions" ]]; then
    VERSION="$(awk '$1 == "shellcheck" { print $2 }' "$PROJECT_ROOT/.tool-versions")"
fi
if [[ -z "$VERSION" ]]; then
    echo "cpf-shellcheck: .tool-versions pins no shellcheck version" >&2
    exit 1
fi

sha256_for() {
    case "$1" in
        0.11.0/linux.x86_64) echo 8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198 ;;
        0.11.0/linux.aarch64) echo 12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588 ;;
        0.11.0/darwin.x86_64) echo 3c89db4edcab7cf1c27bff178882e0f6f27f7afdf54e859fa041fca10febe4c6 ;;
        0.11.0/darwin.aarch64) echo 56affdd8de5527894dca6dc3d7e0a99a873b0f004d7aabc30ae407d3f48b0a79 ;;
        *) return 1 ;;
    esac
}

CACHE_ROOT="${CPF_TOOLS_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/cpf-dev-tools}"
BIN_DIR="$CACHE_ROOT/shellcheck-v$VERSION"
BIN="$BIN_DIR/shellcheck"

file_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    else
        shasum -a 256 "$1" | cut -d' ' -f1
    fi
}

install_shellcheck() {
    local os arch
    case "$(uname -s)" in
        Linux) os=linux ;;
        Darwin) os=darwin ;;
        *)
            echo "shellcheck.sh: unsupported OS $(uname -s)" >&2
            exit 1
            ;;
    esac
    case "$(uname -m)" in
        x86_64 | amd64) arch=x86_64 ;;
        arm64 | aarch64) arch=aarch64 ;;
        *)
            echo "shellcheck.sh: unsupported arch $(uname -m)" >&2
            exit 1
            ;;
    esac

    local expected
    if ! expected="$(sha256_for "$VERSION/$os.$arch")"; then
        echo "shellcheck.sh: no checksum for $VERSION ($os.$arch);" \
            "add it to sha256_for" >&2
        exit 1
    fi

    local asset="shellcheck-v${VERSION}.${os}.${arch}.tar.xz"
    local url="https://github.com/koalaman/shellcheck/releases/download/v${VERSION}/${asset}"
    local tmp
    tmp="$(mktemp -d)"
    # shellcheck disable=SC2064  # expand $tmp now; it is local
    trap "rm -rf '$tmp'" EXIT

    echo "shellcheck.sh: installing $VERSION ($os.$arch)" >&2
    curl -fsSL --retry 3 -o "$tmp/$asset" "$url"
    local actual
    actual="$(file_sha256 "$tmp/$asset")"
    if [[ "$actual" != "$expected" ]]; then
        echo "shellcheck.sh: checksum mismatch for $asset" >&2
        echo "  expected $expected" >&2
        echo "  actual   $actual" >&2
        exit 1
    fi
    tar -xJf "$tmp/$asset" -C "$tmp"
    mkdir -p "$BIN_DIR"
    mv "$tmp/shellcheck-v${VERSION}/shellcheck" "$BIN.tmp.$$"
    chmod +x "$BIN.tmp.$$"
    mv "$BIN.tmp.$$" "$BIN"
}

[[ -x "$BIN" ]] || install_shellcheck

if [[ "${1:-}" == "--print-path" ]]; then
    echo "$BIN"
    exit 0
fi
exec "$BIN" "$@"
