# Demo Service README

## Description

The demo service provides a simplified, self-contained version of the main application's backend. It is designed for demonstration purposes, allowing users to quickly set up and explore core functionalities without requiring a full database or complex dependencies. It uses flat files for data storage.

## Setup and Running

To set up and run the demo service, follow these steps:

1.  **Navigate to the `demo_service` directory:**
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

The demo service uses flat files (`.tinydb` and `.json`) located in the `demo_service/backend/data` directory for data storage.

### Current State

*   Initial data is loaded from the included flat files upon service startup.
*   Basic user and family tree data is available.

### Roadmap

*   **Phase 1: Basic Data Population (Completed)**
    *   Implement loading of initial user data.
    *   Implement loading of initial family tree data (persons and relationships).
*   **Phase 2: Expanded Data Set (Planned)**
    *   Create a more comprehensive sample data set covering various family structures and scenarios.
    *   Include examples of different attributes and media.
*   **Phase 3: Data Generation Script (Planned)**
    *   Develop a script to programmatically generate larger and more diverse demo data sets.
    *   Allow for customization of data generation parameters.
*   **Phase 4: Optional Data Reset Endpoint (Future)**
    *   Consider adding an API endpoint to reset the demo data back to its initial state without restarting the service.

The flat file approach is suitable for the demo's simplicity. For persistent data or larger scale, the main application's database-backed backend should be used.