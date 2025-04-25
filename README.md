# Dzinza Family Tree Application

Dzinza Family Tree is a web application for building and managing family trees, featuring a **Python Flask backend API** and a **React frontend**. It allows users to register, log in, add individuals, define relationships, and explore the family structure visually using React Flow. The backend uses a Flask API to manage the family tree data, while the frontend provides a clean interface for interaction.

## Features

* **Backend:** Flask API for managing data (Python).
* **Frontend:** React single-page application (Vite) with interactive visualization using React Flow.
* **User Management:**
    * User registration and login.
    * Session-based authentication.
    * Password reset via email.
    * Admin role for user management.
    * Admin panel (via API) to list, delete, and change user roles.
* **Data Management:**
    * Add, edit, and delete people.
    * Add, edit, and delete relationships between people.
    * Search functionality for people (via API - frontend implementation pending).
* **Visualization (React Flow):**
    * Hierarchical display of the family tree.
    * Zooming and panning capabilities.
    * Custom nodes displaying person details (name, dates, photo placeholder).
    * Node selection to view details in a sidebar.
    * Basic edge styling based on relationship type.
* **API:**
    * RESTful endpoints for all core functionalities (authentication, people, relationships, tree data, admin).
    * CORS support for frontend interaction.
    * Input validation for API requests.
    * Consistent JSON error responses.
* **Security:**
    * Password hashing (bcrypt).
    * Data encryption at rest for user and family tree data files (`users.json`, `family_tree.json`).
* **Logging:**
    * Application logging (`app.log`).
    * Audit logging for key actions (`audit.log`).

## Project Structure

dzinza-python/├── backend/              # Contains all Python/Flask code│   ├── src/              # Core logic modules (person, family_tree, etc.)│   ├── tests/            # Backend unit and integration tests│   ├── data/             # Data files (users.json, family_tree.json, encryption_key.json)│   ├── venv/             # Python virtual environment (created by setup script)│   ├── app.py            # Flask app entry point│   └── requirements.txt  # Backend dependencies├── frontend/             # React frontend code│   ├── public/│   ├── src/              # React source files (components, context, api, etc.)│   ├── node_modules/     # Node dependencies (created by setup script)│   ├── package.json│   └── ... (other React project files: vite.config.js, index.html, etc.)├── logs/                 # Log files│   ├── backend/          # Backend logs (app.log, audit.log)│   └── frontend/         # Frontend logs (if any)├── .gitignore├── README.md             # This file├── api_docs.md           # API endpoint documentation├── setup_dev.sh          # Development environment setup script├── run_dev.sh            # Development server run script└── todo.md               # Project TODO list
## Prerequisites

* **Python:** 3.11+ (Verify with `python3 --version`)
* **Pip:** Python package installer (usually comes with Python)
* **Node.js:** 18.x or later recommended (Verify with `node --version`)
* **npm:** Node package manager (comes with Node.js, verify with `npm --version`)
* **Git:** For cloning the repository.
* **Bash-compatible shell:** For running the setup and run scripts (e.g., Git Bash on Windows, Terminal on macOS/Linux).
* **(Optional but Recommended) Email Server/Service:** For password reset functionality (configure via environment variables).

## Environment Variables

The backend requires the following environment variables for full functionality:

* `FLASK_SECRET_KEY`: A strong, random secret key for session signing and token generation. **Crucial for security.**
* `EMAIL_USER`: Username/email for the email sending account (for password reset).
* `EMAIL_PASSWORD`: Password or App Password for the email sending account.
* `EMAIL_SERVER`: SMTP server address (e.g., `smtp.gmail.com`).
* `EMAIL_PORT`: SMTP server port (e.g., `587` for TLS).
* `MAIL_SENDER`: The "From" email address for password reset emails.
* `APP_URL`: The base URL of the frontend application (used in password reset links, e.g., `http://localhost:5173`).
* `FLASK_DEBUG`: Set to `1` for development mode (enables debug logging, auto-reload). Defaults to `0` (production mode).

*Note: For development, you can set these in your shell before running `./run_dev.sh` or use a `.env` file with a library like `python-dotenv` (requires adding it to `requirements.txt` and loading it in `app.py`).*

## Setup and Installation (Using Scripts)

These scripts automate the setup process. Run them from the **project root directory** (`dzinza-python/`).

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd dzinza-python
    ```

2.  **Set Environment Variables:** Configure the necessary environment variables (especially `FLASK_SECRET_KEY`).

3.  **Make scripts executable:**
    ```bash
    chmod +x setup_dev.sh
    chmod +x run_dev.sh
    chmod +x devserver.sh # Ensure devserver is also executable
    ```

4.  **Run the setup script:**
    ```bash
    ./setup_dev.sh
    ```
    This script will:
    * Check for the `backend` and `frontend` directories.
    * Create a Python virtual environment (`.venv`) inside the `backend` directory if it doesn't exist.
    * Install Python dependencies from `backend/requirements.txt` into the virtual environment.
    * Install Node.js dependencies from `frontend/package.json` using `npm install`.

## Running the Application (Development - Using Script)

1.  **Ensure Setup is Complete:** Make sure you have run `./setup_dev.sh` successfully at least once and set the required environment variables.

2.  **Run the Development Server Script:**
    * Open a terminal in the project root directory (`dzinza-python/`).
    * Execute the run script:
        ```bash
        ./run_dev.sh
        ```
    * This script will:
        * Activate the backend Python virtual environment.
        * Start the Flask backend API server (typically on `http://127.0.0.1:8090`).
        * Start the React frontend development server (typically on `http://localhost:5173`).
        * Run both servers concurrently.

3.  **Access the Application:**
    * Open your web browser and navigate to the frontend URL provided in the terminal (usually `http://localhost:5173`).
    * The React app will communicate with the backend API running on port 8090.

4.  **Stopping the Servers:**
    * Go back to the terminal where `./run_dev.sh` is running.
    * Press `Ctrl+C`. The script will attempt to gracefully shut down both the backend and frontend servers.

## Usage (React Frontend)

1.  **Register/Login:** Use the forms to register a new user or log in.
2.  **Dashboard:** View the interactive family tree visualization. Zoom/pan as needed.
3.  **View Details:** Click on a person's node in the tree to see their details in the sidebar.
4.  **Add Person/Relationship:** Use the links in the navigation bar to access forms for adding new people or relationships.
5.  **Edit Person/Relationship:** Click the "Edit" button on a person's node to navigate to the edit form. (Editing relationships requires navigating via URL or adding UI elements).
6.  **Admin Panel:** If logged in as an admin user, use the "Admin Panel" link to manage users (view list, change roles, delete users).
7.  **Logout:** Use the "Logout" button in the navigation bar.

## Running Tests

1.  **Backend Tests (Python):**
    * Ensure you are in the project root directory (`dzinza-python/`).
    * Activate the virtual environment: `source backend/.venv/bin/activate` (or `backend\.venv\Scripts\activate` on Windows).
    * Run all tests: `python -m unittest discover backend/tests`
    * Run a specific test file: `python -m unittest  tests.test_api`

2.  **Frontend Tests (React):**
    * Navigate to the `frontend` directory: `cd frontend`
    * Ensure testing libraries are installed (`npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom` if not already present).
    * Configure Jest (`jest.config.js`) if needed.
    * Run tests: `npm test`

## Contributing

Please refer to the `todo.md` file for the detailed plan and planned features. Contributions are welcome!

## License

MIT License
