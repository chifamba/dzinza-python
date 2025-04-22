#!/bin/bash

# Run script for the Dzinza Family Tree development environment
# Starts both the backend Flask API and the frontend Vite dev server concurrently.
# Run this script from the project root directory.

# --- Cleanup Function ---
cleanup() {
    # Kill child process (devserver.sh)
    if [ ! -z "$CHILD_PID" ]; then
        # Kill the child process and all of its children
        kill -9 -$CHILD_PID &> /dev/null # Use process group ID to kill all children
    fi
    wait $CHILD_PID &> /dev/null # Wait for the child to exit
    echo "Shutdown complete."
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM to call cleanup
trap cleanup SIGINT SIGTERM

# --- Start devserver.sh ---
if [ ! -d "backend/.venv" ]; then
  ./setup_dev.sh
fi

./devserver.sh &
CHILD_PID=$! # Get the process ID of the background job

if [ $? -ne 0 ]; then
  cleanup
fi

# Wait for the devserver.sh child process to exit
wait $CHILD_PID

# Cleanup in case wait returns unexpectedly or the script is terminated
cleanup


