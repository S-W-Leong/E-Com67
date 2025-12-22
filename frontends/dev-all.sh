#!/bin/bash

# Development script for E-Com67 frontend applications
# This script starts all applications in development mode

echo "🚀 Starting E-Com67 Frontend Development Servers"
echo "================================================"
echo ""
echo "Starting applications:"
echo "- Admin Dashboard: http://localhost:3000"
echo "- Customer App: http://localhost:3001"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all development servers..."
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start shared library in watch mode
echo "📦 Starting shared library in watch mode..."
cd shared && npm run dev &
cd ..

# Start admin dashboard
echo "🔧 Starting admin dashboard..."
cd admin-dashboard && npm run dev &
cd ..

# Start customer application
echo "🛍️  Starting customer application..."
cd customer-app && npm run dev &
cd ..

# Wait for all background processes
wait