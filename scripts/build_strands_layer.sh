#!/bin/bash
# Build Strands layer for Lambda Python 3.10 x86_64 using Docker
# This ensures Linux x86_64 binaries are built correctly

echo "🔨 Building Strands layer for Lambda Python 3.10 x86_64 using Docker..."

# Clean up existing build
echo "🧹 Cleaning up existing build..."
rm -rf layers/strands/python
mkdir -p layers/strands/python

# Build using Docker with Python 3.10 on Linux x86_64
echo "🐳 Building with Docker (Python 3.10 on Linux x86_64)..."
docker run --rm \
  --platform linux/amd64 \
  -v "$(pwd)/layers/strands:/var/task" \
  -w /var/task \
  python:3.10-slim \
  pip install -r requirements.txt -t python/ --upgrade --no-cache-dir

# Clean up Python cache files
echo "🧹 Cleaning up cache files..."
find layers/strands/python -name '*.pyc' -delete
find layers/strands/python -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find layers/strands/python -name '*.dist-info/RECORD' -type f -delete 2>/dev/null || true

echo "✅ Strands layer built successfully with Linux x86_64 binaries!"
echo "📦 Layer size:"
du -sh layers/strands/python/
echo ""
echo "📋 Verifying Strands SDK installation:"
ls -la layers/strands/python/ | grep strands
