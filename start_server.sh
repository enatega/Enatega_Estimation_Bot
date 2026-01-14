#!/bin/bash
# Start script for Estimation Bot API

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the server
echo "Starting Estimation Bot API..."
echo "Python: $(which python)"
echo "API will be available at: http://localhost:8000"
echo "Frontend will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
