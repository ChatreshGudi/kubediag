#!/bin/bash
set -e

echo "Running KubeDiag scan..."
source .venv/bin/activate
kubediag scan
