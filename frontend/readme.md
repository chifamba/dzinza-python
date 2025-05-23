# Family Tree Frontend

## Project Overview

This is the frontend repository for a web application designed for building, visualizing, and managing family trees. The application focuses on providing a collaborative platform for users to document their family history while ensuring data privacy and security.

## Features

*   **User Authentication:** Secure login and registration.
*   **Family Tree Management:** Create, view, and manage multiple family trees.
*   **Person Management:** Add, edit, and view details about individuals in a tree, including biographical information, dates, places, and custom fields.
*   **Relationship Management:** Define and manage various types of relationships between individuals.
*   **Event Tracking:** Record significant life events for individuals (e.g., birth, death, marriage).
*   **Media Attachments:** Upload and link photos, documents, and other media to individuals and events.
*   **Privacy Settings:** Control the visibility of trees and individual data.
*   **User Collaboration:** Share trees with other users and manage their access levels.
*   **Search and Filtering:** Easily find individuals within a tree.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Node.js (LTS version recommended)
*   npm or yarn
*   A running instance of the Family Tree Backend. Refer to the backend's documentation for setup instructions. Ensure the backend is configured to accept connections from your frontend's origin (check the `CORS_ORIGINS` setting in the backend's `config.py`).

### Installation

1.  Clone the repository:
```
bash
    git clone <repository_url>
    cd family-tree-frontend
    
```
2.  Install dependencies using npm or yarn:
```
bash
    npm install
    # or
    yarn install
    
```
### Configuration

1.  Create a `.env` file in the root of the frontend directory.
2.  Add the following environment variable, replacing the value with the URL of your running backend instance:
```
env
    VITE_BACKEND_API_URL=http://localhost:8090/api
    
```
*   Make sure the URL points to the base path of the backend API (e.g., `http://localhost:8090/api`). The `/api` prefix is defined in the backend blueprints.
    *   If your backend is running on a different host or port, update the URL accordingly.

### Running the Application

To run the frontend in development mode:
```
bash
npm run dev
# or
yarn dev
```
This will start the development server, usually on `http://localhost:5173`. The application will automatically reload as you make changes to the code.

## API Overview

The frontend communicates with a backend API built with Flask, SQLAlchemy, and PostgreSQL. The backend handles data storage, business logic, authentication, and authorization. It also integrates with Redis for session management and rate limiting, and utilizes S3 or MinIO for object storage of media files.

Key functionalities and corresponding (example) backend areas include:

*   **Authentication (`/auth` blueprint):**
    *   User registration (`POST /auth/register`)
    *   User login (`POST /auth/login`)
    *   User logout (`POST /auth/logout`)
    *   Get current user information (`GET /auth/me`)
    *   Password reset functionality.
*   **Family Trees (`/trees` blueprint):**
    *   Create a new tree (`POST /trees`)
    *   Get a list of user's trees (`GET /trees`)
    *   Get details of a specific tree (`GET /trees/<tree_id>`)
    *   Update a tree (`PUT /trees/<tree_id>`)
    *   Delete a tree (`DELETE /trees/<tree_id>`)
    *   Manage tree collaboration and access (`/trees/<tree_id>/access`).
*   **People (`/trees/<tree_id>/people` blueprint):**
    *   Add a person to a tree (`POST /trees/<tree_id>/people`)
    *   Get a list of people in a tree (`GET /trees/<tree_id>/people`)
    *   Get details of a specific person (`GET /trees/<tree_id>/people/<person_id>`)
    *   Update a person's details (`PUT /trees/<tree_id>/people/<person_id>`)
    *   Delete a person (`DELETE /trees/<tree_id>/people/<person_id>`)
    *   Upload profile pictures (`POST /trees/<tree_id>/people/<person_id>/profile_picture`).
*   **Relationships (`/trees/<tree_id>/relationships` blueprint):**
    *   Add a relationship between two people (`POST /trees/<tree_id>/relationships`)
    *   Get relationships for a person or tree (`GET /trees/<tree_id>/relationships` or via person endpoints).
    *   Update/Delete relationships.
*   **Events (`/trees/<tree_id>/events` blueprint):**
    *   Add an event to a person or tree (`POST /trees/<tree_id>/events`)
    *   Get events for a person or tree (`GET /trees/<tree_id>/events` or via person/tree endpoints).
    *   Update/Delete events.
*   **Media (`/trees/<tree_id>/media` blueprint):**
    *   Upload media items (`POST /trees/<tree_id>/media`)
    *   Get media items linked to an entity (person, event, tree) (`GET /trees/<tree_id>/<entity_type>/<entity_id>/media`).
*   **Admin (`/admin` blueprint):** (Requires admin role)
    *   Manage users, etc.

The API uses standard RESTful conventions and communicates using JSON. Authentication is typically handled via session cookies after a successful login. Certain sensitive data within the database (like names, places, notes) is encrypted using Fernet symmetric encryption.

## Technologies Used

### Frontend

*   HTML, CSS, JavaScript
*   React (or your chosen framework/library)
*   [Add specific libraries/frameworks used, e.g., React Router, Axios for API calls, state management library like Redux/Context API/Zustand, UI library like Material UI/Ant Design, etc.]

### Backend

*   Flask (Python Web Framework)
*   SQLAlchemy (ORM)
*   PostgreSQL (Database)
*   Redis (Session Management, Rate Limiting)
*   Bcrypt (Password Hashing)
*   Cryptography (Fernet Encryption)
*   Boto3 (S3/MinIO Object Storage)
*   OpenTelemetry (Observability)
*   Gunicorn (WSGI Server)
*   Docker