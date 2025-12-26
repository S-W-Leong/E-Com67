#!/bin/bash
# Build Strands layer using Docker to match Lambda Python 3.10 environment

echo "🔨 Building Strands layer for Lambda Python 3.10 x86_64..."

# Create python directory if it doesn't exist
mkdir -p layers/strands/python

# Use Docker to build with Python 3.10 on Linux x86_64
docker run --rm \
  -v "$(pwd)/layers/strands:/workspace" \
  -w /workspace \
  --platform linux/amd64 \
  python:3.10-slim \
  bash -c "pip install -r requirements-minimal.txt -t python/ --no-cache-dir && \
           find python -name '*.pyc' -delete && \
           find python -name '__pycache__' -type d -exec rm -rf {} + || true"

echo "✅ Strands layer built successfully!"
echo "📦 Layer contents:"
ls -la layers/strands/python/ | head -20
