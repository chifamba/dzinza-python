import os
import requests
import json

def create_demo_data():
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000") # Default to localhost

    try:
        # Example of making an API call to the main backend
        # You will need to adapt this to the actual API endpoints of your backend
        # This is a placeholder to show the concept of making API calls

        # Example: Create a demo user
        user_data = {
            "username": "demo_user",
            "email": "demo_user@example.com",
            "password": "password123"
        }
        response = requests.post(f"{backend_url}/users/", json=user_data)
        response.raise_for_status() # Raise an exception for bad status codes
        print(f"Demo user created: {response.json()}")

        # You would continue to make API calls to create other demo data (trees, people, relationships, etc.)
        # based on your backend's API endpoints.

    except Exception as e:
        print(f"Error creating demo data: {e}")

if __name__ == "__main__":
    if os.getenv("ENABLE_DEMO_MODE", "true").lower() == "true":
        create_demo_data()
