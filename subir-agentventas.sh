#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
bash "AgentVentas BOT/scripts/subir_a_github.sh" "$@"
