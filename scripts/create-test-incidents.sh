#!/bin/bash
set -e

echo "Applying test incidents..."
kubectl apply -f k8s/

echo "Waiting for resources to be created (some will fail intentionally)..."
sleep 15
echo "Test incidents deployed!"
