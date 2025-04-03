#!/bin/bash
# Start script for Produsum AI

# Kill any running instances of the app
pkill -f "python app.py" 2>/dev/null || echo "No running instances found"

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if .env file exists, if not copy from example
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env file to add your OpenAI API key"
fi

# Start the application
echo "Starting Produsum AI..."
python app.py 