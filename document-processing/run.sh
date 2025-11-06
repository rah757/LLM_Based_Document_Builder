#!/bin/bash

# Document Placeholder Processor - Quick Start Script

echo "🚀 Starting Document Placeholder Processor MVP..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check if uploads folder exists
if [ ! -d "uploads" ]; then
    echo "📁 Creating uploads folder..."
    mkdir uploads
fi

# Navigate to src and run the app
echo "🌐 Starting Flask server..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Application is starting!"
echo "📍 Open your browser and navigate to: http://localhost:5051"
echo "🛑 Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd src
python app.py

