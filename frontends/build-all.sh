#!/bin/bash

# Build script for all E-Com67 frontend applications
# This script builds the shared library and both frontend applications

set -e  # Exit on any error

echo "🚀 Building E-Com67 Frontend Applications"
echo "========================================"

# Build shared components library
echo "📦 Building shared components library..."
cd shared
npm install
npm run build
echo "✅ Shared library built successfully"
cd ..

# Build admin dashboard
echo "🔧 Building admin dashboard..."
cd admin-dashboard
npm install
npm run build
echo "✅ Admin dashboard built successfully"
cd ..

# Build customer application
echo "🛍️  Building customer application..."
cd customer-app
npm install
npm run build
echo "✅ Customer application built successfully"
cd ..

echo ""
echo "🎉 All applications built successfully!"
echo ""
echo "Build outputs:"
echo "- Shared library: frontends/shared/dist/"
echo "- Admin dashboard: frontends/admin-dashboard/dist/"
echo "- Customer app: frontends/customer-app/dist/"
echo ""
echo "Ready for deployment! 🚀"