#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if command -v pnpm >/dev/null 2>&1; then
  pnpm install
  pnpm dev
else
  npm install
  npm run dev
fi
