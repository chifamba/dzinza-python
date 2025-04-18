#!/bin/bash

# Run script for the Dzinza Family Tree development environment
# Starts both the backend Flask API and the frontend Vite dev server concurrently.
# Run this script from the project root directory.

echo "Starting development servers..."

# --- Cleanup Function ---
cleanup() {
    echo "Shutting down servers..."
    # Kill backend process
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
    fi
    # Kill frontend process
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
    fi
    # Kill this script itself if needed, or just exit
    echo "Shutdown complete."
    exit 0
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT SIGTERM

# --- Start Backend ---
echo "Starting backend server (Flask API on port 8090)..."
cd backend || { echo "ERROR: 'backend' directory not found."; exit 1; }

# Activate virtual environment (important!)
source venv/bin/activate || { echo "ERROR: Failed to activate backend virtual environment. Please activate manually: source backend/venv/bin/activate"; exit 1; }

# Set Flask environment variables (can be set in .flaskenv too)
export FLASK_APP=app.py
export FLASK_DEBUG=1 # Enable debug mode for development

# Run Flask in the background
flask run --port=8090 &
BACKEND_PID=$! # Get the process ID of the background job
echo "Backend server started with PID: $BACKEND_PID"

cd .. # Go back to project root

# --- Start Frontend ---
echo "Starting frontend server (Vite)..."
cd frontend || { echo "ERROR: 'frontend' directory not found."; exit 1; }

# Run the Vite dev server (defined in package.json) in the background
npm run dev &
FRONTEND_PID=$! # Get the process ID
echo "Frontend server started with PID: $FRONTEND_PID"

cd .. # Go back to project root

echo "--------------------------------------------------"
echo "Backend API running at http://127.0.0.1:8090"
echo "Frontend running at http://localhost:8080 (or as indicated above)"
echo "Press Ctrl+C to stop both servers."
echo "--------------------------------------------------"

# Wait for background processes to finish (or be interrupted by trap)
wait $BACKEND_PID
wait $FRONTEND_PID

# Fallback cleanup in case wait returns unexpectedly
cleanup
