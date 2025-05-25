#!/bin/bash

# Run script for the Dzinza Family Tree development environment using Docker Compose
# Run this script from the project root directory (dzinza-python/).
clear
echo "========================================================"
echo "clearing Docker system..."
docker builder prune -f && docker system prune -f
echo "Docker system cleaned."

echo "========================================================"
echo "Starting Dzinza Family Tree using Docker Compose..."


export OPENSEARCH_INITIAL_ADMIN_PASSWORD='@(*(HI@#*00uk9))'
# Check if .env file exists, warn if not (optional but good practice)
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found in the project root."
    echo "         Default environment variables will be used."
    echo "         Create a .env file with your FLASK_SECRET_KEY and other settings."
    # Optionally exit here if .env is strictly required
    # exit 1
fi

# Ensure Docker and Docker Compose are installed (basic check)
if ! command -v docker &> /dev/null
then
    echo "ERROR: Docker could not be found. Please install Docker."
    exit 1
fi
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null
then
    echo "ERROR: Docker Compose could not be found. Please install Docker Compose (v1 or v2)."
    exit 1
fi

# Use docker compose (v2) or docker-compose (v1)
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
  DOCKER_COMPOSE_CMD="docker-compose"
fi

# Function to handle cleanup on exit
cleanup() {
    echo "Shutting down Docker Compose services..."
    # Use the detected command
    # $DOCKER_COMPOSE_CMD down -v --remove-orphans # Stop and remove containers, networks, volumes
    $DOCKER_COMPOSE_CMD down --remove-orphans # Stop and remove containers, networks, volumes
    echo "Shutdown complete."
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM to call cleanup
trap cleanup SIGINT SIGTERM

# Build and run the services in detached mode (-d) or foreground
# Use --build to ensure images are rebuilt if Dockerfiles change
echo "Building and starting services..."
# $DOCKER_COMPOSE_CMD up --build -d # Run detached
$DOCKER_COMPOSE_CMD up --build # Run in foreground to see logs

# If running detached, uncomment the following to follow logs:
# echo "Services started in detached mode. Following logs (Ctrl+C to stop logs)..."
# $DOCKER_COMPOSE_CMD logs -f

# If running in foreground, the script will wait here until Ctrl+C is pressed,
# which will trigger the cleanup function.

# Fallback cleanup in case the script exits unexpectedly after starting
cleanup

