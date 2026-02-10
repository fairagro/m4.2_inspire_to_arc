#!/bin/bash
set -e

echo "🔧 Building Docker image for container structure test..."
docker build -f docker/Dockerfile.sql_to_arc -t sql-to-arc:test .

echo "🔍 Running Container Structure Test..."
container-structure-test test \
    --image sql-to-arc:test \
    --config docker/container-structure-tests/sql_to_arc.yaml
