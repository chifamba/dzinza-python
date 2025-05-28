# Dzinza Family Tree Application

Dzinza Family Tree is a web application for building and managing family trees, featuring a **Python Flask backend API** and a **React frontend**. It allows users to register, log in, add individuals, define relationships, and explore the family structure visually using React Flow.

## Features

### Backend
- Flask application APIs for managing data.
- User authentication and session management.
- RESTful endpoints for core functionalities (authentication, people, relationships, tree data, admin).
- Logging and audit capabilities.

### Frontend
- React single-page application with interactive visualization using React Flow.
- User-friendly interface for managing family trees.
- Features like zooming, panning, and hierarchical display of family trees.

### Security
- Password hashing (bcrypt).
- Data encryption at rest.

### Data Management
- Add, edit, and delete people and relationships.
- Search functionality for people.

## Setup and Installation

### Prerequisites
- Python 3.11+
- Node.js 16+
- Docker (for containerized deployment)

### Installation Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/dzinza-family-tree.git
   cd dzinza-family-tree
   ```
2. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Install frontend dependencies:
   ```bash
   cd ../frontend
   npm install
   ```

### Running the Application

#### Backend
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Run the Flask development server:
   ```bash
   flask run
   ```

#### Frontend
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Start the development server:
   ```bash
   npm run dev
   ```

## Usage

1. **Register/Login:** Use the forms to register a new user or log in.
2. **Dashboard:** View the interactive family tree visualization. Zoom/pan as needed.
3. **Add Person/Relationship:** Use the navigation bar to add new people or relationships.
4. **Edit Person/Relationship:** Click the "Edit" button on a person's node to navigate to the edit form.
5. **Admin Panel:** Manage users if logged in as an admin.
6. **Logout:** Use the "Logout" button in the navigation bar.

## Contributing

Contributions are welcome! Please follow the guidelines in `CONTRIBUTING.md`.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
