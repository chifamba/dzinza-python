#!/bin/bash

# Setup script for the Dzinza Family Tree development environment
# Run this script from the project root directory.

echo "Starting development environment setup..."

# --- Prerequisites Check (Informational) ---
echo "INFO: Please ensure you have Python 3.11+ and Node.js 23+ installed."
# Add commands to check versions if desired, e.g.,
# python --version
# node --version
# npm --version

# --- Backend Setup ---
echo "Setting up backend (Python/Flask)..."
cd backend || { echo "ERROR: 'backend' directory not found."; exit 1; }

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv || { echo "ERROR: Failed to create virtual environment."; exit 1; }
else
    echo "Python virtual environment 'venv' already exists."
fi

# Activate virtual environment (Note: Activation is temporary for this script's execution)
# The user needs to activate it manually for running commands directly.
echo "Installing Python dependencies (requires virtual environment to be activated manually later)..."
# Attempt to install within the venv context if possible, otherwise install globally if venv activation fails/is complex in script
source venv/bin/activate # Try activating (might not work depending on shell)
pip install -r requirements.txt || { echo "ERROR: Failed to install Python dependencies."; exit 1; }
# Deactivate after install (if activation worked)
deactivate &> /dev/null

echo "Backend setup complete. Activate with: source backend/venv/bin/activate"
cd .. # Go back to project root

# --- Frontend Setup ---
echo "Setting up frontend (React/Vite)..."
cd frontend || { echo "ERROR: 'frontend' directory not found."; exit 1; }

echo "Installing Node.js dependencies..."
npm install || { echo "ERROR: Failed to install Node.js dependencies."; exit 1; }

echo "Frontend setup complete."
cd .. # Go back to project root

echo "--------------------------------------------------"
echo "Setup finished successfully!"
echo "To run the application:"
echo "1. Activate the backend virtual environment: source backend/venv/bin/activate"
echo "2. Run the development server script: ./run_dev.sh"
echo "--------------------------------------------------"

exit 0
