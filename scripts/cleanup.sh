#!/bin/bash
CLUSTER_NAME="kubediag-test"

echo "Deleting kind cluster '$CLUSTER_NAME'..."
kind delete cluster --name $CLUSTER_NAME
echo "Cleanup complete."
