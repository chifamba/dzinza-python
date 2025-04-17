# Family Tree API

Family Tree API is a web application for building and managing family trees, featuring a **Python Flask backend API**. It allows users to register, log in, add individuals, define relationships, and explore the family structure visually.

**Note:** This project is undergoing a refactoring to separate the backend and frontend codebases and replace the original server-rendered frontend with a modern React-based interface.

## Features

*   User registration and login (Admin/User roles)
*   **Backend:** Flask API for managing data (Python).
*   **Frontend:** React single-page application.
*   **Data Management:** Add, edit, and view people and relationships via API.
*   **Interactive Visualization (React Flow):**
    *   Hierarchical display of the family tree.
    *   Zooming and panning capabilities.
    *   Node selection to view details.
    *   (Planned) Custom nodes displaying more person details (dates, photos).
    *   (Planned) Styling nodes/edges based on properties (gender, relationship type).
    *   (Planned) Inline editing directly on the graph.
*   Search functionality for people (via API).
*   Admin panel for user management (via API).
*   Password reset functionality (via API).
*   Audit logging for key backend actions.

## Project Structure
```
family-tree-api/
├── backend/              # Contains all Python/Flask code
│   ├── src/              # Core logic modules (person, family_tree, etc.)
│   ├── tests/            # Backend unit and integration tests
│   ├── data/             # Data files (users.json, family_tree.json)
│   ├── app.py            # Flask app entry point
│   └── requirements.txt  # Backend dependencies
├── frontend/             # React frontend code
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── ... (other React project files)
├── logs/                 # Log files
│   ├── backend/          # Backend logs (app.log, audit.log)
│   └── frontend/         # Frontend logs (if any)
├── .gitignore
├── README.md             # This file
└── todo.md               # Project TODO list (reflecting refactor plan)
```
## Prerequisites

*   **Python:** 3.11+
*   **Pip:** Python package installer
*   **Node.js:** 23.x or later (for the React frontend)
*   **npm** or **yarn:** Node package manager (comes with Node.js)

## Setup and Installation

1.  **Clone the repository:**
```
bash
    git clone <repository-url>
    cd family-tree-api
    
```
2.  **Backend Setup (Python/Flask API):**
    *   Navigate to the backend directory:
```
bash
        cd backend
        
```
*   Create and activate a virtual environment (recommended):
```
bash
        python -m venv venv
        source venv/bin/activate  # On Windows use `venv\Scripts\activate`
        
```
*   Install backend dependencies:
```
bash
        pip install -r requirements.txt
        
```
* Navigate back to the project root:
```
bash
        cd ..
        
```
3.  **Frontend Setup (React):**
    *   Navigate to the frontend directory:
```
bash
        cd frontend
        
```
*   Install frontend dependencies:
```
bash
        npm install
        # or if using yarn:
        # yarn install
        
```
* Navigate back to the project root:
```
bash
        cd ..
        
```
## Running the Application (Development)

You need to run both the backend API server and the frontend development server concurrently.

1.  **Run the Backend (Flask API):**
    *   Open a terminal in the project root (`family-tree-api`).
    *   Navigate to the backend directory:
```
bash
        cd backend
        
```
*   Make sure your Python virtual environment is activated:
```
bash
        source venv/bin/activate # Or venv\Scripts\activate on Windows
        
```
*   Run the Flask development server:
```
bash
        # Set environment variables (Bash/Zsh)
        export FLASK_APP=app.py
        export FLASK_DEBUG=1

        # Set environment variables (Windows CMD)
        # set FLASK_APP=app.py
        # set FLASK_DEBUG=1

        # Set environment variables (Windows PowerShell)
        # $env:FLASK_APP = "app.py"
        # $env:FLASK_DEBUG = "1"

        # Run Flask on the specified port
        flask run --port=8090
        
```
*   The backend API will typically be running on `http://127.0.0.1:8090`. Logs will appear in `logs/backend/`.

2.  **Run the Frontend (React Dev Server):**
    *   Open a *second* terminal in the project root (`family-tree-api`).
    *   Navigate to the frontend directory:
```
bash
        cd frontend
        
```
*   Start the React development server:
```
bash
        npm start
        # or if using yarn:
        # yarn start
        
```
*   The React application will typically open automatically in your browser at `http://localhost:8080`.

3.  **Access the Application:** Open your web browser and navigate to `http://localhost:8080` (or the port specified by the React development server).

## Usage (React Frontend)

1.  **Register/Login:** Use the forms in the React application to register a new user or log in.
2.  **View Tree:** The main dashboard should display the interactive family tree visualization.
3.  **Interact with Tree:** Use zoom/pan controls. Click on nodes (people) to view details (implementation pending based on plan).
4.  **Add/Edit Data:** Use forms within the React application (potentially modals triggered from the visualization or separate views) to add/edit people and relationships. These forms will interact with the backend API.
5.  **Search:** Use the search interface within the React app.
6.  **Admin Panel:** If logged in as an ADMIN user, navigate to the user management section within the React app (route needs to be defined).
7.  **Logout:** Use the "Logout" button/link in the React app.

## Running Tests

1.  **Backend Tests (Python):**
    *   Navigate to the `backend` directory:
```
bash
        cd backend
        
```
*   Ensure the Python virtual environment is activated.
    *   Run all tests:
```
bash
        python -m unittest discover tests
        
```
*   Run a specific test file:
```
bash
        python -m unittest tests.test_person # Adjust path relative to backend dir
        
```
2.  **Frontend Tests (React):**
    *   Navigate to the `frontend` directory.
    *   Run tests using the command specified by your React setup (e.g., Create React App):
```
bash
        npm test
        # or
        # yarn test
        
```
*   (Planned) End-to-end tests using Cypress or Playwright will have their own run commands.

## Contributing

Please refer to the `todo.md` file for the detailed refactoring plan and planned features. Contributions are welcome!

## License

MIT License