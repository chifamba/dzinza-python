# backend/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.13-slim 
# Set the working directory in the container
WORKDIR /app

# Set environment variables for Flask and Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
# FLASK_APP points to the 'app' instance in /app/main.py (created by create_app())
ENV FLASK_APP=main:app
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8090
# For production images, FLASK_DEBUG should be 0.
# This can be overridden at runtime (e.g., via docker-compose) for development.
ENV FLASK_DEBUG=0
# Optional: Set Gunicorn workers, can also be overridden

# Install PostgreSQL development libraries first
# RUN apt-get update && apt-get install -y postgresql-client libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first to leverage Docker's layer caching.
# This assumes requirements.txt is in the same directory as the Dockerfile (the build context).
COPY backend/ /app/

# Install Python dependencies
# Using --no-cache-dir reduces image size.
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the application code from the build context (the local ./backend directory)
# to the /app directory in the container.
# This includes main.py, config.py, and subdirectories like blueprints/, services/, data/, etc.


# Make port 8090 available to the world outside this container
EXPOSE 8090

# Define the command to run the application using Gunicorn for production.
# 'main:app' refers to the 'app' Flask instance in '/app/main.py'.
# Gunicorn will look for this in the WORKDIR.
# The number of workers can be tuned based on your server's resources.
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8090", "main:app"]

# To run in development mode (e.g., by overriding CMD in docker-compose.yml):
# CMD ["flask", "run"]
# For this to work, ensure FLASK_DEBUG is set to 1 in the development environment.
