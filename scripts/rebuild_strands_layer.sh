#!/bin/bash

# Script to rebuild the Strands layer with all required dependencies

echo "Rebuilding Strands layer with missing dependencies..."

# Navigate to the Strands layer directory from the project root
cd layers/strands

# Ensure python directory exists
mkdir -p python

# Install dependencies using Docker to match Lambda runtime
echo "Installing dependencies using Docker (Python 3.10 runtime)..."

# Create a temporary Dockerfile for building the layer
cat > Dockerfile.temp << 'EOF'
FROM public.ecr.aws/lambda/python:3.10

# Copy requirements file
COPY python/requirements.txt /tmp/requirements.txt

# Install dependencies
RUN pip install -r /tmp/requirements.txt -t /tmp/python/

# Copy installed packages
CMD ["cp", "-r", "/tmp/python/", "/output/"]
EOF

# Build and run the Docker container to install dependencies
docker build -f Dockerfile.temp -t strands-layer-builder .
docker run --rm -v "$(pwd)/python:/output" strands-layer-builder cp -r /tmp/python/ /output/

# Clean up
rm -f Dockerfile.temp

echo "Strands layer rebuilt successfully!"
echo "Contents of python directory:"
ls -la python/ | head -20

echo ""
echo "Now redeploy your stack with: cdk deploy"