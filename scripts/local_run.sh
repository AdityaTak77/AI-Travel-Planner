#!/bin/bash
# Local run script for AI Travel Planner
# This script sets up a virtual environment and runs the application

set -e

echo "AI Travel Planner - Local Setup"
echo "================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "Warning: .env file not found!"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "Please edit .env with your actual API keys before running."
    echo ""
fi

# Run the application
echo ""
echo "Starting AI Travel Planner..."
echo "================================"
echo ""

if [ $# -eq 0 ]; then
    # No arguments - run with sample request
    python -m src.main examples/sample_itinerary_request.json
else
    # Run with provided arguments
    python -m src.main "$@"
fi

echo ""
echo "================================"
echo "Execution complete!"
