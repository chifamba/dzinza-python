#!/bin/sh

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
  echo "Activating virtual environment..."
  source .venv/bin/activate
else
  echo "Warning: .venv directory not found. Running without virtual environment."
fi

# Check if required packages are installed
pip freeze | grep -q Flask || pip install Flask
pip freeze | grep -q tinydb || pip install tinydb

# Run the Flask application using python -m flask run
# The PORT environment variable is often used by hosting platforms
# Defaulting to 5000 if PORT is not set
FLASK_APP=app.py # Explicitly set the app file
FLASK_DEBUG=1    # Enable debug mode for development (auto-reload, error pages)
echo "Starting Flask development server..."
python3 -m flask run --host=0.0.0.0 --port=${PORT:-8080}

# Deactivate virtual environment on exit (optional)
# deactivate
