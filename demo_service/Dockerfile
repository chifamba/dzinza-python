# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the demo service script into the container
COPY demo_service.py /app/demo_service.py

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir requests Flask

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run demo_service.py when the container launches
CMD ["python", "demo_service.py"]
