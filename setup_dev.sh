#!/bin/bash

# Setup script for the Dzinza Family Tree development environment
# Run this script from the project root directory.

echo "Starting setup for the Dzinza Family Tree development environment..."

# --- Prerequisites Check (Informational) ---
echo "INFO: Please ensure you have Python 3.11+ and Node.js (with npm) installed."
# Add commands to check versions if desired, e.g.,
echo "INFO: Checking Python version..."
python3 --version
echo "INFO: Checking Node.js and npm versions..."
node --version
npm --version

# --- Backend Setup ---
echo "--------------------------------------------------"
echo "INFO: Setting up backend (Python/Flask)..."
cd backend || { echo "ERROR: 'backend' directory not found."; exit 1; }

# Check if virtual environment exists, create if not
if [ ! -d ".venv" ]; then
    echo "INFO: Creating Python virtual environment..."
    python3 -m venv .venv || { echo "ERROR: Failed to create virtual environment."; exit 1; }
else
    echo "INFO: Python virtual environment '.venv' already exists."
fi

# Activate the virtual environment and install dependencies
echo "INFO: Installing Python dependencies..."
source .venv/bin/activate || { echo "ERROR: Failed to activate virtual environment."; exit 1; }
pip install --upgrade pip || { echo "ERROR: Failed to upgrade pip"; exit 1; }
pip install -r requirements.txt || { echo "ERROR: Failed to install Python dependencies."; deactivate; exit 1; }
deactivate

echo "INFO: Backend setup complete. To activate the virtual environment:"
echo "source backend/.venv/bin/activate"
cd .. # Go back to project root

# --- Frontend Setup ---
echo "--------------------------------------------------"
echo "INFO: Setting up frontend (React/Vite)..."
cd frontend || { echo "ERROR: 'frontend' directory not found."; exit 1; }

echo "INFO: Installing Node.js dependencies..."
npm install || { echo "ERROR: Failed to install Node.js dependencies."; exit 1; }

echo "INFO: Frontend setup complete."
cd .. # Go back to project root

echo "--------------------------------------------------"
echo "INFO: Development environment setup has been completed successfully!"
echo ""
echo "Next Steps:"
echo "  1. Start the application by running: ./run_dev.sh"
echo ""
echo "--------------------------------------------------"

exit 0
