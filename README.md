# Dzinza Family Tree Application

Dzinza Family Tree is a web application for building and managing family trees, featuring a **Python Flask backend API** and a **React frontend**. It allows users to register, log in, add individuals, define relationships, and explore the family structure visually using React Flow. The backend uses a flask API to manage the family tree data. The frontend is a react application which provides a clean interface to manage the family tree.

## Features
* **Backend:** Flask API for managing data (Python).
* User registration and login (Admin/User roles) via API.
* **Backend:** Flask API for managing data (Python).
* **Frontend:** React single-page application (Vite).
* **Data Management:** Add, edit, and view people and relationships via API.
* **Interactive Visualization (React Flow):**
    * Hierarchical display of the family tree.
    * Zooming and panning capabilities.
    * View details for the selected node.
    * Custom nodes displaying more person details (dates, photos).
    * Styling nodes/edges based on properties (gender, relationship type).
    * Editing of people and relationships.
* Search functionality for people (via API).
* Admin panel for user management (via API).
* Audit logging for key backend actions.
* Consistent Json responses for errors.
* Input validation for the API endpoints.
* API Authentication (Session-based) and CORS support.
* API Input Validation.

## Project Structure
dzinza-python/├── backend/              # Contains all Python/Flask code│   ├── src/              # Core logic modules (person, family_tree, etc.)│   ├── tests/            # Backend unit and integration tests│   ├── data/             # Data files (users.json, family_tree.json)│   ├── venv/             # Python virtual environment (created by setup script)│   ├── app.py            # Flask app entry point│   └── requirements.txt  # Backend dependencies├── frontend/             # React frontend code│   ├── public/│   ├── src/│   ├── node_modules/     # Node dependencies (created by setup script)│   ├── package.json│   └── ... (other React project files)├── logs/                 # Log files│   ├── backend/          # Backend logs (app.log, audit.log)│   └── frontend/         # Frontend logs (if any)├── .gitignore├── README.md             # This file├── setup_dev.sh          # Development environment setup script├── run_dev.sh            # Development server run script└── todo.md               # Project TODO list## Prerequisites

* **Python:** 3.11+ (Verify with `python3 --version`)
* **Pip:** Python package installer (usually comes with Python)
* **Node.js:** 23.x or later (Verify with `node --version`)
* **npm:** Node package manager (comes with Node.js, verify with `npm --version`)
* **Git:** For cloning the repository.
* **Bash-compatible shell:** For running the setup and run scripts (e.g., Git Bash on Windows, Terminal on macOS/Linux).

## Current state of the Application
The application currently allows users to:
*   Register and Login to the application.
*   Add, edit and delete people.
*   Add, edit and delete relationships between people.
* View the family tree structure in the frontend.
* The API provides endpoints for all the functionality above and more.
* Admin user management is available via the API.
* Audit logs are kept for important actions.


## Setup and Installation (Using Scripts)

These scripts automate the setup process. Run them from the **project root directory** (`dzinza-python/`).

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd dzinza-python
    ```

2.  **Make scripts executable:**
    ```bash
    chmod +x setup_dev.sh
    chmod +x run_dev.sh
    ```

3.  **Run the setup script:**
    ```bash
    ./setup_dev.sh
    ```
    This script will:
    * Check for the `backend` and `frontend` directories.
    * Create a Python virtual environment (`venv`) inside the `backend` directory if it doesn't exist.
    * Install Python dependencies from `backend/requirements.txt` into the virtual environment.
    * Install Node.js dependencies from `frontend/package.json` using `npm install`.

## Running the Application (Development - Using Script)

1.  **Ensure Setup is Complete:** Make sure you have run `./setup_dev.sh` successfully at least once.

2.  **Run the Development Server Script:**
    * Open a terminal in the project root directory (`dzinza-python/`).
    * Execute the run script:
        ```bash
        ./run_dev.sh
        ```
    * This script will:
        * Activate the backend Python virtual environment.
        * Start the Flask backend API server (typically on `http://127.0.0.1:8090`).
        * Start the React frontend development server (typically on `http://localhost:8080`).
        * Run both servers concurrently.

3.  **Access the Application:**
    * Open your web browser and navigate to the frontend URL provided in the terminal (usually `http://localhost:8080`).
    * The React app will communicate with the backend API running on port 8090.

4.  **Stopping the Servers:**
    * Go back to the terminal where `./run_dev.sh` is running.
    * Press `Ctrl+C`. The script will attempt to gracefully shut down both the backend and frontend servers.

## Usage (React Frontend)

1.  **Register/Login:** Use the forms in the React application to register a new user or log in via the API.
2.  **View Tree:** The main dashboard should display the interactive family tree visualization.
3.  **Interact with Tree:** Use zoom/pan controls. Click on nodes (people) to view details.
4.  **Add/Edit Data:** Use forms within the React application (potentially modals triggered from the visualization or separate views) to add/edit people and relationships via API calls.
5.  **Search:** Use the search interface within the React app (if implemented).
6.  **Admin Panel:** If logged in as an ADMIN user, access admin features within the React app (if implemented).
7.  **Logout:** Use the "Logout" button/link in the React app, which should call the `/api/logout` endpoint.

## Running Tests

1.  **Backend Tests (Python):**
    * Navigate to the `backend` directory: `cd backend`
    * Activate the virtual environment: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
    * Run all tests: `python -m unittest discover tests`
    * Run a specific test file: `python -m unittest tests.test_person`

2.  **Frontend Tests (React):**
    * Navigate to the `frontend` directory: `cd frontend`
    * Run tests: `npm test`

## Contributing

Please refer to the `todo.md` file for the detailed refactoring plan and planned features. Contributions are welcome!

## License

MIT License
