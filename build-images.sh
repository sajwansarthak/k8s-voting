#!/usr/bin/env bash
# Builds all three app images directly inside Minikube's Docker daemon,
# so no registry, no push, no AWS — Kubernetes can just use them locally.
set -euo pipefail

echo "Pointing Docker CLI at Minikube's internal daemon..."
eval "$(minikube docker-env)"

echo "Building vote..."
docker build -t voting-app-vote:latest ./vote

echo "Building worker..."
docker build -t voting-app-worker:latest ./worker

echo "Building result..."
docker build -t voting-app-result:latest ./result

echo "Done. Images built inside Minikube:"
docker images | grep voting-app
