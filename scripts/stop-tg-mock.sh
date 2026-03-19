#!/usr/bin/env bash
# Stop tg-mock container
# Usage: bash scripts/stop-tg-mock.sh

set -euo pipefail

if docker ps -q --filter name=sarthi-tg-mock | grep -q .; then
    echo "Stopping tg-mock..."
    docker stop sarthi-tg-mock >/dev/null 2>&1
    docker rm sarthi-tg-mock >/dev/null 2>&1
    echo "✅ tg-mock stopped"
else
    echo "tg-mock is not running"
fi
