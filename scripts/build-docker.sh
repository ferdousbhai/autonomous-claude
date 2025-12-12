#!/usr/bin/env bash
# Build Docker image for autonomous-claude sandbox
#
# Usage:
#   ./scripts/build-docker.sh              # Build with latest tag
#   ./scripts/build-docker.sh v1.0.0       # Build with specific tag
#   ./scripts/build-docker.sh v1.0.0 push  # Build and push to registry

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
IMAGE_NAME="ghcr.io/ferdousbhai/autonomous-claude"
TAG="${1:-latest}"
ACTION="${2:-build}"

echo "========================================"
echo "Building autonomous-claude sandbox image"
echo "========================================"
echo "Image: ${IMAGE_NAME}:${TAG}"
echo "Action: ${ACTION}"
echo ""

cd "$PROJECT_DIR"

# Build the image
echo "Building Docker image..."
docker build \
    -t "${IMAGE_NAME}:${TAG}" \
    -f Dockerfile \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    .

echo ""
echo "Successfully built ${IMAGE_NAME}:${TAG}"

# Tag as latest if building a version tag
if [[ "$TAG" =~ ^v[0-9] ]]; then
    echo "Also tagging as latest..."
    docker tag "${IMAGE_NAME}:${TAG}" "${IMAGE_NAME}:latest"
fi

# Push if requested
if [ "$ACTION" = "push" ]; then
    echo ""
    echo "Pushing to registry..."
    docker push "${IMAGE_NAME}:${TAG}"

    if [[ "$TAG" =~ ^v[0-9] ]]; then
        docker push "${IMAGE_NAME}:latest"
    fi

    echo "Successfully pushed ${IMAGE_NAME}:${TAG}"
fi

echo ""
echo "Done!"
