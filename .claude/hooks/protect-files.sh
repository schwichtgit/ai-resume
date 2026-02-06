#!/bin/bash
# Protect-files hook: Block edits to sensitive files
# This hook is called before Claude Code edits a file

set -euo pipefail

# Claude Code hooks receive JSON on stdin, not as positional arguments.
# For PreToolUse hooks, the JSON structure is:
# { "tool_name": "Write", "tool_input": { "file_path": "/path/to/file", ... } }
INPUT=$(cat /dev/stdin 2>/dev/null) || true

if [[ -z "$INPUT" ]]; then
    # No input provided, nothing to validate
    exit 0
fi

# Parse the file_path from the JSON input using python3
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except (json.JSONDecodeError, KeyError, TypeError):
    print('')
" 2>/dev/null) || true

if [[ -z "$FILE_PATH" ]]; then
    # Could not parse file path from JSON, allow execution
    exit 0
fi

# Get just the filename for pattern matching
FILENAME=$(basename "$FILE_PATH")

# Define protected file patterns
PROTECTED_PATTERNS=(
    # Environment files
    ".env"
    ".env.local"
    ".env.development"
    ".env.production"
    ".env.staging"
    ".env.*"

    # SSH keys
    "id_rsa"
    "id_rsa.pub"
    "id_ed25519"
    "id_ed25519.pub"
    "id_ecdsa"
    "id_ecdsa.pub"
    "authorized_keys"
    "known_hosts"

    # Certificates and keys
    "*.pem"
    "*.key"
    "*.crt"
    "*.p12"
    "*.pfx"

    # Credentials and secrets
    "*credentials*"
    "*secret*"
    "*password*"
    "*token*"
    "*.keystore"

    # Cloud provider configs
    "gcloud-*.json"
    "service-account*.json"
    "aws-credentials"

    # Package lock files (prevent tampering)
    "package-lock.json"
    "yarn.lock"
    "pnpm-lock.yaml"
    "Cargo.lock"
    "poetry.lock"
)

# Check if file matches any protected pattern
for pattern in "${PROTECTED_PATTERNS[@]}"; do
    # Handle glob patterns
    if [[ "$FILENAME" == $pattern ]] || [[ "$FILE_PATH" == *"$pattern"* ]]; then
        # Special case: allow reading but warn
        echo "WARNING: Attempting to modify protected file: $FILE_PATH"
        echo "Pattern matched: $pattern"

        # For env files and credentials, block completely
        case "$FILENAME" in
            .env*|*credentials*|*secret*|*password*|id_rsa*|id_ed25519*|*.pem|*.key)
                echo "BLOCKED: This file type is protected and cannot be modified"
                exit 1
                ;;
            *lock*)
                echo "BLOCKED: Lock files should not be manually modified"
                exit 1
                ;;
        esac
    fi
done

# Additional check for files in sensitive directories
SENSITIVE_DIRS=(
    ".ssh"
    ".gnupg"
    ".aws"
    ".gcloud"
    ".config/gcloud"
)

for dir in "${SENSITIVE_DIRS[@]}"; do
    if [[ "$FILE_PATH" == *"/$dir/"* ]] || [[ "$FILE_PATH" == *"$dir/"* ]]; then
        echo "BLOCKED: Files in $dir directory are protected"
        exit 1
    fi
done

# All checks passed
exit 0
