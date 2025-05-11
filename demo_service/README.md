# Demo Service README

## Description

The demo service acts as a lightweight frontend that connects to the main application's backend. It is designed for demonstration purposes, allowing users to quickly set up and explore core functionalities by interacting with the full backend service. This ensures the demo stays in sync with the latest backend features and data model.

## Setup and Running

To set up and run the demo service, you first need to have the main backend service running.

1.  **Set up and run the main backend service:**
    *   Follow the instructions in the main project's README to set up and run the backend service. Ensure it is accessible at a known URL (e.g., `http://localhost:8000`).

2.  **Navigate to the `demo_service` directory:**
```
bash
    cd demo_service
    
```
2.  **Build the Docker image:**
```
bash
    docker build -t demo-service .
    
```
3.  **Run the Docker container:**
```
bash
    docker run -p 8000:8000 demo-service
    
```
The demo service will be accessible at `http://localhost:8000`.

## Data Loading Plan and Roadmap

The demo service connects to the main backend service and utilizes the data stored and managed by the backend. Data loading, population, and management are handled by the main backend's mechanisms (e.g., database migrations, initial data scripts).

### Current State

*   The demo service displays the data currently available in the main backend.
*   The state of the data depends entirely on the main backend's configuration and loaded data.
