# Dzinza - Family Tree Application

Dzinza is a simple web application for building and managing family trees. It allows users to register, log in, add individuals, define relationships between them, and view the family structure.

## Features

* User registration and login (Admin/User roles)
* Add, edit, and view people in the family tree.
* Define relationships (Parent-Child, Marriage, Sibling) between people.
* Search for individuals.
* Admin panel for user management.
* Password reset functionality (Conceptual - requires email setup).
* Audit logging for key actions.
* Basic text-based representation of the tree (via data structure).

## Project Structure

dzinza-python/├── data/                 # Default data storage (JSON files)│   ├── audit.log│   ├── family_tree.json│   └── users.json├── docs/                 # Project documentation│   └── index.md├── logs/                 # Application logs (e.g., Flask logs)│   └── app.log├── src/                  # Source code│   ├── templates/        # HTML templates (Flask/Jinja2)│   │   ├── errors/       # Error page templates (403, 404, 500)│   │   └── ... (other templates: index, login, edit_person etc.)│   ├── audit_log.py      # Handles audit logging│   ├── db_utils.py       # Utility functions for loading/saving JSON data│   ├── encryption.py     # Password hashing and verification│   ├── family_tree.py    # Core FamilyTree class and logic│   ├── person.py         # Person data model│   ├── relationship.py   # Relationship data model│   ├── user.py           # User data model and roles│   ├── user_management.py # User management logic│   └── user_interface.py # (Potentially legacy) CLI interface parts├── tests/                # Unit and integration tests│   ├── test_data/        # Temporary data for integration tests│   └── ... (test files: test_app.py, test_person.py etc.)├── .gitignore├── app.py                # Main Flask application file (routes, app setup)├── devserver.sh          # Script to run the development server├── input.md              # (Potentially input requirements/notes)├── main.py               # (Potentially alternative entry point or script)├── README.md             # This file├── requirements.txt      # Python dependencies└── todo.md               # Project TODO list
## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd dzinza-python
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

1.  **Run the development server:**
    Use the provided script:
    ```bash
    bash devserver.sh
    ```
    Or run Flask directly:
    ```bash
    flask run
    ```
    The application will typically be available at `http://127.0.0.1:5000`.

2.  **Initial Setup:**
    * The application uses JSON files in the `data/` directory for storage by default. These files will be created automatically if they don't exist.
    * There is no default admin user. You may need to register the first user and potentially modify the `data/users.json` file manually to grant the first user ADMIN privileges if required for initial setup, or implement a command-line script to create an admin user. (See `UserRole` in `src/user.py`).

## Usage

1.  **Register/Login:** Access the web interface and register a new user or log in with existing credentials.
2.  **Add Person:** Once logged in, navigate to the "Add Person" section (usually linked from the main page or navigation bar) and fill in the details.
3.  **Edit Person:** View a person's details (e.g., by clicking their name on the main list) and look for an "Edit" button/link.
4.  **Add Relationship:** Navigate to the "Add Relationship" section. Select two individuals from the dropdown lists and specify the relationship type (e.g., MARRIED, PARENT_OF, SIBLING_OF).
5.  **Edit Relationship:** Similar to editing a person, view relationship details (if available) and look for an "Edit" option.
6.  **Search:** Use the search bar (if available on the main page) to find people by name or notes.
7.  **Admin Panel:** If logged in as an ADMIN user, access the "/admin/users" URL to view and delete existing users.
8.  **Logout:** Use the "Logout" link.

## Running Tests

Tests are located in the `tests/` directory and use Python's `unittest` framework.

1.  **Navigate to the project root directory (`dzinza-python`).**
2.  **Run all tests:**
    ```bash
    python -m unittest discover tests
    ```
    Or run a specific test file:
    ```bash
    python -m unittest tests/test_person.py
    ```

## Contributing

Please refer to the `todo.md` file for planned features and improvements. Contributions are welcome!

## License

MIT License
