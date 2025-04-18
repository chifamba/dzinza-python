sh
#!/bin/bash

# Set environment variables
export BACKEND_PORT=8090
export FRONTEND_PORT=5173

# Start backend
cd backend 
source .venv/bin/activate
export FLASK_APP=app.py
export FLASK_DEBUG=1
flask run --port=$BACKEND_PORT &


# Start frontend
cd ..
cd frontend
npm run dev -- --port=$FRONTEND_PORT &

# Print server URLs
echo "Backend server is running at http://127.0.0.1:$BACKEND_PORT"
echo "Frontend is running at http://localhost:$FRONTEND_PORT"

# Return to root
cd ..

# Sleep for a long time
sleep 10000