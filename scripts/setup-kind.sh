#!/bin/bash
set -e

CLUSTER_NAME="kubediag-test"

echo "Creating kind cluster '$CLUSTER_NAME'..."
kind create cluster --name $CLUSTER_NAME

echo "Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=60s

echo "Cluster '$CLUSTER_NAME' is ready!"
