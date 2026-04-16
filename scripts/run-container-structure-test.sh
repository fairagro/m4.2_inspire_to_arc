#!/bin/bash
set -e

echo "🔧 Building Docker image for container structure test..."
docker build -f docker/Dockerfile.harvester -t inspire-to-arc:test .

echo "🔍 Running Container Structure Test..."
container-structure-test test \
    --image inspire-to-arc:test \
    --config docker/container-structure-tests/inspire.yaml
