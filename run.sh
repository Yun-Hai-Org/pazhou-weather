#!/usr/bin/env bash
set -euo pipefail
exec uv run --env-file .env main.py
