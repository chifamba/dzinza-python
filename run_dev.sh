#!/bin/bash

# Run script for the Dzinza Family Tree development environment
# Starts both the backend Flask API and the frontend Vite dev server concurrently.
# Run this script from the project root directory.

# Define ports (adjust if needed, Vite default is often 5173)
BACKEND_PORT=8090
FRONTEND_PORT=5173 # Default Vite port

echo "Starting development servers..."

# --- Cleanup Function ---
cleanup() {
    echo "Shutting down servers..."
    # Kill backend process
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID &> /dev/null # Suppress "Terminated" message
    fi
    # Kill frontend process
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID &> /dev/null # Suppress "Terminated" message
    fi
    wait $BACKEND_PID $FRONTEND_PID &> /dev/null # Wait briefly for processes to exit
    echo "Shutdown complete."
    exit 0
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT SIGTERM

# --- Start Backend ---
echo "Starting backend server (Flask API on port $BACKEND_PORT)..."
cd backend || { echo "ERROR: 'backend' directory not found."; exit 1; }

# Activate virtual environment (important!)
source venv/bin/activate || { echo "ERROR: Failed to activate backend virtual environment. Please activate manually: source backend/venv/bin/activate"; exit 1; }

# Set Flask environment variables (can be set in .flaskenv too)
export FLASK_APP=app.py
export FLASK_DEBUG=1 # Enable debug mode for development

# Run Flask in the background on the specified port
flask run --port=$BACKEND_PORT &
BACKEND_PID=$! # Get the process ID of the background job
echo "Backend server started with PID: $BACKEND_PID"

cd .. # Go back to project root

# --- Start Frontend ---
echo "Starting frontend server (Vite on port $FRONTEND_PORT)..."
cd frontend || { echo "ERROR: 'frontend' directory not found."; exit 1; }

# Run the Vite dev server (defined in package.json) in the background
# Explicitly set the port Vite should use
npm run dev -- --port $FRONTEND_PORT &
FRONTEND_PID=$! # Get the process ID
echo "Frontend server started with PID: $FRONTEND_PID"

cd .. # Go back to project root

# --- Display Info ---
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
GREEN='\033[1;32m'
NC='\033[0m' # No Color

echo -e "${YELLOW}======================================================================================${NC}"
echo -e "|                                                                                    |"
echo -e "|   ${CYAN}Backend API running at http://127.0.0.1:$BACKEND_PORT${NC}                                    |"
echo -e "|   ${CYAN}Frontend running at http://localhost:$FRONTEND_PORT${NC}                                      |"
echo -e "|                                                                                    |"
echo -e "|   ${GREEN}Press Ctrl+C to stop both servers.${NC}                                               |"
echo -e "|                                                                                    |"
echo -e "${YELLOW}======================================================================================${NC}"


# Wait for background processes to finish (or be interrupted by trap)
# Use wait -n to wait for any job to finish (useful if one crashes)
# Fallback to waiting for specific PIDs if wait -n isn't available/reliable
wait $BACKEND_PID $FRONTEND_PID

# Fallback cleanup in case wait returns unexpectedly
cleanup
