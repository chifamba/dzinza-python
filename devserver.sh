sh
#!/bin/bash

# Check if setup has been run. If not run setup
if [ ! -d "backend/.venv" ]; then
    ./setup_dev.sh
fi

# Use relative path for virtual environment activation
BACKEND_VENV="./backend/.venv/bin/activate"

# Function to start backend server
start_backend() {
    cd backend
    source "$BACKEND_VENV"
    export FLASK_APP=app.py
    export FLASK_DEBUG=1
    flask run --port=8090
    cd ..
}

# Function to start frontend server
start_frontend() {
    cd frontend
    npm run dev -- --port=5173
    cd ..
}

# Start backend
start_backend &
start_frontend &