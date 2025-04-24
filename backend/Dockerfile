# backend/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables for Flask and Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8090
# Set FLASK_DEBUG=0 for production builds, or pass via docker-compose for dev
# ENV FLASK_DEBUG=0

# Install system dependencies if needed (e.g., for libraries with C extensions)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the tests folder
# COPY tests /app/tests

# Copy all files
COPY backend .
RUN ls -l /app
# Make port 8090 available to the world outside this container
EXPOSE 8090

# Define the command to run the application using Flask's built-in server (for development)
# For production, consider using a production-ready WSGI server like Gunicorn or Waitress
# Example using Gunicorn:
# CMD ["gunicorn", "--bind", "0.0.0.0:8090", "app:app"]
RUN pytest /app/tests
RUN python backend/app/db_init.py
CMD ["flask", "run"]

