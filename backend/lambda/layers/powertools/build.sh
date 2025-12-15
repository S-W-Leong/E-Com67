#!/bin/bash
# Build script for Lambda Powertools layer
# This installs dependencies into the correct directory structure for Lambda layers

set -e

echo "Building Lambda Powertools layer..."

# Clean existing build
rm -rf python/

# Install dependencies
pip install -r requirements.txt -t python/ --upgrade

echo "Layer built successfully!"
echo "Contents:"
ls -la python/
