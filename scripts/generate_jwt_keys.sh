#!/usr/bin/env bash
# Generate RS256 JWT key pair for AIFlow authentication.
# Usage: ./scripts/generate_jwt_keys.sh [private_key_path] [public_key_path]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

PRIVATE_KEY="${1:-$PROJECT_DIR/jwt_private.pem}"
PUBLIC_KEY="${2:-$PROJECT_DIR/jwt_public.pem}"

if [[ -f "$PRIVATE_KEY" ]]; then
    echo "ERROR: Private key already exists: $PRIVATE_KEY"
    echo "Delete it first if you want to regenerate."
    exit 1
fi

echo "Generating RS256 2048-bit key pair..."
openssl genrsa -out "$PRIVATE_KEY" 2048 2>/dev/null
openssl rsa -in "$PRIVATE_KEY" -pubout -out "$PUBLIC_KEY" 2>/dev/null
chmod 600 "$PRIVATE_KEY"
chmod 644 "$PUBLIC_KEY"

echo "Generated:"
echo "  Private key: $PRIVATE_KEY"
echo "  Public key:  $PUBLIC_KEY"
echo ""
echo "Add to .env:"
echo "  AIFLOW_JWT_PRIVATE_KEY_PATH=$PRIVATE_KEY"
echo "  AIFLOW_JWT_PUBLIC_KEY_PATH=$PUBLIC_KEY"
